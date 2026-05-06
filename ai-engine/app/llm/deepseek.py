from __future__ import annotations

from typing import Any

import httpx

from app.config import settings
from app.llm.base import BaseLLM, LLMMessage, LLMResponse


class DeepSeekLLM(BaseLLM):
    def __init__(self):
        self.base_url = settings.deepseek_base_url
        self.model = settings.deepseek_model
        self.api_key = settings.deepseek_api_key

    async def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        formatted_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
        }
        if kwargs.get("temperature") is not None:
            payload["temperature"] = kwargs["temperature"]
        if kwargs.get("max_tokens") is not None:
            payload["max_tokens"] = kwargs["max_tokens"]
        if kwargs.get("response_format"):
            payload["response_format"] = kwargs["response_format"]

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = {
            "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
            "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
            "total_tokens": data.get("usage", {}).get("total_tokens", 0),
        }
        return LLMResponse(content=content, usage=usage, model=self.model)

    async def chat_with_images(
        self,
        messages: list[LLMMessage],
        images: list[str],
        **kwargs: Any,
    ) -> LLMResponse:
        # DeepSeek supports multimodal in some models, fallback to text-only
        # For now, append image URLs to the last user message
        last_user_idx = -1
        formatted_messages: list[dict[str, Any]] = []
        for i, m in enumerate(messages):
            formatted_messages.append({"role": m.role, "content": m.content})
            if m.role == "user":
                last_user_idx = i

        if images and last_user_idx >= 0:
            image_text = "\n\nImages:\n" + "\n".join(f"![image]({img})" for img in images)
            formatted_messages[last_user_idx]["content"] += image_text

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        usage = {
            "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
            "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
            "total_tokens": data.get("usage", {}).get("total_tokens", 0),
        }
        return LLMResponse(content=content, usage=usage, model=self.model)