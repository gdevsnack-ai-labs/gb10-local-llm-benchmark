from __future__ import annotations
import csv
import io
import json
import zipfile
from pathlib import Path
from datetime import datetime
import yaml

from app.core.config import settings


def _dict_or_empty(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def canonical_environment(env: dict) -> dict:
    """Interpret the persisted nested environment schema once for exports."""
    os_info = _dict_or_empty(env.get("os"))
    cpu = _dict_or_empty(env.get("cpu"))
    bench = _dict_or_empty(env.get("llama_bench"))
    server = _dict_or_empty(env.get("llama_server"))
    cpp = _dict_or_empty(env.get("llama_cpp"))
    physical = cpu.get("physical", "-")
    logical = cpu.get("logical", "-")
    return {
        "os": " ".join(str(x) for x in (os_info.get("system"), os_info.get("release")) if x) or "-",
        "arch": env.get("arch") or os_info.get("machine") or "-",
        "cpu": f"{physical} physical / {logical} logical",
        "gpu": str(env.get("nvidia") or "-"),
        "llama_bench_path": bench.get("resolved") or bench.get("path") or "-",
        "llama_bench_commit": bench.get("commit") or cpp.get("commit") or "-",
        "llama_server_path": server.get("resolved") or server.get("path") or "-",
        "llama_server_version": server.get("version") or "-",
        "llama_server_commit": server.get("commit") or cpp.get("commit") or bench.get("commit") or "-",
        "llama_cpp_commit": cpp.get("commit") or bench.get("commit") or server.get("commit") or "-",
        "platform_commit": env.get("platform_commit") or "-",
        "config": env.get("config") if isinstance(env.get("config"), dict) else {},
    }

def _load_run_files(run_id: str) -> dict:
    root = settings.run_root / run_id
    manifest = json.loads((root / "manifest.json").read_text()) if (root / "manifest.json").exists() else {}
    env = json.loads((root / "environment.json").read_text()) if (root / "environment.json").exists() else {}
    result = json.loads((root / "result.json").read_text()) if (root / "result.json").exists() else {}
    recipe = (root / "recipe.yaml").read_text(encoding="utf-8") if (root / "recipe.yaml").exists() else None
    resolved_config = {}
    if (root / "resolved-config.yaml").exists():
        try:
            resolved_config = yaml.safe_load((root / "resolved-config.yaml").read_text(encoding="utf-8")) or {}
        except Exception:
            resolved_config = {}
    if not resolved_config:
        resolved_config = manifest.get("resolved_config") or manifest.get("config", {})
    metrics = []
    if (root / "metrics.jsonl").exists():
        for line in (root / "metrics.jsonl").read_text().splitlines():
            if line.strip():
                try: metrics.append(json.loads(line))
                except: pass
    samples = []
    if (root / "samples.jsonl").exists():
        for line in (root / "samples.jsonl").read_text().splitlines():
            if line.strip():
                try: samples.append(json.loads(line))
                except: pass
    return {"manifest": manifest, "env": env, "result": result, "metrics": metrics, "samples": samples, "recipe": recipe, "resolved_config": resolved_config, "root": root}

def build_json_bundle(run_id: str, rec) -> dict:
    files = _load_run_files(run_id)
    return {
        "run": rec.model_dump(mode="json") if hasattr(rec, "model_dump") else rec,
        "manifest": files["manifest"],
        "environment": files["env"],
        "recipe": files["recipe"],
        "resolved_config": files["resolved_config"],
        "result": files["result"],
        "metrics": files["metrics"],
        "samples_count": len(files["samples"]),
        "exported_at": datetime.now().isoformat(),
    }

def build_csv_metrics(run_id: str) -> str:
    files = _load_run_files(run_id)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["name","value","unit","extra"])
    for m in files["metrics"]:
        w.writerow([m.get("name",""), m.get("value",""), m.get("unit",""), json.dumps(m.get("extra",""), ensure_ascii=False)[:200]])
    if not files["metrics"]:
        # fallback to summary samples
        s = files["result"]
        if isinstance(s, dict):
            for k,v in s.items():
                if isinstance(v, (int,float)) and k not in ("total","samples"):
                    w.writerow([k, v, "", ""])
    return out.getvalue()

def build_markdown(run_id: str, rec) -> str:
    files = _load_run_files(run_id)
    manifest = files["manifest"]
    env = files["env"]
    result = files["result"]
    suite = rec.suite if hasattr(rec, "suite") else manifest.get("suite","")
    status = rec.status if hasattr(rec, "status") else "unknown"
    created = rec.created_at.isoformat() if hasattr(rec, "created_at") else ""
    lines = [
        f"# Run {run_id}",
        f"- **Suite:** {suite}",
        f"- **Status:** {status}",
        f"- **Created:** {created}",
        f"- **Recipe:** {manifest.get('recipe') or rec.recipe if hasattr(rec,'recipe') else '-'}",
        "",
        "## Config",
        "```json",
        json.dumps(files["resolved_config"], indent=2, ensure_ascii=False),
        "```",
        "",
        "## Result Summary",
        "```json",
        json.dumps(result, indent=2, ensure_ascii=False)[:4000],
        "```",
        "",
        "## Metrics",
        "| name | value | unit |",
        "|---|---|---|",
    ]
    for m in files["metrics"][:50]:
        lines.append(f"| {m.get('name')} | {m.get('value')} | {m.get('unit','')} |")
    if not files["metrics"]:
        lines.append("| (no normalized metrics) | - | - |")
    lines += ["", "## Environment", "```json", json.dumps(env, indent=2, ensure_ascii=False)[:3000], "```", "", f"_Exported {datetime.now().isoformat()} · GB10 LLM Bench_"]
    return "\n".join(lines)

def build_methodology(run_id: str, rec) -> str:
    files = _load_run_files(run_id)
    manifest = files["manifest"]
    env = files["env"]
    cfg = files["resolved_config"]
    suite = manifest.get("suite","")
    canon = canonical_environment(env)
    runtime_keys = ("managed", "server_url", "model_path", "n_gpu_layers", "flash_attn", "ctx_size", "batch_size", "ubatch_size", "parallel", "cache_policy", "warmup", "repetitions")
    runtime = " ".join(f"{key}={cfg[key]}" for key in runtime_keys if key in cfg)
    runtime = runtime or "(not recorded)"
    return "\n".join([
        f"# Methodology — {run_id}",
        f"**Suite:** {suite}  **Status:** {getattr(rec,'status','')}  **Date:** {getattr(rec,'created_at',datetime.now()).isoformat() if hasattr(rec,'created_at') else datetime.now().isoformat()}",
        "",
        "## Reproducibility",
        f"- Model: `{cfg.get('model_path','-')}`",
        f"- llama-bench: `{canon['llama_bench_path']}` (llama.cpp commit `{canon['llama_bench_commit']}`)",
        f"- llama-server: `{canon['llama_server_path']}` (version `{canon['llama_server_version']}`)",
        f"- llama.cpp/build commit: `{canon['llama_cpp_commit']}`",
        f"- Platform commit: `{canon['platform_commit']}`",
        f"- Runtime config: `{runtime}`",
        f"- OS: {canon['os']} / {canon['arch']} / CPU {canon['cpu']}",
        f"- GPU: {canon['gpu']}",
        f"- Cache policy: `{cfg.get('cache_policy', 'unspecified')}`; warmup=`{cfg.get('warmup', 'unspecified')}` (recorded configuration)",
        "",
        "## Procedure",
        "1. `capture_environment` → `environment.json`",
        "2. `RunManager` merges recipe + config → `manifest.json`",
        "3. `model_lock` serializes if `model_path` present (GB10 single host)",
        "4. Managed server (if `managed:true`) → configured health wait → run → auto-stop",
        "5. `BenchmarkRunner.run` → `result.json` + `samples.jsonl`/`metrics.jsonl` + `events.jsonl` (1s telemetry)",
        "",
        "## Evidence",
        f"- `runs/{run_id}/manifest.json` / `environment.json` / `result.json` / `samples.jsonl` / `events.jsonl`",
        "- SQLite `runs` + `run_metrics` (queryable)",
        "- Artifacts: coding `artifacts/coding/<id>/` with code/tests/logs",
        "",
        "## Interpretation",
        "- `llama-bench` PP/TG are engine microbenchmarks (no tok/sampling), label separately from server throughput",
        "- Server `aggregate_predicted_tps` vs per-request `decode_tps` vs latency P50/P95/P99 — do not mix",
        "- Knowledge/coding/tool/agent pass_rates are domain-separated, no universal score",
        "",
        "_Generated by GB10 LLM Bench export_",
    ])

def build_zip(run_id: str, rec) -> bytes:
    files = _load_run_files(run_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # core
        for name in ["manifest.json","recipe.yaml","resolved-config.yaml","environment.json","result.json","metrics.jsonl","samples.jsonl","events.jsonl"]:
            p = files["root"] / name
            if p.exists():
                z.write(p, f"{run_id}/{name}")
        # db bundle
        z.writestr(f"{run_id}/bundle.json", json.dumps(build_json_bundle(run_id, rec), indent=2, ensure_ascii=False))
        z.writestr(f"{run_id}/metrics.csv", build_csv_metrics(run_id))
        z.writestr(f"{run_id}/report.md", build_markdown(run_id, rec))
        z.writestr(f"{run_id}/methodology.md", build_methodology(run_id, rec))
        # artifacts subset (limit)
        for p in sorted(files["root"].rglob("*")):
            if p.is_file() and p.name not in ("manifest.json","recipe.yaml","resolved-config.yaml","environment.json","result.json","metrics.jsonl","samples.jsonl","events.jsonl"):
                # cap at 200 files / 20MB
                try:
                    if p.stat().st_size > 5_000_000:
                        continue
                    z.write(p, f"{run_id}/{p.relative_to(files['root'])}")
                except:
                    pass
                if len(z.namelist()) > 200:
                    break
    return buf.getvalue()
