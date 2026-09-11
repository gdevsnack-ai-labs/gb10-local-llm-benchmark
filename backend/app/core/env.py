from __future__ import annotations
import json
import os
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import psutil

from app.core.config import settings
from app.services.model_registry import infer_family, infer_quant, infer_tags


def _safe_run(cmd: list[str], timeout: int = 5) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return (r.stdout.strip() or r.stderr.strip())[:4000]
        return (r.stdout.strip() + r.stderr.strip())[:4000] or None
    except Exception:
        return None


def _git_commit(path: Path) -> str | None:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return None


def _resolve_binary(configured: str | None, default: str, candidate: Path) -> Path:
    """Resolve a configured tool, optionally using LLAMA_CPP_ROOT."""
    value = configured or default
    path = Path(value)
    if path.exists():
        return path.resolve()
    if path.name == Path(default).name and candidate.exists():
        return candidate.resolve()
    return path


def capture_environment(run_dir: Path, config: dict) -> dict:
    """Collect environment snapshot per FULL_DESIGN ch.20"""
    uname = platform.uname()
    mem = psutil.virtual_memory()
    # NVIDIA
    nvidia = _safe_run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], timeout=5)
    if nvidia is None:
        nvidia = _safe_run(["nvidia-smi"], timeout=5)
    cuda_env = {k: v for k, v in os.environ.items() if k.startswith("CUDA")}
    # llama.cpp build info
    llama_cpp_root = os.getenv("LLAMA_CPP_ROOT")
    bench_candidate = Path(llama_cpp_root) / "build/bin/llama-bench" if llama_cpp_root else Path("llama-bench")
    server_candidate = Path(llama_cpp_root) / "build/bin/llama-server" if llama_cpp_root else Path("llama-server")
    bench_resolved = _resolve_binary(None, settings.llama_bench, bench_candidate)
    llama_bench_path = str(bench_resolved)
    llama_help = _safe_run([llama_bench_path, "--help"], timeout=5)
    server_resolved = _resolve_binary(
        config.get("llama_server_bin"),
        settings.llama_server,
        server_candidate,
    )
    llama_server_path = str(server_resolved)
    llama_server_version = _safe_run([llama_server_path, "--version"], timeout=5)
    if not llama_server_version:
        llama_server_version = _safe_run([llama_server_path, "--help"], timeout=5)
    # try to find git commit for llama.cpp
    llama_cpp_commit = None
    candidates = [Path(llama_cpp_root)] if llama_cpp_root else []
    candidates.append(Path(llama_bench_path).parent.parent)
    for cand in candidates:
        if (cand / ".git").exists():
            llama_cpp_commit = _git_commit(cand)
            if llama_cpp_commit:
                break
    # platform commit
    platform_commit = _git_commit(Path(__file__).resolve().parents[3])
    if not platform_commit:
        platform_commit = _git_commit(settings.run_root.resolve() if settings.run_root.exists() else Path.cwd())
    # model stat
    model_path = config.get("model_path")
    model_stat = None
    if model_path:
        p = Path(model_path)
        if p.exists():
            try:
                st = p.stat()
                model_stat = {
                    "name": p.name,
                    "path": str(p),
                    "registry_id": str(p.as_posix()),
                    "sha256": None,
                    "size": st.st_size,
                    "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                    "variant": infer_family(p.name),
                    "quant": infer_quant(p.name),
                    "tags": infer_tags(p),
                }
                # sha256 is expensive for large GGUF, skip by default, record if small or explicitly requested
            except Exception as e:
                model_stat = {"path": str(p), "error": str(e)}
        else:
            model_stat = {"path": str(p), "exists": False}
    env = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "os": {"system": uname.system, "release": uname.release, "version": uname.version, "machine": uname.machine, "processor": uname.processor},
        "arch": uname.machine,
        "cpu": {"physical": psutil.cpu_count(logical=False), "logical": psutil.cpu_count(logical=True)},
        "memory": {"total": mem.total, "available": mem.available},
        "nvidia": nvidia,
        "cuda_env": cuda_env,
        "llama_bench": {"path": llama_bench_path, "resolved": str(bench_resolved), "commit": llama_cpp_commit, "help_head": (llama_help[:2000] if llama_help else None)},
        "llama_server": {"path": llama_server_path, "resolved": str(server_resolved), "commit": llama_cpp_commit, "version": (llama_server_version[:2000] if llama_server_version else None)},
        "platform_commit": platform_commit,
        "model": model_stat,
        "config": config,
    }
    # write file if run_dir given
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "environment.json").write_text(json.dumps(env, indent=2, ensure_ascii=False))
    except Exception:
        pass
    return env
