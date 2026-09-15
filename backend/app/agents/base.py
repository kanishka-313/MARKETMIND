"""
Base Agent.

Every agent is an async callable that:
  1. Receives a context dict (symbol, prior agent outputs).
  2. Emits log events through an emit() callback.
  3. Returns its result, which the orchestrator merges into the context.
"""
from __future__ import annotations
import abc
from typing import Any, Awaitable, Callable

EmitFn = Callable[[str, str, dict | None], Awaitable[None]]


class BaseAgent(abc.ABC):
    name: str = "base"

    async def run(self, context: dict[str, Any], emit: EmitFn) -> dict[str, Any]:
        await emit("started", f"{self.name} started", None)
        try:
            result = await self.execute(context, emit)
            await emit("completed", f"{self.name} completed", {"summary": self.summarize(result)})
            return result
        except Exception as e:  # noqa: BLE001
            await emit("failed", f"{self.name} failed: {e}", None)
            raise

    @abc.abstractmethod
    async def execute(self, context: dict[str, Any], emit: EmitFn) -> dict[str, Any]:
        ...

    def summarize(self, result: dict[str, Any]) -> str:
        return "ok"
