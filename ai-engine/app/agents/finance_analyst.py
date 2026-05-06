from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.base import LLMMessage
from app.llm.router import chat
from app.message_bus import MessageBus
from app.spiders.alibaba1688 import search_products as search_1688_products

FINANCE_ANALYST_PROMPT = """你是一位资深的电商财务专家，负责成本核算、利润分析和税务筹划。
你需要基于采购成本、物流成本、平台佣金、广告投放费用、退货率等数据，进行精细化的ROI预测。

分析时请严格遵守以下常识规则：
- 平台佣金一般在5%-15%之间
- 物流成本不会低于2元/单
- 退货率一般不超过30%
- 利润率不可能超过90%
- 毛利率 = (售价-采购成本)/售价

你会收到1688平台的真实采购价格数据，请基于这些数据进行精确的ROI计算。

请以JSON格式输出分析报告：
{
  "products": [
    {
      "name": "商品名称",
      "purchase_cost": 采购成本(元),
      "selling_price": 建议售价(元),
      "platform_commission_rate": 平台佣金率,
      "platform_commission": 平台佣金(元),
      "logistics_cost": 物流成本(元),
      "ad_cost_per_order": 单均广告成本(元),
      "return_rate": 预估退货率,
      "return_cost": 退货成本(元),
      "net_profit_per_order": 单均净利润(元),
      "profit_margin": 利润率,
      "roi": 预期ROI,
      "break_even_orders": 回本所需订单数,
      "recommendation": "推荐/观望/不推荐",
      "risk_notes": "风险提示"
    }
  ],
  "overall_assessment": "整体评估",
  "investment_suggestion": "投资建议"
}"""


class FinanceAnalystAgent(BaseAgent):
    name = "finance_analyst"
    description = "财务审核智能体 - 负责ROI分析和盈利模型评估"

    def __init__(self, bus: MessageBus):
        super().__init__(bus)

    async def process(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        product_data = payload.get("products", payload.get("product_analysis", {}))

        await self.bus.log(task_id, self.name, "info", f"Starting finance analysis for task {task_id}")

        alibaba_data: list[dict[str, Any]] = []
        alibaba_error = ""

        product_names: list[str] = []
        if isinstance(product_data, dict):
            products_list = product_data.get("products", [])
            for p in products_list:
                if isinstance(p, dict) and p.get("name"):
                    product_names.append(str(p["name"]))
        elif isinstance(product_data, str):
            try:
                parsed = json.loads(product_data)
                for p in parsed.get("products", []):
                    if isinstance(p, dict) and p.get("name"):
                        product_names.append(str(p["name"]))
            except (json.JSONDecodeError, AttributeError):
                pass

        if product_names:
            try:
                search_keyword = product_names[0].split()[0] if product_names[0] else "热销"
                alibaba_data = await asyncio.to_thread(search_1688_products, keyword=search_keyword, page=1)
                await self.bus.log(task_id, self.name, "info", f"1688 returned {len(alibaba_data)} products")
            except Exception as e:
                alibaba_error = str(e)
                await self.bus.log(task_id, self.name, "warning", f"1688 scraping failed: {e}")

        context_parts: list[str] = []
        context_parts.append("请对以下选品结果进行财务审核和ROI分析：")
        context_parts.append(f"\n选品数据：\n{product_data if isinstance(product_data, str) else json.dumps(product_data, ensure_ascii=False, indent=2)}")

        if alibaba_data:
            real_data = []
            for item in alibaba_data:
                entry = {
                    "product_name": item.get("product_name", ""),
                    "price_min": item.get("price_min"),
                    "price_max": item.get("price_max"),
                    "moq": item.get("moq"),
                    "shop_name": item.get("shop_name", ""),
                }
                if entry["product_name"]:
                    real_data.append(entry)
            if real_data:
                context_parts.append(
                    f"\n以下是从1688平台抓取的真实采购价格数据：\n{json.dumps(real_data, ensure_ascii=False, indent=2)}"
                )
        elif alibaba_error:
            context_parts.append(f"\n[注意] 1688数据抓取失败：{alibaba_error}，请基于你的专业知识估算采购成本。")

        context_parts.append("\n请输出完整的财务分析报告，注意数值必须符合商业常识。")

        user_content = "\n".join(context_parts)

        messages = [
            LLMMessage(role="system", content=FINANCE_ANALYST_PROMPT),
            LLMMessage(role="user", content=user_content),
        ]

        response = await chat("finance_review", messages, temperature=0.3)

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            raw = response.content
            json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw)
            json_match = json_blocks[0].strip() if json_blocks else ""
            if not json_match:
                brace_match = re.search(r"\{[\s\S]*\}", raw)
                if brace_match:
                    json_match = brace_match.group(0)
            if json_match:
                try:
                    result = json.loads(json_match)
                except json.JSONDecodeError:
                    result = {"raw_response": raw, "parse_error": "Could not extract JSON from response"}
            else:
                result = {"raw_response": raw, "parse_error": "Response is not valid JSON"}

        result["task_id"] = task_id
        result["agent"] = self.name
        result["model_used"] = response.model
        if response.usage:
            result["token_usage"] = response.usage
        if alibaba_data:
            result["data_source"] = "1688_real"
        elif alibaba_error:
            result["data_source"] = "llm_knowledge_fallback"
            result["alibaba_error"] = alibaba_error

        result = self._sanity_check(result)

        return result

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