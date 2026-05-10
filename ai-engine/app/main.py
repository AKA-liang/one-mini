from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.agents.product_picker import ProductPickerAgent
from app.agents.finance_analyst import FinanceAnalystAgent
from app.message_bus import MessageBus, get_message_bus
from app.logger import init_logging, get_logger
from app.spiders.browser import get_browser


class CharsetMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        if response.headers.get("content-type", "").startswith("application/json"):
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response


app = FastAPI(title="One Mini AI Engine", version="0.1.0")
app.add_middleware(CharsetMiddleware)

init_logging()
logger = get_logger("main")

bus: MessageBus | None = None
agents: dict[str, object] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global bus, agents
    bus = await get_message_bus()
    agents = {
        "product_picker": ProductPickerAgent(bus),
        "finance_analyst": FinanceAnalystAgent(bus),
    }
    logger.info("AI Engine started", extra={"agents": list(agents.keys())})

    # Start persistent Edge browser (CDP) — disabled: conflicts with persistent_context
    # browser = await get_browser()
    browser = None

    asyncio.create_task(_consume_tasks())
    yield
    if bus:
        await bus.close()
        logger.info("AI Engine shutdown")
    if browser:
        await browser.shutdown()


app.router.lifespan_context = lifespan


async def _consume_tasks():
    if not bus:
        return
    logger.info("Task consumer started")
    processed = 0
    while True:
        try:
            messages = await bus.read_task(count=1, block=5000)
            for msg in messages:
                to_agent = msg.get("to_agent", "")
                task_id = msg.get("task_id", "")
                action = msg.get("action", "")
                payload = msg.get("payload", {})
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except json.JSONDecodeError:
                        payload = {"raw": payload}

                logger.info(f"Processing task {task_id} → {to_agent}/{action}")
                agent = agents.get(to_agent)
                if agent is None:
                    await bus.log(task_id, "router", "error", f"Unknown agent: {to_agent}")
                    logger.warning(f"Unknown agent: {to_agent} for task {task_id}")
                    continue

                await bus.log(task_id, "router", "info", f"Routing task {task_id} to {to_agent}")

                # Auto-chain: if product_analysis finishes, trigger finance_review
                if to_agent == "product_picker":
                    try:
                        result = await agent.run(task_id, payload)
                        processed += 1
                        logger.info(f"ProductPicker completed task {task_id} (#{processed})")
                        # Chain to finance_analyst
                        finance_agent = agents.get("finance_analyst")
                        if finance_agent:
                            finance_payload = {
                                "product_analysis": result,
                                "original_task_id": task_id,
                            }
                            finance_task_id = str(uuid.uuid4())
                            await bus.send_task(
                                finance_task_id,
                                "finance_analyst",
                                "finance_review",
                                finance_payload,
                                from_agent="product_picker",
                            )
                            await bus.log(task_id, "router", "info",
                                          f"Chained to finance_analyst with task {finance_task_id}")
                            logger.info(f"Chained finance_analyst for task {task_id}")
                    except Exception as e:
                        await bus.log(task_id, "router", "error", f"Agent failed: {e}")
                        logger.error(f"ProductPicker failed for task {task_id}: {e}", exc_info=True)

                elif to_agent == "finance_analyst":
                    try:
                        await agent.run(task_id, payload)
                        processed += 1
                        logger.info(f"FinanceAnalyst completed task {task_id} (#{processed})")
                    except Exception as e:
                        await bus.log(task_id, "router", "error", f"Agent failed: {e}")
                        logger.error(f"FinanceAnalyst failed for task {task_id}: {e}", exc_info=True)

                else:
                    try:
                        await agent.run(task_id, payload)
                        logger.info(f"Agent {to_agent} completed task {task_id}")
                    except Exception as e:
                        await bus.log(task_id, "router", "error", f"Agent failed: {e}")
                        logger.error(f"Agent {to_agent} failed for task {task_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Consumer loop error: {e}", exc_info=True)
            await asyncio.sleep(1)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "one-mini-ai-engine",
        "version": "0.1.0",
        "agents": list(agents.keys()),
    }


@app.post("/test/send-task")
async def test_send_task():
    if not bus:
        return {"error": "Message bus not initialized"}
    task_id = str(uuid.uuid4())
    await bus.send_task(
        task_id,
        "product_picker",
        "echo_test",
        {"test": True, "keywords": ["美妆", "护肤"], "platform": "douyin"},
        from_agent="test",
    )
    return {"task_id": task_id, "status": "sent", "target": "product_picker"}


@app.post("/test/chat")
async def test_chat(prompt: str = "你好，请用一句话介绍你自己", model: str = "minimax"):
    from app.llm.router import get_llm
    from app.llm.base import LLMMessage

    llm = get_llm(model)
    messages = [LLMMessage(role="user", content=prompt)]
    response = await llm.chat(messages)
    return {
        "model": response.model,
        "content": response.content,
        "usage": response.usage,
    }