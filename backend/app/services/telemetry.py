from __future__ import annotations
import asyncio
import time
import psutil
import subprocess
from typing import Any, Callable, Awaitable

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


def _gpu_util() -> dict | None:
    # try nvidia-smi util
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
        if r.returncode == 0 and r.stdout.strip():
            parts = [x.strip() for x in r.stdout.strip().split(",")]
            return {"gpu_util_pct": float(parts[0]) if parts[0] not in ("N/A","") else None,
                    "mem_used_mib": float(parts[1]) if len(parts)>1 and parts[1] not in ("N/A","") else None,
                    "mem_total_mib": float(parts[2]) if len(parts)>2 and parts[2] not in ("N/A","") else None,
                    "power_w": float(parts[3]) if len(parts)>3 and parts[3] not in ("N/A","") else None}
    except Exception:
        pass
    return None


class TelemetrySampler:
    def __init__(self, emit: Emit, interval: float = 1.0):
        self.emit = emit
        self.interval = interval
        self.task: asyncio.Task | None = None
        self._running = False
        self._start = 0.0

    async def _loop(self):
        # warmup cpu_percent
        psutil.cpu_percent(interval=None)
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                gpu = _gpu_util()
                elapsed = time.perf_counter() - self._start
                payload: dict[str, Any] = {
                    "elapsed_s": round(elapsed, 2),
                    "cpu_pct": cpu,
                    "mem_used_bytes": mem.used,
                    "mem_total_bytes": mem.total,
                    "mem_pct": mem.percent,
                }
                if gpu:
                    payload.update(gpu)
                await self.emit("telemetry", payload)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            try:
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break

    async def start(self):
        self._running = True
        self._start = time.perf_counter()
        self.task = asyncio.create_task(self._loop())

    async def stop(self):
        self._running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
