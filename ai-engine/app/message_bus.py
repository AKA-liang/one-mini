from __future__ import annotations

import json
import asyncio
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from app.config import settings
from app.logger import get_logger

logger = get_logger("redis")


class MessageBus:
    TASK_STREAM = "agent:task"
    RESULT_STREAM = "agent:task:result"
    LOG_STREAM = "agent:log"
    COMMAND_STREAM = "agent:command"
    _MAX_RECONNECT_RETRIES = 3

    def __init__(self):
        self.redis: aioredis.Redis | None = None
        self._connected = False

    async def connect(self):
        for attempt in range(1, 6):
            try:
                self.redis = aioredis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    password=settings.redis_password or None,
                    db=settings.redis_db,
                    decode_responses=True,
                    socket_connect_timeout=10,
                    socket_keepalive=True,
                    health_check_interval=30,
                )
                await self.redis.ping()
                self._connected = True
                logger.info(f"Redis connected {settings.redis_host}:{settings.redis_port}")
                return
            except Exception as e:
                wait = min(2 ** attempt, 15)
                logger.warning(f"Redis connect attempt {attempt}/5 failed: {e} — retry in {wait}s")
                if attempt < 5:
                    await asyncio.sleep(wait)
                else:
                    self._connected = False
                    raise RuntimeError(f"Redis connection failed after 5 attempts: {e}")

    async def close(self):
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Redis disconnected")

    async def _ensure_connected(self) -> bool:
        if self._connected and self.redis:
            try:
                await self.redis.ping()
                return True
            except Exception:
                self._connected = False
        for attempt in range(1, self._MAX_RECONNECT_RETRIES + 1):
            try:
                await self.redis.ping()
                self._connected = True
                logger.info("Redis reconnected")
                return True
            except Exception as e:
                logger.warning(f"Redis reconnect attempt {attempt}/{self._MAX_RECONNECT_RETRIES}: {e}")
                await asyncio.sleep(2)
        logger.error("Redis: all reconnect attempts failed")
        return False

    async def health(self) -> bool:
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def send_task(
        self,
        task_id: str,
        to_agent: str,
        action: str,
        payload: dict[str, Any],
        from_agent: str = "ai_engine",
        priority: str = "normal",
    ) -> str:
        msg_id = _uuid()
        message: dict[str, str] = {
            "msg_id": msg_id,
            "task_id": task_id,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "action": action,
            "payload": json.dumps(payload, ensure_ascii=False),
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            if not self._connected:
                await self._ensure_connected()
            result = await self.redis.xadd(self.TASK_STREAM, message)
            return result
        except Exception as e:
            logger.error(f"Redis send_task failed for {task_id}: {e}")
            self._connected = False
            raise

    async def send_result(
        self,
        task_id: str,
        from_agent: str,
        result: dict[str, Any],
        status: str = "completed",
    ) -> str:
        message: dict[str, str] = {
            "task_id": task_id,
            "from_agent": from_agent,
            "status": status,
            "result": json.dumps(result, ensure_ascii=False),
            "timestamp": datetime.now().isoformat(),
        }
        try:
            if not self._connected:
                await self._ensure_connected()
            resp = await self.redis.xadd(self.RESULT_STREAM, message)
            return resp
        except Exception as e:
            logger.error(f"Redis send_result failed for {task_id}: {e}")
            self._connected = False
            raise

    async def read_task(self, count: int = 1, block: int = 5000) -> list[dict[str, Any]]:
        if not hasattr(self, '_task_cursor'):
            self._task_cursor = "$"
        streams = {self.TASK_STREAM: self._task_cursor}
        messages = await self.redis.xread(streams, count=count, block=block)
        result = []
        for stream_name, msgs in messages:
            for msg_id, data in msgs:
                parsed = _parse_message(data)
                parsed["_redis_id"] = msg_id
                result.append(parsed)
                self._task_cursor = msg_id
        return result

    async def ack_task(self, redis_id: str) -> bool:
        """Delete a processed task message from the stream."""
        try:
            count = await self.redis.xdel(self.TASK_STREAM, redis_id)
            return count > 0
        except Exception:
            return False

    async def read_result(self, count: int = 1, block: int = 5000) -> list[dict[str, Any]]:
        if not hasattr(self, '_result_cursor'):
            self._result_cursor = "0"
        streams = {self.RESULT_STREAM: self._result_cursor}
        messages = await self.redis.xread(streams, count=count, block=block)
        result = []
        for stream_name, msgs in messages:
            for msg_id, data in msgs:
                parsed = _parse_message(data)
                parsed["_redis_id"] = msg_id
                result.append(parsed)
                self._result_cursor = msg_id
        return result

    async def log(
        self,
        task_id: str,
        agent_name: str,
        level: str,
        message: str,
        action: str = "",
    ) -> None:
        log_msg: dict[str, str] = {
            "task_id": task_id,
            "agent_name": agent_name,
            "level": level,
            "message": message,
            "action": action,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            if not self._connected:
                await self._ensure_connected()
            await self.redis.xadd(self.LOG_STREAM, log_msg)
        except Exception as e:
            logger.warning(f"Redis log failed for {task_id}: {e}")
            self._connected = False

    async def send_command(
        self,
        task_id: str,
        command: str,
        target_agent: str = "",
        payload: dict[str, Any] | None = None,
    ) -> str:
        message: dict[str, str] = {
            "task_id": task_id,
            "command": command,
            "target_agent": target_agent,
            "payload": json.dumps(payload or {}, ensure_ascii=False),
            "timestamp": datetime.now().isoformat(),
        }
        result = await self.redis.xadd(self.COMMAND_STREAM, message)
        return result


_message_bus: MessageBus | None = None


async def get_message_bus() -> MessageBus:
    global _message_bus
    if _message_bus is None:
        _message_bus = MessageBus()
        await _message_bus.connect()
    return _message_bus


def _parse_message(data: dict[str, str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, value in data.items():
        if key == "payload" or key == "result":
            try:
                parsed[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                parsed[key] = value
        else:
            parsed[key] = value
    return parsed


def _uuid() -> str:
    import uuid

    return str(uuid.uuid4())