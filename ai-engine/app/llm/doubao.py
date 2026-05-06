from __future__ import annotations

import hashlib
import hmac
import json
import datetime
from typing import Any

import httpx

from app.config import settings
from app.llm.base import BaseLLM, LLMMessage, LLMResponse


class DoubaoLLM(BaseLLM):
    def __init__(self):
        self.endpoint = settings.doubao_endpoint
        self.model_id = settings.doubao_model_id
        self.access_key = settings.volc_access_key
        self.secret_key = settings.volc_secret_key

    async def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        formatted_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]

        payload: dict[str, Any] = {
            "model": self.model_id,
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
                f"{self.endpoint}/chat/completions",
                headers=self._build_headers(),
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
        return LLMResponse(content=content, usage=usage, model=self.model_id)

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
            "model": self.model_id,
            "messages": formatted_messages,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.endpoint}/chat/completions",
                headers=self._build_headers(),
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
        return LLMResponse(content=content, usage=usage, model=self.model_id)

    def _build_headers(self) -> dict[str, str]:
        # Volcengine Ark API uses Bearer token auth
        # For now, using access key as authorization token
        # Will be updated with proper HMAC signing if needed
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_key}",
        }