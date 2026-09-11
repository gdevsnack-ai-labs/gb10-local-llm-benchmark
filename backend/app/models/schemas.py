from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

RunStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class RunCreate(BaseModel):
    suite: str
    recipe: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    id: str
    suite: str
    status: RunStatus
    recipe: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    summary: dict[str, Any] = Field(default_factory=dict)


class RunEvent(BaseModel):
    run_id: str
    type: str
    ts: datetime
    seq: int = 0
    data: dict[str, Any] = Field(default_factory=dict)
