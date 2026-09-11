from __future__ import annotations
import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.schemas import RunEvent


class EventBus:
    def __init__(self, run_root: Path | None = None):
        self.queues: dict[str, list[asyncio.Queue]] = defaultdict(list)
        self.run_root = run_root or settings.run_root
        self._seq: dict[str, int] = defaultdict(int)

    def _event_path(self, run_id: str) -> Path:
        return self.run_root / run_id / "events.jsonl"

    async def publish(self, run_id: str, event_type: str, data: dict):
        self._seq[run_id] += 1
        ev = RunEvent(run_id=run_id, type=event_type, ts=datetime.now(timezone.utc), data=data, seq=self._seq[run_id])
        # persist to JSONL
        try:
            p = self._event_path(run_id)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(ev.model_dump_json() + "\n")
        except Exception:
            pass
        for q in list(self.queues[run_id]):
            await q.put(ev)

    async def subscribe(self, run_id: str):
        q: asyncio.Queue = asyncio.Queue()
        self.queues[run_id].append(q)
        # replay persisted events
        try:
            p = self._event_path(run_id)
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        line=line.strip()
                        if not line:
                            continue
                        try:
                            ev = RunEvent.model_validate_json(line)
                            await q.put(ev)
                        except Exception:
                            continue
                # ensure seq continues
                try:
                    last = ev.seq if 'ev' in locals() else 0  # type: ignore
                    if last:
                        self._seq[run_id] = max(self._seq[run_id], last)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            while True:
                yield await q.get()
        finally:
            self.queues[run_id].remove(q)

    def read_persisted(self, run_id: str, limit: int = 1000) -> list[RunEvent]:
        p = self._event_path(run_id)
        if not p.exists():
            return []
        out: list[RunEvent] = []
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line=line.strip()
                    if not line:
                        continue
                    try:
                        out.append(RunEvent.model_validate_json(line))
                    except Exception:
                        continue
        except Exception:
            return out
        return out[-limit:]
