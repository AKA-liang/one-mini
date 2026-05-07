from __future__ import annotations

import asyncio
import json
from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.base import LLMMessage
from app.llm.router import chat
from app.message_bus import MessageBus
from app.spiders.chanmama import search_hot_products, search_trending_keywords

PRODUCT_PICKER_PROMPT = """你是一位专业的电商选品专家，精通市场分析、竞品调研和爆款挖掘。
你需要分析抖音等平台的热销趋势，结合用户画像和消费心理，筛选出具有高增长潜力的商品。

选品时需综合考虑：
1）市场需求量和增长速度
2）竞争激烈程度
3）利润空间和ROI预期
4）物流难度和供应链稳定性
5）合规性和售后风险

你会收到蝉妈妈平台的真实热销数据，请基于这些数据进行深度分析。

选品完成后，需输出详细的选品报告，包括：商品定位、目标客群、定价策略、推广建议和风险提示。

请以JSON格式输出，包含以下字段：
{
  "products": [
    {
      "name": "商品名称",
      "category": "品类",
      "price_range": "建议定价范围",
      "target_audience": "目标客群",
      "potential_score": 1-10,
      "competition_level": "低/中/高",
      "supply_difficulty": "低/中/高",
      "roi_expectation": "预期ROI",
      "risk_notes": "风险提示",
      "promotion_suggestion": "推广建议"
    }
  ],
  "market_summary": "市场概况总结",
  "trend_analysis": "趋势分析"
}"""


class ProductPickerAgent(BaseAgent):
    name = "product_picker"
    description = "选品分析智能体 - 负责市场热点抓取和爆品筛选"

    def __init__(self, bus: MessageBus):
        super().__init__(bus)

    async def process(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        keywords = payload.get("keywords", [])
        platform = payload.get("platform", "douyin")
        limit = payload.get("limit", 10)

        await self.bus.log(task_id, self.name, "info", f"Starting product analysis: keywords={keywords}, platform={platform}")

        chanmama_data: list[dict[str, Any]] = []
        chanmama_error = ""
        try:
            search_keyword = keywords[0] if keywords else ""
            chanmama_data = await asyncio.to_thread(search_hot_products, keyword=search_keyword, date_type="day")
            await self.bus.log(task_id, self.name, "info", f"Chanmama returned {len(chanmama_data)} products for keyword '{search_keyword}'")
        except Exception as e:
            chanmama_error = str(e)
            await self.bus.log(task_id, self.name, "warning", f"Chanmama scraping failed: {e}")

        context_parts: list[str] = []
        if keywords:
            context_parts.append(f"关键词：{', '.join(keywords)}")
        else:
            context_parts.append(f"热点关键词：{', '.join(search_trending_keywords())}")

        context_parts.append(f"平台：{platform}")
        context_parts.append(f"需要推荐的爆品数量：{limit}")

        if chanmama_data:
            data_text = json.dumps(chanmama_data, ensure_ascii=False, indent=2)
            context_parts.append(
                f"\n以下是从蝉妈妈平台抓取的真实热销数据：\n{data_text}"
            )
        elif chanmama_error:
            context_parts.append(f"\n[注意] 蝉妈妈数据抓取失败：{chanmama_error}，请基于你的专业知识进行分析。")

        user_content = "\n".join(context_parts) + "\n\n请输出完整的选品分析报告。"

        messages = [
            LLMMessage(role="system", content=PRODUCT_PICKER_PROMPT),
            LLMMessage(role="user", content=user_content),
        ]

        response = await chat("product_analysis", messages, temperature=0.7)

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            raw = response.content
            json_match = ""
            import re
            json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw)
            if json_blocks:
                json_match = json_blocks[0].strip()
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
        if chanmama_data:
            result["data_source"] = "chanmama_real"
        elif chanmama_error:
            result["data_source"] = "llm_knowledge_fallback"
            result["chanmama_error"] = chanmama_error

        return result