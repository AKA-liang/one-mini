from __future__ import annotations

import json
import re
from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.base import LLMMessage
from app.llm.router import chat
from app.message_bus import MessageBus

CONTENT_CREATOR_PROMPT = """你是一位资深的抖音电商内容创作者，负责根据选品结果生成带货内容。

你会收到一份选品分析报告，包含多款商品的详细信息（名称、到手价、佣金率、月销量、目标客群、推广建议等）。

请为每款商品生成以下内容：

1. **短视频脚本** (short_video_script): 30-60秒的口播脚本，包含：
   - 开头3秒钩子（吸引停留）
   - 痛点/场景引入
   - 产品卖点展示（2-3个核心卖点）
   - 价格锚点 + 限时优惠话术
   - 行动号召 (CTA)

2. **商品卡片文案** (product_card_text): 适合抖音商品橱窗/小黄车的短文案，突出：
   - 核心卖点一句话
   - 到手价 + 优惠信息
   - 信任背书（如"月销X万"）
   - emoji点缀

3. **话题标签** (hashtags): 5-8个精准带货话题标签

输出格式（纯JSON，不要用```json```包裹）:
{
  "products": [
    {
      "product_name": "商品名称",
      "short_video_script": "完整口播脚本...",
      "product_card_text": "商品卡片文案...",
      "hashtags": ["#话题1", "#话题2", "#话题3", "#话题4", "#话题5"]
    }
  ],
  "overall_strategy": "整体内容策略建议（如发布时间、节奏、矩阵打法）"
}"""


class ContentCreatorAgent(BaseAgent):
    name = "content_creator"
    description = "内容创作智能体 — 根据选品生成短视频脚本和带货文案"

    def __init__(self, bus: MessageBus):
        super().__init__(bus)

    async def process(self, task_id: str, payload: dict[str, Any], action: str = "") -> dict[str, Any]:
        # Accept product_analysis from product_picker or finance_analyst chain result
        product_analysis = payload.get("product_analysis", {})
        if not product_analysis:
            return {"task_id": task_id, "agent": self.name,
                    "error": "No product_analysis data provided", "products": []}

        products = product_analysis.get("products", [])
        if not products:
            return {"task_id": task_id, "agent": self.name,
                    "error": "No products found in analysis", "products": []}

        await self.bus.log(task_id, self.name, "info",
                           f"Generating content for {len(products)} products")

        # Build context for LLM
        context_parts = ["## 选品分析数据\n"]
        for i, p in enumerate(products):
            context_parts.append(
                f"### 商品{i + 1}\n"
                f"- 名称: {p.get('name', '未知')}\n"
                f"- 品类: {p.get('category', '未分类')}\n"
                f"- 到手价: ¥{p.get('price', 'N/A')}\n"
                f"- 佣金率: {p.get('commission_rate', 'N/A')}\n"
                f"- 月销量: {p.get('monthly_sales', 'N/A')}\n"
                f"- 目标客群: {p.get('target_audience', 'N/A')}\n"
                f"- 竞争程度: {p.get('competition_level', 'N/A')}\n"
                f"- 推广建议: {p.get('promotion_suggestion', 'N/A')}\n"
                f"- 潜力评分: {p.get('potential_score', 'N/A')}/10\n"
            )

        if product_analysis.get("market_summary"):
            context_parts.append(f"\n## 市场概况\n{product_analysis['market_summary']}")
        if product_analysis.get("trend_analysis"):
            context_parts.append(f"\n## 趋势分析\n{product_analysis['trend_analysis']}")

        context = "\n".join(context_parts)

        response = await chat("content_creation", [
            LLMMessage(role="system", content=CONTENT_CREATOR_PROMPT),
            LLMMessage(role="user", content=context),
        ], temperature=0.8)

        result = self._parse_response(response.content)
        result["task_id"] = task_id
        result["agent"] = self.name
        result["model_used"] = response.model
        if response.usage:
            result["token_usage"] = response.usage

        await self.bus.log(task_id, self.name, "info",
                           f"Generated content for {len(result.get('products', []))} products")

        return result

    @staticmethod
    def _parse_response(text: str) -> dict[str, Any]:
        text = text.strip()
        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try extracting JSON from markdown code blocks
        m = re.search(r'\{[\s\S]*\}', text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        # Try fixing common issues
        try:
            cleaned = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        return {"raw_response": text[:1000], "products": [],
                "error": "Failed to parse LLM response", "agent": "content_creator"}
