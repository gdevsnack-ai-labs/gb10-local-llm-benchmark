from __future__ import annotations
import io
import json
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse, PlainTextResponse

from app.core.config import settings
from app.models.schemas import RunCreate

router = APIRouter()


def bind(store, manager, events):
    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/system")
    async def system():
        import platform, psutil, subprocess
        mem = psutil.virtual_memory()
        nvidia = None
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                nvidia = r.stdout.strip()
        except Exception:
            pass
        return {
            "platform": platform.platform(),
            "arch": platform.machine(),
            "cpu": psutil.cpu_count(logical=False),
            "cpu_logical": psutil.cpu_count(logical=True),
            "memory_total": mem.total,
            "nvidia": nvidia,
        }

    @router.get("/recipes")
    async def list_recipes():
        import yaml
        root = settings.recipe_root
        out = []
        for p in sorted(root.glob("*.yaml")):
            try:
                doc = yaml.safe_load(p.read_text()) or {}
                out.append({"name": p.name, "suite": doc.get("suite"), "config": doc.get("config", {}), "raw": doc})
            except Exception as e:
                out.append({"name": p.name, "error": str(e)})
        return out

    @router.get("/runs")
    async def list_runs():
        return store.list()

    @router.get("/runs/{run_id}")
    async def get_run(run_id: str):
        rec = store.get(run_id)
        if not rec:
            raise HTTPException(404, "run not found")
        return rec

    @router.post("/runs", status_code=202)
    async def create_run(req: RunCreate):
        try:
            # quick validation
            if not req.suite:
                raise KeyError("suite is required")
            return await manager.create(req)
        except (KeyError, FileNotFoundError, ValueError) as e:
            raise HTTPException(400, str(e))

    @router.post("/runs/{run_id}/cancel")
    async def cancel_run(run_id: str):
        rec = store.get(run_id)
        if not rec:
            raise HTTPException(404, "run not found")
        ok = await manager.cancel(run_id)
        if not ok:
            raise HTTPException(400, f"run {run_id} not cancellable (status={rec.status})")
        return {"status": "cancelled", "run_id": run_id}

    @router.get("/runs/{run_id}/metrics")
    async def get_metrics(run_id: str):
        rec = store.get(run_id)
        if not rec:
            raise HTTPException(404, "run not found")
        metrics = store.get_metrics(run_id)
        # also try metrics.jsonl file
        p = settings.run_root / run_id / "metrics.jsonl"
        file_metrics = []
        if p.exists():
            try:
                with open(p) as f:
                    for line in f:
                        file_metrics.append(json.loads(line))
            except Exception:
                pass
        return {"db": metrics, "file": file_metrics, "summary": rec.summary}

    @router.get("/runs/{run_id}/environment")
    async def get_environment(run_id: str):
        p = settings.run_root / run_id / "environment.json"
        if not p.exists():
            raise HTTPException(404, "environment not found")
        return JSONResponse(json.loads(p.read_text()))

    @router.get("/runs/{run_id}/artifacts")
    async def list_artifacts(run_id: str):
        root = settings.run_root / run_id
        if not root.exists():
            raise HTTPException(404, "run not found")
        files = []
        for pp in sorted(root.rglob("*")):
            if pp.is_file():
                rel = pp.relative_to(root)
                # prevent traversal: just relative
                files.append({"path": str(rel), "size": pp.stat().st_size})
        return {"run_id": run_id, "files": files}

    @router.get("/runs/{run_id}/artifacts/{path:path}")
    async def get_artifact(run_id: str, path: str):
        root = settings.run_root / run_id
        target = (root / path).resolve()
        # traversal guard
        if not str(target).startswith(str(root.resolve())):
            raise HTTPException(400, "invalid path")
        if not target.exists() or not target.is_file():
            raise HTTPException(404, "artifact not found")
        return FileResponse(target)

    @router.get("/runs/{run_id}/events")
    async def run_events(run_id: str):
        async def stream():
            rec = store.get(run_id)
            if rec:
                yield f"data: {json.dumps({'run_id': run_id, 'type': 'snapshot', 'data': rec.model_dump(mode='json')})}\n\n"
            async for ev in events.subscribe(run_id):
                yield f"data: {ev.model_dump_json()}\n\n"
                if ev.type == "status" and ev.data.get("status") in {"completed", "failed", "cancelled"}:
                    break
        return StreamingResponse(stream(), media_type="text/event-stream")

    @router.get("/runs/{run_id}/events/history")
    async def events_history(run_id: str, limit: int = 1000):
        return events.read_persisted(run_id, limit=limit)

    @router.post("/compare")
    async def compare(payload: dict):
        ids: list[str] = payload.get("run_ids", [])
        if not ids or len(ids) < 2:
            raise HTTPException(400, "need at least 2 run_ids")
        runs = []
        for rid in ids[:8]:
            rec = store.get(rid)
            if not rec:
                raise HTTPException(404, f"run {rid} not found")
            runs.append(rec)
        # check compatibility: suite and cache_policy
        suites = set(r.suite for r in runs)
        # build metric table
        table = []
        for r in runs:
            metrics = store.get_metrics(r.id)
            row = {"run_id": r.id, "suite": r.suite, "status": r.status, "recipe": r.recipe, "created_at": r.created_at.isoformat()}
            for m in metrics:
                row[m["name"]] = m["value"]
            # add summary fallback
            if r.summary.get("aggregate_predicted_tps"):
                row["aggregate_predicted_tps"] = r.summary["aggregate_predicted_tps"]
            if r.summary.get("latency_mean_s"):
                row["latency_mean_s"] = r.summary["latency_mean_s"]
            table.append(row)
        return {"runs": [r.model_dump(mode="json") for r in runs], "table": table, "warning": "compare only compatible suite/cache_policy" if len(suites) > 1 else None}

    @router.get("/models")
    async def list_models(family: str | None = None, tag: str | None = None):
        return store.list_variants(family=family, tag=tag)

    @router.post("/models/scan")
    async def scan_models(payload: dict | None = None):
        from app.services.model_registry import scan_ggufs
        root_str = (payload or {}).get("root") or os.getenv("MODEL_ROOT")
        if not root_str:
            raise HTTPException(400, "root required or set MODEL_ROOT")
        root = Path(root_str)
        if not root.exists():
            raise HTTPException(400, f"root not found: {root}")
        result = scan_ggufs(root, store)
        return result

    @router.get("/presets")
    async def list_presets():
        return store.list_presets()

    @router.post("/presets")
    async def create_preset(payload: dict):
        name = payload.get("name")
        config = payload.get("config", {})
        if not name:
            raise HTTPException(400, "name required")
        store.upsert_preset(name, config)
        return {"status": "ok", "name": name}

    @router.get("/queue")
    async def get_queue():
        # queued + running runs ordered by created_at
        all_runs = store.list(limit=50)
        queued = [r for r in all_runs if r.status in ("queued", "running")]
        return {"queued": [r.model_dump(mode="json") for r in queued], "total": len(queued)}

    @router.get("/server/status")
    async def server_status():
        from app.services.server_manager import server_manager
        return {"managed": server_manager.is_running(), "url": server_manager.get_url()}

    @router.post("/server/stop")
    async def server_stop():
        from app.services.server_manager import server_manager
        await server_manager.stop()
        return {"status": "stopped"}

    @router.get("/runs/{run_id}/export")
    async def export_run(run_id: str, format: str = Query("json", description="json|csv|markdown|zip|methodology")):
        from app.services.export import build_json_bundle, build_csv_metrics, build_markdown, build_methodology, build_zip
        rec = store.get(run_id)
        if not rec:
            raise HTTPException(404, "run not found")
        fmt = format.lower()
        if fmt == "json":
            return JSONResponse(build_json_bundle(run_id, rec))
        if fmt == "csv":
            return PlainTextResponse(build_csv_metrics(run_id), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={run_id}-metrics.csv"})
        if fmt in ("markdown", "md"):
            return PlainTextResponse(build_markdown(run_id, rec), media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename={run_id}.md"})
        if fmt == "methodology":
            return PlainTextResponse(build_methodology(run_id, rec), media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename={run_id}-methodology.md"})
        if fmt == "zip":
            data = build_zip(run_id, rec)
            return StreamingResponse(io.BytesIO(data), media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={run_id}.zip"})
        raise HTTPException(400, "format must be json|csv|markdown|zip|methodology")

    @router.get("/runs/{run_id}/methodology")
    async def get_methodology(run_id: str):
        from app.services.export import build_methodology
        rec = store.get(run_id)
        if not rec:
            raise HTTPException(404, "run not found")
        return PlainTextResponse(build_methodology(run_id, rec), media_type="text/markdown")

    return router
