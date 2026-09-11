from __future__ import annotations
from app.runners.base import BenchmarkRunner, RunContext


class PlaceholderRunner(BenchmarkRunner):
    def __init__(self, name: str):
        self.name = name

    async def run(self, ctx: RunContext) -> dict:
        await ctx.emit("phase", {"name": self.name, "note": "runner contract scaffold only"})
        return {
            "kind": self.name,
            "implemented": False,
            "next": "Implement suite adapter using the common RunContext/Artifact contract."
        }
