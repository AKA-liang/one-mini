from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.llm.base import LLMMessage
from app.llm.router import chat
from app.message_bus import MessageBus
from app.export.excel import export_task_data

logger = logging.getLogger(__name__)

FINANCE_ANALYST_PROMPT = """你是一位资深的电商财务专家，负责成本核算和ROI预测。

⚠️ 输出格式：只输出纯JSON，不要用```json```包裹，不要加任何解释文字。

你会收到选品Agent的输出，每款商品已标注：
- price: 到手价（真实数据）
- commission_rate: 佣金率（真实数据，来自巨量百应选品广场）
- monthly_sales: 月销量

你必须严格使用 price 和 commission_rate 进行财务计算，不要估算。

计算规则：
- revenue = price (售价)
- purchase_cost = 不需要（选品广场给的是到手价，已包含所有成本）
- platform_commission = price × commission_rate
- logistics_cost ≥ 2元/单
- ad_cost_per_order = price × 5%~10%
- return_rate ≤ 30%（根据品类估算）
- net_profit = price × commission_rate - logistics_cost - ad_cost_per_order
  （即：佣金收入 - 物流 - 广告 = 净利）
- profit_margin = net_profit / price
- ROI = net_profit / ad_cost_per_order

JSON格式:
{
  "products": [
    {
      "name": "商品名称",
      "selling_price": 到手价(元),
      "commission_rate": 佣金率,
      "commission_income": 佣金收入(元),
      "logistics_cost": 物流成本(元),
      "ad_cost_per_order": 广告成本(元),
      "return_rate": 退货率,
      "net_profit_per_order": 单笔净利润(元),
      "profit_margin": 利润率,
      "roi": ROI,
      "recommendation": "强烈推荐/推荐/观望/不推荐",
      "risk_notes": "风险提示"
    }
  ],
  "overall_assessment": "整体评估",
  "investment_suggestion": "投资建议"
}"""


async def fetch_own_platform_data(product_names: list[str]) -> dict[str, Any] | None:
    if not settings.own_platform_db_url and not settings.own_platform_api_key:
        return None
    logger.info(f"OwnPlatform: fetching data for {len(product_names)} products (stub)")
    return None


class FinanceAnalystAgent(BaseAgent):
    name = "finance_analyst"
    description = "财务审核智能体 - 负责ROI分析和盈利模型评估"

    def __init__(self, bus: MessageBus):
        super().__init__(bus)

    async def process(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        product_data = payload.get("products", payload.get("product_analysis", {}))

        await self.bus.log(task_id, self.name, "info", f"Starting finance analysis for task {task_id}")

        # Extract products with wholesale prices from product_picker output
        products_with_prices = self._extract_products_with_prices(product_data)
        own_data = await self._fetch_own_platform(task_id, product_names=[])

        if not products_with_prices:
            error_msg = "No products with wholesale prices found — product_picker output is empty or missing best_supply_price"
            await self.bus.log(task_id, self.name, "error", error_msg)
            return {
                "task_id": task_id,
                "agent": self.name,
                "error": error_msg,
                "data_source": "none",
            }

        await self.bus.log(task_id, self.name, "info",
                           f"Got {len(products_with_prices)} products with wholesale prices from ProductPicker")

        context = self._build_context(products_with_prices, own_data)

        response = await chat("finance_review", [
            LLMMessage(role="system", content=FINANCE_ANALYST_PROMPT),
            LLMMessage(role="user", content=context),
        ], temperature=0.3)

        result = self._parse_response(response.content)

        result["task_id"] = task_id
        result["agent"] = self.name
        result["model_used"] = response.model
        if response.usage:
            result["token_usage"] = response.usage

        data_sources = ["product_picker"]
        if own_data:
            data_sources.append("own_platform")
        result["data_source"] = ", ".join(data_sources)

        result["wholesale_status"] = self._format_price_summary(products_with_prices)

        # Export Excel
        try:
            filepath = export_task_data(
                task_id=task_id, keywords="",
                budget=None, category=None,
                finance_data=result.get("products"),
                agent="finance_analyst",
            )
            result["excel_file"] = os.path.basename(filepath)
        except Exception as e:
            await self.bus.log(task_id, self.name, "warning", f"Excel export failed: {e}")

        result = self._sanity_check(result)
        return result

    async def _fetch_own_platform(self, task_id: str, product_names: list[str]) -> dict[str, Any] | None:
        if not settings.own_platform_db_url and not settings.own_platform_api_key:
            return None
        try:
            data = await fetch_own_platform_data(product_names)
            if data:
                await self.bus.log(task_id, self.name, "info", "Own platform data retrieved")
            else:
                await self.bus.log(task_id, self.name, "info", "Own platform: no matching data found")
            return data
        except Exception as e:
            await self.bus.log(task_id, self.name, "warning", f"Own platform fetch failed: {e}")
            return None

    def _extract_products_with_prices(self, product_data: Any) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []
        raw_products: list[dict] = []

        if isinstance(product_data, dict):
            raw_products = product_data.get("products", [])
        elif isinstance(product_data, str):
            try:
                parsed = json.loads(product_data)
                raw_products = parsed.get("products", [])
            except (json.JSONDecodeError, AttributeError):
                pass

        for p in raw_products:
            if not isinstance(p, dict):
                continue
            name = p.get("name", "")
            price = p.get("price", p.get("best_supply_price"))  # backward compat
            comm = p.get("commission_rate")

            if not name:
                continue
            if price is None:
                continue

            products.append({
                "name": str(name)[:200],
                "price": float(price),
                "commission_rate": float(comm) if comm else 0,
                "monthly_sales": p.get("monthly_sales", p.get("sales")),
            })

        return products

    def _format_price_summary(self, products: list[dict]) -> str:
        parts = []
        for p in products[:5]:
            name = p.get("name", "")[:20]
            pr = p.get("price", 0)
            cr = p.get("commission_rate", 0)
            parts.append(f"{name}: ¥{pr}/{cr:.0%}")
        return f"佣金数据(共{len(products)}款): " + " | ".join(parts)

    def _build_context(
        self,
        products_with_prices: list[dict[str, Any]],
        own_data: dict[str, Any] | None,
    ) -> str:
        parts: list[str] = []
        parts.append("请对以下选品结果进行财务审核和ROI分析：")

        real_data = []
        for item in products_with_prices:
            entry = {
                "name": item.get("name", ""),
                "price": item.get("price", 0),
                "commission_rate": item.get("commission_rate", 0),
                "monthly_sales": item.get("monthly_sales"),
            }
            if entry["name"]:
                real_data.append(entry)

        parts.append(f"\n选品数据（含真实到手价+佣金率）：\n{json.dumps(real_data, ensure_ascii=False, indent=2)}")
        parts.append("\n说明：price=到手售价, commission_rate=真实佣金率（来自巨量百应选品广场），"
                     "佣金收入 = price × commission_rate，净利润 = 佣金收入 - 物流 - 广告。")

        if own_data:
            parts.append(f"\n本平台历史数据：\n{json.dumps(own_data, ensure_ascii=False, indent=2)}")

        parts.append("\n请基于以上真实数据输出完整的财务分析报告。")
        return "\n".join(parts)

    def _parse_response(self, content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", content)
        for block in blocks:
            try:
                return json.loads(block.strip())
            except json.JSONDecodeError:
                continue
        brace = re.search(r"\{[\s\S]*\}", content)
        if brace:
            try:
                return json.loads(brace.group(0))
            except json.JSONDecodeError:
                pass
        return {"raw_response": content[:2000]}

    def _sanity_check(self, result: dict[str, Any]) -> dict[str, Any]:
        products = result.get("products", [])
        for product in products:
            if isinstance(product, dict):
                profit_margin = product.get("profit_margin", 0)
                if isinstance(profit_margin, (int, float)) and profit_margin > 0.9:
                    product["profit_margin"] = 0.9
                    product["_sanity_check"] = "profit_margin capped at 90%"

                commission_rate = product.get("platform_commission_rate", 0)
                if isinstance(commission_rate, (int, float)):
                    if commission_rate > 0.15:
                        product["platform_commission_rate"] = 0.15
                        product["_sanity_check"] = "commission_rate capped at 15%"
                    elif commission_rate < 0.05 and commission_rate > 0:
                        product["platform_commission_rate"] = 0.05
                        product["_sanity_check"] = "commission_rate floored at 5%"

                logistics_cost = product.get("logistics_cost", 0)
                if isinstance(logistics_cost, (int, float)) and logistics_cost < 2:
                    product["logistics_cost"] = 2
                    product["_sanity_check"] = "logistics_cost floored at 2 yuan"

        return result
