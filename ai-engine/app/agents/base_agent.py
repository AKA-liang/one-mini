from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.message_bus import MessageBus


class BaseAgent(ABC):
    name: str = "base"
    description: str = ""

    def __init__(self, bus: MessageBus):
        self.bus = bus

    @abstractmethod
    async def process(self, task_id: str, payload: dict[str, Any], action: str = "") -> dict[str, Any]:
        pass

    async def run(self, task_id: str, payload: dict[str, Any], action: str = "") -> dict[str, Any]:
        await self.bus.log(task_id, self.name, "info", f"Agent {self.name} started processing")
        try:
            result = await self.process(task_id, payload, action)
            await self.bus.send_result(task_id, self.name, result, "completed")
            await self.bus.log(task_id, self.name, "info", f"Agent {self.name} completed successfully")
            return result
        except Exception as e:
            error_result = {"error": str(e), "agent": self.name}
            await self.bus.send_result(task_id, self.name, error_result, "failed")
            await self.bus.log(task_id, self.name, "error", f"Agent {self.name} failed: {e}")
            raise