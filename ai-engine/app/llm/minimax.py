from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import settings
from app.llm.base import BaseLLM, LLMMessage, LLMResponse


class MiniMaxLLM(BaseLLM):
    def __init__(self):
        self.base_url = settings.minimax_base_url
        self.model = settings.minimax_model
        self.api_key = settings.minimax_api_key

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
        max_tokens = kwargs.get("max_tokens", 4096)
        payload["max_tokens"] = max_tokens
        if kwargs.get("response_format"):
            payload["response_format"] = kwargs["response_format"]

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        content = self._strip_think_tags(content)

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
        formatted_messages: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "user" and images:
                content_parts: list[dict[str, Any]] = [
                    {"type": "text", "text": m.content}
                ]
                for img in images:
                    content_parts.append(
                        {"type": "image_url", "image_url": {"url": img}}
                    )
                formatted_messages.append({"role": "user", "content": content_parts})
            else:
                formatted_messages.append({"role": m.role, "content": m.content})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
        }
        max_tokens = kwargs.get("max_tokens", 4096)
        payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._build_headers(),
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        content = self._strip_think_tags(content)

        usage = {
            "prompt_tokens": data.get("usage", {}).get("prompt_tokens", 0),
            "completion_tokens": data.get("usage", {}).get("completion_tokens", 0),
            "total_tokens": data.get("usage", {}).get("total_tokens", 0),
        }
        return LLMResponse(content=content, usage=usage, model=self.model)

    def _build_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    @staticmethod
    def _strip_think_tags(content: str) -> str:
        think_open = '<' + 'think>'
        think_close = '</' + 'think>'
        import re
        pattern = think_open + '.*?' + think_close
        stripped = re.sub(pattern, '', content, flags=re.DOTALL).strip()
        return stripped if stripped else content.strip()

