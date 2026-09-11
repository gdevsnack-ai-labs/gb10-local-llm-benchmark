from __future__ import annotations
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.schemas import RunCreate, RunRecord


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        with self.conn:
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                suite TEXT NOT NULL,
                status TEXT NOT NULL,
                recipe TEXT,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                error TEXT,
                summary_json TEXT NOT NULL
            )
            """)
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS run_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                name TEXT NOT NULL,
                value REAL,
                unit TEXT,
                extra_json TEXT,
                FOREIGN KEY(run_id) REFERENCES runs(id) ON DELETE CASCADE
            )
            """)
            # EventBus persists the authoritative event stream as runs/<id>/events.jsonl.
            # Do not create a second, unused SQLite event store.
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS model_variants (
                id TEXT PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                file_size INTEGER,
                mtime TEXT,
                quantization TEXT,
                family TEXT,
                tags_json TEXT,
                display_name TEXT,
                sha256 TEXT,
                last_scan TEXT
            )
            """)
            self.conn.execute("""
            CREATE TABLE IF NOT EXISTS backend_presets (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                config_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
            # migrate: add missing columns if db existed before
            try:
                self.conn.execute("SELECT seq FROM run_events LIMIT 1")
            except Exception:
                pass

    def create_run(self, run_id: str, req: RunCreate) -> RunRecord:
        rec = RunRecord(
            id=run_id, suite=req.suite, status="queued", recipe=req.recipe,
            config=req.config, created_at=utcnow(), summary={}
        )
        with self.lock, self.conn:
            self.conn.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rec.id, rec.suite, rec.status, rec.recipe, json.dumps(rec.config),
                 rec.created_at.isoformat(), None, None, None, json.dumps({}))
            )
        return rec

    def update(self, run_id: str, **fields: Any):
        allowed = {"status", "started_at", "finished_at", "error", "summary"}
        sets, vals = [], []
        for key, value in fields.items():
            if key not in allowed:
                continue
            col = "summary_json" if key == "summary" else key
            if key == "summary": value = json.dumps(value)
            if isinstance(value, datetime): value = value.isoformat()
            sets.append(f"{col} = ?")
            vals.append(value)
        if not sets:
            return
        vals.append(run_id)
        with self.lock, self.conn:
            self.conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE id = ?", vals)

    def add_metrics(self, run_id: str, metrics: list[dict]):
        if not metrics:
            return
        with self.lock, self.conn:
            for m in metrics:
                self.conn.execute(
                    "INSERT INTO run_metrics (run_id, name, value, unit, extra_json) VALUES (?, ?, ?, ?, ?)",
                    (run_id, m.get("name"), m.get("value"), m.get("unit"), json.dumps(m.get("extra") or {})),
                )

    def get_metrics(self, run_id: str) -> list[dict]:
        rows = self.conn.execute("SELECT name, value, unit, extra_json FROM run_metrics WHERE run_id = ? ORDER BY id", (run_id,)).fetchall()
        return [{"name": r["name"], "value": r["value"], "unit": r["unit"], "extra": json.loads(r["extra_json"])} for r in rows]

    # model variants
    def upsert_variant(self, path: str, file_size: int, mtime: str, quantization: str | None, family: str | None, tags: list[str], display_name: str, sha256: str | None):
        import uuid
        vid = str(Path(path).as_posix())
        # use path as id (or hash)
        # normalize id as path string
        now = utcnow().isoformat()
        with self.lock, self.conn:
            self.conn.execute("""
            INSERT INTO model_variants (id, path, file_size, mtime, quantization, family, tags_json, display_name, sha256, last_scan)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET file_size=excluded.file_size, mtime=excluded.mtime, quantization=excluded.quantization, family=excluded.family, tags_json=excluded.tags_json, display_name=excluded.display_name, sha256=excluded.sha256, last_scan=excluded.last_scan
            """, (vid, path, file_size, mtime, quantization, family, json.dumps(tags), display_name, sha256, now))

    def delete_missing_variants(self, found_paths: list[str]):
        # keep only found; delete others
        # if found empty, don't delete all
        if not found_paths:
            return
        placeholders = ",".join("?" for _ in found_paths)
        with self.lock, self.conn:
            self.conn.execute(f"DELETE FROM model_variants WHERE path NOT IN ({placeholders})", found_paths)

    def list_variants(self, family: str | None = None, tag: str | None = None, limit: int = 200) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM model_variants ORDER BY family, quantization, path LIMIT ?", (limit,)).fetchall()
        out = []
        for r in rows:
            tags = json.loads(r["tags_json"]) if r["tags_json"] else []
            if family and r["family"] != family:
                continue
            if tag and tag not in tags:
                continue
            out.append({"id": r["id"], "path": r["path"], "file_size": r["file_size"], "mtime": r["mtime"], "quantization": r["quantization"], "family": r["family"], "tags": tags, "display_name": r["display_name"], "sha256": r["sha256"], "last_scan": r["last_scan"]})
        return out

    def list_presets(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM backend_presets ORDER BY name").fetchall()
        return [{"id": r["id"], "name": r["name"], "config": json.loads(r["config_json"]), "created_at": r["created_at"]} for r in rows]

    def upsert_preset(self, name: str, config: dict):
        import uuid
        pid = name
        now = utcnow().isoformat()
        with self.lock, self.conn:
            self.conn.execute("""
            INSERT INTO backend_presets (id, name, config_json, created_at) VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET config_json=excluded.config_json
            """, (pid, name, json.dumps(config), now))

    def get(self, run_id: str) -> RunRecord | None:
        row = self.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return self._row(row) if row else None

    def list(self, limit: int = 100) -> list[RunRecord]:
        rows = self.conn.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(r: sqlite3.Row) -> RunRecord:
        return RunRecord(
            id=r["id"], suite=r["suite"], status=r["status"], recipe=r["recipe"],
            config=json.loads(r["config_json"]), created_at=datetime.fromisoformat(r["created_at"]),
            started_at=datetime.fromisoformat(r["started_at"]) if r["started_at"] else None,
            finished_at=datetime.fromisoformat(r["finished_at"]) if r["finished_at"] else None,
            error=r["error"], summary=json.loads(r["summary_json"]),
        )
