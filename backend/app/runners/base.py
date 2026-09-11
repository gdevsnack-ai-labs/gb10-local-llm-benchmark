from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Any

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class RunContext:
    run_id: str
    run_dir: Path
    config: dict[str, Any]
    emit: Emit
    cancel_event: asyncio.Event | None = None


class BenchmarkRunner(ABC):
    name: str

    @abstractmethod
    async def run(self, ctx: RunContext) -> dict[str, Any]:
        raise NotImplementedError
