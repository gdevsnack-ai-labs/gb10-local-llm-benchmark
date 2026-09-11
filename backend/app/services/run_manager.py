from __future__ import annotations
import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import yaml

from app.core.config import settings
from app.core.env import capture_environment
from app.db.store import Store
from app.models.schemas import RunCreate
from app.runners.base import RunContext
from app.runners.reasoning import normalize_thinking_config
from app.runners.coding import CodingRunner
from app.runners.knowledge import KnowledgeRunner
from app.runners.llama_bench import LlamaBenchRunner, normalize_llama_bench_rows
from app.runners.server_perf import ServerPerformanceRunner
from app.runners.tool_call import ToolCallRunner
from app.runners.agent_single import AgentSingleRunner
from app.runners.agent_multi import AgentMultiRunner
from app.runners.placeholders import PlaceholderRunner
from app.services.events import EventBus
from app.services.server_manager import server_manager
from app.services.telemetry import TelemetrySampler


class RunManager:
    def __init__(self, store: Store, events: EventBus):
        self.store = store
        self.events = events
        self.tasks: dict[str, asyncio.Task] = {}
        self.cancel_events: dict[str, asyncio.Event] = {}
        self.model_lock = asyncio.Lock()  # serialize model-dependent runs (GB10 single host)
        self.runners = {
            "performance": LlamaBenchRunner(),
            "server-performance": ServerPerformanceRunner(),
            "coding": CodingRunner(),
            "tool-call": ToolCallRunner(),
            "agent-single": AgentSingleRunner(),
            "agent-multi": AgentMultiRunner(),
            "knowledge": KnowledgeRunner(),
        }

    def _load_recipe(self, name: str | None) -> tuple[dict, Path | None, str | None]:
        if not name:
            return {}, None, None
        path = settings.recipe_root / name
        if path.suffix not in {".yaml", ".yml"}:
            path = path.with_suffix(".yaml")
        if not path.exists():
            raise FileNotFoundError(f"Recipe not found: {path}")
        raw = path.read_text(encoding="utf-8")
        return yaml.safe_load(raw) or {}, path, raw

    async def create(self, req: RunCreate):
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        recipe, recipe_path, recipe_source = self._load_recipe(req.recipe)
        merged = {**recipe.get("config", {}), **req.config}
        thinking = normalize_thinking_config(merged)
        merged.setdefault("thinking_mode", thinking.mode)
        merged.setdefault("thinking_budget", thinking.budget)
        merged.setdefault("request_timeout_s", thinking.request_timeout_s)
        req = RunCreate(suite=req.suite or recipe.get("suite", "performance"), recipe=req.recipe, config=merged)
        rec = self.store.create_run(run_id, req)
        cancel_ev = asyncio.Event()
        self.cancel_events[run_id] = cancel_ev
        self.tasks[run_id] = asyncio.create_task(
            self._execute(run_id, req, cancel_ev, recipe_path=recipe_path, recipe_source=recipe_source)
        )
        return rec

    async def cancel(self, run_id: str) -> bool:
        rec = self.store.get(run_id)
        if not rec or rec.status not in ("queued", "running"):
            return False
        ev = self.cancel_events.get(run_id)
        if ev:
            ev.set()
        task = self.tasks.get(run_id)
        if task:
            task.cancel()
        # update DB optimistically; _execute will finalize
        self.store.update(run_id, status="cancelled", finished_at=datetime.now(timezone.utc))
        await self.events.publish(run_id, "status", {"status": "cancelled"})
        return True

    def _validate_suite(self, suite: str):
        if suite not in self.runners:
            raise KeyError(f"Unknown suite: {suite}. Available: {', '.join(self.runners)}")

    async def _execute(
        self,
        run_id: str,
        req: RunCreate,
        cancel_event: asyncio.Event,
        recipe_path: Path | None = None,
        recipe_source: str | None = None,
    ):
        run_dir = settings.run_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        recipe_sha256 = hashlib.sha256(recipe_source.encode("utf-8")).hexdigest() if recipe_source is not None else None
        manifest = {
            "run_id": run_id,
            "suite": req.suite,
            "recipe": req.recipe,
            "recipe_path": str(recipe_path) if recipe_path else None,
            "recipe_sha256": recipe_sha256,
            "config": req.config,
            "resolved_config": dict(req.config),
        }
        if recipe_source is not None:
            (run_dir / "recipe.yaml").write_text(recipe_source, encoding="utf-8")
        resolved_yaml = yaml.safe_dump(req.config, sort_keys=False, allow_unicode=True)
        manifest["resolved_config_sha256"] = hashlib.sha256(resolved_yaml.encode("utf-8")).hexdigest()
        (run_dir / "resolved-config.yaml").write_text(resolved_yaml, encoding="utf-8")
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        # environment capture before run
        try:
            capture_environment(run_dir, req.config)
        except Exception:
            pass
        # serialize model runs: wait for lock before marking running
        need_lock = req.suite in ("performance", "server-performance", "knowledge", "coding", "tool-call", "agent-single", "agent-multi") and req.config.get("model_path")
        lock_acquired = False
        if need_lock:
            await self.model_lock.acquire()
            lock_acquired = True
        self.store.update(run_id, status="running", started_at=datetime.now(timezone.utc))
        await self.events.publish(run_id, "status", {"status": "running"})
        telemetry = TelemetrySampler(lambda t, d: self.events.publish(run_id, t, d), interval=1.0)
        await telemetry.start()
        managed_server = None
        try:
            self._validate_suite(req.suite)
            runner = self.runners[req.suite]
            # handle managed server (server-performance, knowledge, coding, tool-call)
            effective_config = dict(req.config)
            if req.suite in ("server-performance", "knowledge", "coding", "tool-call", "agent-single", "agent-multi") and (effective_config.get("managed") or (effective_config.get("model_path") and not effective_config.get("server_url"))):
                # start managed server
                managed_server = await server_manager.start(run_dir, effective_config, emit=lambda t,d: self.events.publish(run_id, t, d))
                effective_config["server_url"] = managed_server.url
                # record managed flag
                effective_config["_managed_url"] = managed_server.url
                await self.events.publish(run_id, "phase", {"name": "managed-server", "url": managed_server.url})
            # Persist the effective runtime configuration after managed-server resolution.
            resolved_yaml = yaml.safe_dump(effective_config, sort_keys=False, allow_unicode=True)
            manifest["resolved_config"] = effective_config
            manifest["resolved_config_sha256"] = hashlib.sha256(resolved_yaml.encode("utf-8")).hexdigest()
            (run_dir / "resolved-config.yaml").write_text(resolved_yaml, encoding="utf-8")
            (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
            ctx = RunContext(
                run_id=run_id,
                run_dir=run_dir,
                config=effective_config,
                emit=lambda t, d: self.events.publish(run_id, t, d),
                cancel_event=cancel_event,
            )
            result = await runner.run(ctx)
            # attach managed info
            if managed_server:
                result["_managed_server"] = {"url": managed_server.url, "model": managed_server.model}
            # normalize llama-bench rows if present
            if req.suite == "performance" and isinstance(result, dict) and "rows" in result:
                try:
                    metrics = normalize_llama_bench_rows(result.get("rows", []), run_id)
                    # persist metrics.jsonl
                    with open(run_dir / "metrics.jsonl", "w", encoding="utf-8") as f:
                        for m in metrics:
                            f.write(json.dumps(m, ensure_ascii=False) + "\n")
                    self.store.add_metrics(run_id, metrics)
                    result["metrics_normalized"] = len(metrics)
                except Exception as e:
                    result["metrics_error"] = str(e)
            (run_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            # check if cancelled during run
            if cancel_event.is_set():
                self.store.update(run_id, status="cancelled", finished_at=datetime.now(timezone.utc), summary=result)
                await self.events.publish(run_id, "status", {"status": "cancelled", "summary": result})
            else:
                self.store.update(run_id, status="completed", finished_at=datetime.now(timezone.utc), summary=result)
                await self.events.publish(run_id, "status", {"status": "completed", "summary": result})
        except asyncio.CancelledError:
            self.store.update(run_id, status="cancelled", finished_at=datetime.now(timezone.utc), error="cancelled")
            await self.events.publish(run_id, "status", {"status": "cancelled", "error": "cancelled"})
        except Exception as e:
            # if cancel was requested, mark cancelled
            if cancel_event.is_set():
                self.store.update(run_id, status="cancelled", finished_at=datetime.now(timezone.utc), error=str(e))
                await self.events.publish(run_id, "status", {"status": "cancelled", "error": str(e)})
            else:
                self.store.update(run_id, status="failed", finished_at=datetime.now(timezone.utc), error=str(e))
                await self.events.publish(run_id, "status", {"status": "failed", "error": str(e)})
        finally:
            await telemetry.stop()
            if managed_server:
                try:
                    if not req.config.get("reuse_managed"):
                        await server_manager.stop()
                    else:
                        await self.events.publish(run_id, "phase", {"name": "server-kept", "url": managed_server.url})
                except Exception:
                    pass
            if lock_acquired:
                try:
                    self.model_lock.release()
                except Exception:
                    pass
            self.tasks.pop(run_id, None)
            self.cancel_events.pop(run_id, None)
