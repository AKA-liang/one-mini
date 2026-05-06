from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str
    content: str
    images: list[str] | None = None


class LLMResponse(BaseModel):
    content: str
    usage: dict[str, int] | None = None
    model: str = ""


class BaseLLM(ABC):
    @abstractmethod
    async def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        pass

    @abstractmethod
    async def chat_with_images(
        self,
        messages: list[LLMMessage],
        images: list[str],
        **kwargs: Any,
    ) -> LLMResponse:
        pass