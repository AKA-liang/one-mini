from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.base import LLMMessage
from app.llm.router import chat
from app.message_bus import MessageBus
from app.spiders.chanmama import search_hot_products, search_trending_keywords, search_hot_products_persistent
from app.spiders.buyin import search_buyin
from app.export.excel import export_task_data

PRODUCT_PICKER_PROMPT = """你是一位专业的电商选品专家，筛选出具有高增长潜力和盈利空间的商品。

⚠️ 输出格式：只输出纯JSON，不要用```json```包裹，不要加任何解释文字。

你会收到两组真实数据：

## 蝉妈妈 — 抖音需求侧 (25维度)
每条商品: title, brand, sales_volume_text, sales_amount_text, live/video拆分,
sales_volume_index(需求强度), creator_count(达人数=竞争), shop_count(小店数=供给)

## 巨量百应选品广场 — 采购价+佣金
每条商品: product_name, price(到手价), commission_rate(佣金率), sales(月销量), earn(赚取金额)
这些是按蝉妈妈热销品名在选品广场精确搜索匹配的结果。

选品排序维度：
1）利润空间 (price × commission_rate → 赚取金额，越高越优先)
2）需求强度 (蝉妈妈 sales_volume_index，越高越优先)
3）竞争密度 (creator_count，适中最佳)
4）销量验证 (Buyin月销量 vs 蝉妈妈预估销量，一致则可信度高)

输出要求：为每款商品标注「到手价」和「佣金率」。(数值)

JSON格式:
{
  "products": [
    {
      "name": "商品名称",
      "category": "品类",
      "price": 到手价(元 数值),
      "commission_rate": 佣金率(0.00-1.00),
      "monthly_sales": 月销量,
      "earn_per_order": 单笔赚取(元),
      "target_audience": "目标客群",
      "potential_score": 1-10,
      "competition_level": "低/中/高",
      "roi_expectation": "预期ROI",
      "risk_notes": "风险提示",
      "promotion_suggestion": "推广建议"
    }
  ],
  "market_summary": "市场概况",
  "trend_analysis": "趋势分析"
}"""


class ProductPickerAgent(BaseAgent):
    name = "product_picker"
    description = "选品分析智能体"

    def __init__(self, bus: MessageBus):
        super().__init__(bus)

    async def process(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        keywords = payload.get("keywords", [])
        limit = payload.get("limit", 10)
        budget = payload.get("budget")
        category = payload.get("category")
        # Normalize: treat empty/zero budget as "no constraint"
        if budget in (None, "", "0", 0):
            budget = None
        if category in (None, ""):
            category = None
        search_kw = " ".join(keywords) if keywords else ""
        # Hot list fallback: no keywords → use trending defaults
        if not search_kw or "?" in search_kw:
            trending = search_trending_keywords()
            search_kw = " ".join(trending[:3]) if trending else "美妆护肤"
            await self.bus.log(task_id, self.name, "info",
                               f"No keywords provided — using hot list: {search_kw}")

        await self.bus.log(task_id, self.name, "info",
                           f"Starting: keywords={keywords}, budget={budget}")

        # ─── Stage 1: Chanmama → hot products (persistent_context) ───
        chanmama_data, chanmama_error = await self._fetch_chanmama_persistent(task_id, search_kw)
        if not chanmama_data:
            # Fallback to cookie injection
            chanmama_data, chanmama_error = await self._fetch_chanmama_cookie(task_id, search_kw)

        if not chanmama_data:
            return {"task_id": task_id, "agent": self.name,
                    "error": f"Chanmama failed: {chanmama_error}", "data_source": "none"}

        await self.bus.log(task_id, self.name, "info", f"Chanmama: {len(chanmama_data)} products")

        # ─── Stage 2: Buyin by name → price + commission ───
        names = self._extract_product_names(chanmama_data, n=5)
        buyin_products, buyin_error = await self._fetch_buyin_by_names(task_id, names)

        await self.bus.log(task_id, self.name, "info",
                           f"Buyin: {len(buyin_products)} matches from {len(names)} names")

        # ─── Build context → LLM ───
        chanmama_preview = self._simplify_chanmama(chanmama_data[:20])
        ctx = self._build_context(search_kw, limit, budget, category,
                                  chanmama_preview, buyin_products)

        response = await chat("product_analysis", [
            LLMMessage(role="system", content=PRODUCT_PICKER_PROMPT),
            LLMMessage(role="user", content=ctx),
        ], temperature=0.7)

        result = self._parse_response(response.content)
        result["task_id"] = task_id
        result["agent"] = self.name
        result["model_used"] = response.model
        if response.usage:
            result["token_usage"] = response.usage

        data_sources = ["chanmama"]
        if buyin_products:
            data_sources.append("buyin")
        result["data_source"] = ", ".join(data_sources)
        if chanmama_error:
            result["chanmama_error"] = chanmama_error
        if buyin_error:
            result["buyin_error"] = buyin_error

        # Export Excel
        try:
            filepath = export_task_data(
                task_id=task_id, keywords=search_kw,
                budget=str(budget) if budget else None,
                category=category,
                chanmama_data=chanmama_data,
                buyin_data=buyin_products,
                llm_products=result.get("products"),
                agent="product_picker",
            )
            result["excel_file"] = os.path.basename(filepath)
            await self.bus.log(task_id, self.name, "info", f"Excel saved: {os.path.basename(filepath)}")
        except Exception as e:
            await self.bus.log(task_id, self.name, "warning", f"Excel export failed: {e}")

        return result

    async def _fetch_chanmama_persistent(self, task_id: str, kw: str) -> tuple[list[dict], str]:
        """Primary: persistent_context (real Edge profile, API interception)."""
        try:
            from app.spiders.chanmama import search_hot_products_persistent
            data = await asyncio.to_thread(search_hot_products_persistent, keyword=kw, limit=50)
            await self.bus.log(task_id, self.name, "info", f"Chanmama(persistent): {len(data)} products")
            return data, ""
        except Exception as e:
            await self.bus.log(task_id, self.name, "warning", f"Chanmama(persistent) failed: {e}")
            return [], str(e)

    async def _fetch_chanmama_cookie(self, task_id: str, kw: str) -> tuple[list[dict], str]:
        """Fallback: cookie injection."""
        try:
            data = await asyncio.to_thread(search_hot_products, keyword=kw, limit=100)
            await self.bus.log(task_id, self.name, "info", f"Chanmama(cookie): {len(data)} products")
            return data, ""
        except Exception as e:
            return [], str(e)

    async def _fetch_buyin_by_names(self, task_id: str, names: list[str]) -> tuple[list[dict], str]:
        if not names:
            return [], "No names"
        from app.spiders.browser import get_browser
        all_products: list[dict] = []
        seen: set[str] = set()
        buyin_errors: list[str] = []

        for name in names[:5]:
            try:
                browser = await get_browser()
                page = await browser.new_page()
                await page.goto("https://buyin.jinritemai.com/dashboard/merch-picking-library",
                               wait_until="networkidle", timeout=60000)
                await page.wait_for_selector('.auxo-input, input[type="search"]', timeout=20000)
                await page.wait_for_timeout(3000)

                search_input = await page.query_selector('.auxo-input, input[type="search"]')
                if search_input:
                    await search_input.click()
                    await page.wait_for_timeout(500)
                    await search_input.type(name, delay=50)
                    await page.wait_for_timeout(500)
                    await search_input.press("Enter")
                    try:
                        await page.wait_for_selector('text=/到手价/', timeout=25000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(5000)

                body_text = await page.evaluate("document.body.innerText || ''")
                error_matched = None
                for pat in ["网络不稳定", "请稍后再试", "登录", "验证", "系统错误"]:
                    if pat in body_text:
                        logger.warning(f"Buyin: Error — {pat}")
                        error_matched = pat
                        await page.close()
                        break
                if error_matched:
                    buyin_errors.append(f"buyin/{name}: {error_matched}")
                else:
                    # Extract data
                    from app.spiders.buyin import _SEARCH_EXTRACT_JS, _normalize_product
                    items = await page.evaluate(_SEARCH_EXTRACT_JS)

                    for item in items:
                        if isinstance(item, dict):
                            n = _normalize_product(item)
                            pn = n.get("product_name", "") if n else ""
                            if pn and pn not in seen:
                                seen.add(pn)
                                all_products.append(n)
                await page.close()
            except Exception as e:
                logger.warning(f"Buyin CDP for '{name}': {e}")

        error_str = "; ".join(buyin_errors[:5]) if buyin_errors else ""
        return all_products, error_str

    def _extract_product_names(self, data: list[dict], n: int = 5) -> list[str]:
        names: list[str] = []
        seen: set[str] = set()
        for item in data:
            title = item.get("title", "")
            short = self._shorten_name(title)
            if short and short not in seen:
                seen.add(short)
                names.append(short)
            if len(names) >= n:
                break
        return names

    @staticmethod
    def _shorten_name(title: str) -> str:
        """Extract core product name: brand + product type, skip 适用/机型/promotional words."""
        # Remove whitespace and special chars
        title = re.sub(r"[\s\-_【】\[\]\(\)（）]", " ", title)
        words = title.split()
        skip = {"适用", "新款", "爆款", "热销", "正品", "厂家", "直销", "抖音", "同款",
                "专用", "通用", "简约", "高档", "高级", "新款", "跨境", "网红"}
        # Also skip phone model patterns
        phone_pattern = re.compile(r"^(苹果|华为|vivo|oppo|小米|iphone|\d+(pro|promax|mini|plus)?)$", re.I)
        core = [w for w in words if w not in skip and not phone_pattern.match(w)]
        # Take first 3-4 words as search phrase
        result = " ".join(core[:3])
        return result if len(result) >= 4 else core[0] if core else title[:15]

    @staticmethod
    def _simplify_chanmama(items: list[dict]) -> list[dict]:
        keep = ["title", "brand", "sales_volume_text", "sales_amount_text",
                "live_volume_text", "video_volume_text",
                "sales_volume_index", "sales_amount_index",
                "creator_count", "shop_count", "product_count"]
        return [{k: item.get(k) for k in keep if item.get(k) is not None} for item in items]

    def _build_context(self, kw: str, limit: int, budget, category,
                       chanmama: list[dict], buyin: list[dict]) -> str:
        parts = ["## 选品任务", f"关键词：{kw}", f"需要推荐：{limit} 款"]
        if budget:
            parts.append(f"预算上限：{budget} 元")
        if category:
            parts.append(f"品类限制：{category}")

        if chanmama:
            parts.append(f"\n## 蝉妈妈热销SPU ({len(chanmama)}条)")
            parts.append("字段: sales_volume_index=需求, creator_count=竞争, shop_count=供给")
            parts.append(json.dumps(chanmama[:15], ensure_ascii=False, indent=2))

        if buyin:
            simple = [{"name": p.get("product_name", ""), "price": p.get("price"),
                       "commission_rate": p.get("commission_rate"), "sales": p.get("sales")}
                      for p in buyin[:20]]
            parts.append(f"\n## 巨量百应选品广场 ({len(buyin)}条，按蝉妈妈品名精确匹配)")
            parts.append("字段: price=到手价, commission_rate=佣金率, sales=月销量")
            parts.append(json.dumps(simple, ensure_ascii=False, indent=2))

        parts.append("\n请综合需求热度和实际采购价，选出最优商品。")
        return "\n".join(parts)

    def _parse_response(self, content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks (greedy)
        blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", content)
        for block in blocks:
            try:
                return json.loads(block.strip())
            except json.JSONDecodeError:
                continue

        # Try matching outermost braces
        brace = re.search(r"\{[\s\S]*\}", content)
        if brace:
            try:
                return json.loads(brace.group(0))
            except json.JSONDecodeError:
                pass

        # Last resort: try to find any JSON-like structure
        possible = re.findall(r'\{[^{}]*"name"[^{}]*"price"[^{}]*\}', content)
        if possible:
            products = []
            for p_str in possible:
                try:
                    products.append(json.loads(p_str))
                except json.JSONDecodeError:
                    pass
            if products:
                return {"products": products, "_reconstructed": True}

        return {"raw_response": content[:2000], "parse_error": "Could not extract JSON"}
