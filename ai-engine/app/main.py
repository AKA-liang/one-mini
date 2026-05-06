from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents.product_picker import ProductPickerAgent
from app.agents.finance_analyst import FinanceAnalystAgent
from app.message_bus import MessageBus, get_message_bus

app = FastAPI(title="One Mini AI Engine", version="0.1.0")

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
    asyncio.create_task(_consume_tasks())
    yield
    if bus:
        await bus.close()


app.router.lifespan_context = lifespan


async def _consume_tasks():
    if not bus:
        return
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

                agent = agents.get(to_agent)
                if agent is None:
                    await bus.log(
                        task_id,
                        "router",
                        "error",
                        f"Unknown agent: {to_agent}",
                    )
                    continue

                await bus.log(task_id, "router", "info", f"Routing task {task_id} to {to_agent}")

                # Auto-chain: if product_analysis finishes, trigger finance_review
                if to_agent == "product_picker":
                    try:
                        result = await agent.run(task_id, payload)
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
                            await bus.log(
                                task_id,
                                "router",
                                "info",
                                f"Chained to finance_analyst with task {finance_task_id}",
                            )
                    except Exception as e:
                        await bus.log(task_id, "router", "error", f"Agent failed: {e}")

                elif to_agent == "finance_analyst":
                    try:
                        await agent.run(task_id, payload)
                    except Exception as e:
                        await bus.log(task_id, "router", "error", f"Agent failed: {e}")

                else:
                    try:
                        await agent.run(task_id, payload)
                    except Exception as e:
                        await bus.log(task_id, "router", "error", f"Agent failed: {e}")

        except Exception as e:
            print(f"Error consuming tasks: {e}")
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