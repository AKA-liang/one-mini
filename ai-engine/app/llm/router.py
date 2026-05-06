from __future__ import annotations

from typing import Any

from app.llm.base import BaseLLM, LLMMessage, LLMResponse
from app.llm.doubao import DoubaoLLM
from app.llm.deepseek import DeepSeekLLM
from app.llm.minimax import MiniMaxLLM

_LLM_INSTANCES: dict[str, BaseLLM] = {}

# Task type to model mapping (MiniMax as primary)
TASK_MODEL_MAP: dict[str, str] = {
    "product_analysis": "minimax",      # M2.7 reasoning for product selection
    "finance_review": "minimax",        # M2.7 reasoning for ROI analysis
    "customer_service": "minimax",      # Chinese conversation
    "data_extraction": "minimax",       # Fast classification
    "knowledge_search": "minimax",      # Embedding + retrieval
}


def get_llm(model_type: str = "minimax") -> BaseLLM:
    if model_type not in _LLM_INSTANCES:
        if model_type == "minimax":
            _LLM_INSTANCES[model_type] = MiniMaxLLM()
        elif model_type == "doubao":
            _LLM_INSTANCES[model_type] = DoubaoLLM()
        elif model_type == "deepseek":
            _LLM_INSTANCES[model_type] = DeepSeekLLM()
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    return _LLM_INSTANCES[model_type]


def get_llm_for_task(task_type: str) -> BaseLLM:
    model_type = TASK_MODEL_MAP.get(task_type, "minimax")
    return get_llm(model_type)


async def chat(task_type: str, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
    llm = get_llm_for_task(task_type)
    return await llm.chat(messages, **kwargs)


async def chat_with_images(
    task_type: str,
    messages: list[LLMMessage],
    images: list[str],
    **kwargs: Any,
) -> LLMResponse:
    llm = get_llm_for_task(task_type)
    return await llm.chat_with_images(messages, images, **kwargs)