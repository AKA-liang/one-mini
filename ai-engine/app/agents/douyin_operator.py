"""
Douyin Operator Agent — comment management + auto-reply.
Workflow: list works → export comments → LLM generates replies → batch reply.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from app.agents.base_agent import BaseAgent
from app.llm.base import LLMMessage
from app.llm.router import chat
from app.message_bus import MessageBus
from app.spiders.douyin_creator import list_works, export_comments, reply_comments, publish_article, publish_imagetext

REPLY_PROMPT = """你是抖音账号的客服助手。根据评论内容生成回复。

规则：
- 回复不超过 400 个 Unicode 字符
- 使用中文引号 ""
- 语气友好、亲切
- 如果是产品咨询，引导到购买链接
- 如果是好评，表达感谢
- 如果是投诉，表示理解并提供解决方案
- 不接受引流、外链、联系方式等违规内容

请为每条评论生成回复，以JSON格式输出：
{
  "replies": [
    {
      "username": "用户名",
      "commentText": "原始评论",
      "replyMessage": "回复内容"
    }
  ]
}"""


class DouyinOperatorAgent(BaseAgent):
    name = "douyin_operator"
    description = "抖音运营智能体 — 评论管理和自动回复"

    def __init__(self, bus: MessageBus):
        super().__init__(bus)

    async def process(self, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        action = payload.get("action", "auto_reply")
        work_title = payload.get("work_title", "")
        reply_limit = payload.get("reply_limit", 20)

        await self.bus.log(task_id, self.name, "info", f"Starting: action={action}")

        # ─── Action: auto_reply (comment management) ───
        if action == "auto_reply":
            return await self._handle_auto_reply(task_id, work_title, reply_limit)

        # ─── Action: publish_article ───
        if action == "publish_article":
            title = payload.get("title", "")
            content = payload.get("content", "")
            image = payload.get("image_path", "")
            subtitle = payload.get("subtitle", "")
            tags = payload.get("tags", [])
            dry_run = payload.get("dry_run", False)
            result = await asyncio.to_thread(publish_article, title, content, image, subtitle, tags, dry_run)
            if result.get("status") == "login_required":
                result["error"] = "发布失败 — 请先在 Edge 中登录 creator.douyin.com"
            result["task_id"] = task_id
            result["agent"] = self.name
            await self.bus.log(task_id, self.name, "info",
                               f"Article publish: {result.get('status')} | "
                               f"title='{title[:120]}' | content_len={len(content or '')} | "
                               f"image='{image[:80] if image else 'none'}' | dry_run={dry_run}")
            return result

        # ─── Action: publish_imagetext ───
        if action == "publish_imagetext":
            title = payload.get("title", "")
            image_paths = payload.get("image_paths", [])
            desc = payload.get("description", "")
            dry_run = payload.get("dry_run", False)
            result = await asyncio.to_thread(publish_imagetext, title, image_paths, desc, dry_run)
            if result.get("status") == "login_required":
                result["error"] = "发布失败 — 请先在 Edge 中登录 creator.douyin.com"
            result["task_id"] = task_id
            result["agent"] = self.name
            await self.bus.log(task_id, self.name, "info",
                               f"Imagetext publish: {result.get('status')} | "
                               f"title='{title[:120]}' | desc_len={len(desc or '')} | "
                               f"images={len(image_paths or [])} | dry_run={dry_run}")
            return result

        return {"task_id": task_id, "agent": self.name, "error": f"Unknown action: {action}"}

    async def _handle_auto_reply(self, task_id: str, work_title: str, reply_limit: int) -> dict[str, Any]:
        works = await asyncio.to_thread(list_works)
        await self.bus.log(task_id, self.name, "info", f"Found {len(works)} works")

        if not works:
            return {"task_id": task_id, "agent": self.name,
                    "error": "未找到作品 — 请先在 Edge 中登录 creator.douyin.com 后再试"}

        # Step 2: Export comments
        if not work_title and works:
            work_title = works[0].get("title", "")
        if not work_title:
            return {"task_id": task_id, "agent": self.name, "error": "No work_title specified and no works available"}

        comments_data = await asyncio.to_thread(export_comments, work_title, reply_limit)
        comments = comments_data.get("comments", [])
        await self.bus.log(task_id, self.name, "info",
                           f"Exported {len(comments)} unreplied comments from '{work_title}'")

        if not comments:
            return {
                "task_id": task_id,
                "agent": self.name,
                "works_count": len(works),
                "work_title": work_title,
                "comments_count": 0,
                "message": "No unreplied comments found",
            }

        # Step 3: LLM generates replies
        ctx = json.dumps(comments, ensure_ascii=False, indent=2)
        response = await chat("comment_reply", [
            LLMMessage(role="system", content=REPLY_PROMPT),
            LLMMessage(role="user", content=f"请为以下评论生成回复：\n{ctx}"),
        ], temperature=0.7)

        reply_data = self._parse_json(response.content)
        replies = reply_data.get("replies", reply_data)

        if not replies:
            return {
                "task_id": task_id,
                "agent": self.name,
                "works_count": len(works),
                "work_title": work_title,
                "comments_count": len(comments),
                "replies_count": 0,
                "message": "LLM did not generate replies",
            }

        # Step 4: Batch reply
        reply_result = await asyncio.to_thread(reply_comments, replies, work_title)

        reply_preview = json.dumps(replies[:3], ensure_ascii=False)[:400]
        await self.bus.log(task_id, self.name, "info",
                           f"Batch reply: {len(replies)} replies to '{work_title}' | "
                           f"results={reply_result.get('summary', '')} | preview={reply_preview}")

        result = {
            "task_id": task_id,
            "agent": self.name,
            "works_count": len(works),
            "work_title": work_title,
            "comments_count": len(comments),
            "replies_count": len(replies),
            "reply_result": reply_result,
        }
        return result

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", content)
            for b in blocks:
                try:
                    return json.loads(b.strip())
                except json.JSONDecodeError:
                    pass
            brace = re.search(r"\{[\s\S]*\}", content)
            if brace:
                try:
                    return json.loads(brace.group(0))
                except json.JSONDecodeError:
                    pass
            return {"replies": []}
