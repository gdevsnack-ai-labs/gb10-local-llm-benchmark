from __future__ import annotations
import asyncio
import json
import os
import time
from pathlib import Path
from datetime import datetime, timezone
import httpx

from app.runners.reasoning import build_server_reasoning_args


class ManagedServer:
    def __init__(self, url: str, proc: asyncio.subprocess.Process, log_path: Path, model: str):
        self.url = url
        self.proc = proc
        self.log_path = log_path
        self.model = model
        self.started_at = datetime.now(timezone.utc)

    async def wait_health(self, timeout: int = 90) -> bool:
        deadline = time.time() + timeout
        async with httpx.AsyncClient(timeout=5) as client:
            while time.time() < deadline:
                try:
                    r = await client.get(f"{self.url}/health")
                    if r.status_code == 200:
                        return True
                except Exception:
                    pass
                await asyncio.sleep(0.5)
                # if proc died
                if self.proc.returncode is not None:
                    return False
        return False

    async def stop(self):
        if self.proc.returncode is None:
            try:
                self.proc.terminate()
                try:
                    await asyncio.wait_for(self.proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.proc.kill()
                    await self.proc.wait()
            except Exception:
                pass


class ServerManager:
    def __init__(self):
        self.current: ManagedServer | None = None
        self.lock = asyncio.Lock()

    async def start(self, run_dir: Path, config: dict, emit=None) -> ManagedServer:
        async with self.lock:
            # stop existing if any and model differs or forced
            if self.current:
                await self.stop()
            model = config.get("model_path") or config.get("model")
            if not model:
                raise ValueError("model_path required for managed server")
            # MTP-packaged GGUFs need their embedded draft block loaded.
            if not config.get("spec_type") and not config.get("spec") and "MTP" in Path(model).name.upper():
                config["spec_type"] = "mtp"
                config.setdefault("spec_draft_n_max", 3)
            host = config.get("host") or os.getenv("LLMBENCH_SERVER_HOST")
            port_value = config.get("port") or os.getenv("LLMBENCH_MANAGED_SERVER_PORT")
            if not host or not port_value:
                raise ValueError("managed server host and port must be configured")
            port = int(port_value)
            url = f"http://{host}:{port}"
            bin_path = config.get("llama_server_bin") or "llama-server"
            llama_cpp_root = os.getenv("LLAMA_CPP_ROOT")
            candidate = Path(llama_cpp_root) / "build/bin/llama-server" if llama_cpp_root else None
            if bin_path == "llama-server" and candidate and candidate.exists():
                bin_path = str(candidate)
            # build args
            args = [bin_path, "-m", model, "--host", host, "--port", str(port)]
            # common preset mapping
            if "ctx_size" in config:
                args += ["--ctx-size", str(config["ctx_size"])]
            elif "ctx_size" not in config:
                args += ["--ctx-size", "8192"]
            if "n_gpu_layers" in config:
                args += ["--n-gpu-layers", str(config["n_gpu_layers"])]
            else:
                args += ["--n-gpu-layers", "999"]
            if config.get("flash_attn") is not None:
                args += ["--flash-attn", "on" if config["flash_attn"] else "off"]
            # batch
            if "batch_size" in config:
                args += ["--batch-size", str(config["batch_size"])]
            if "ubatch_size" in config:
                args += ["--ubatch-size", str(config["ubatch_size"])]
            # mmproj
            if "mmproj" in config:
                args += ["--mmproj", str(config["mmproj"])]
            # threads
            if "threads" in config:
                args += ["--threads", str(config["threads"])]
            # enable metrics/slots
            args += ["--metrics", "--slots"]
            # parallel slots
            if "parallel" in config:
                args += ["--parallel", str(config["parallel"])]
            # extra args passthrough
            for k in ["cache_type_k", "cache_type_v"]:
                if k in config:
                    flag = "--cache-type-k" if k == "cache_type_k" else "--cache-type-v"
                    args += [flag, str(config[k])]
            # speculative decoding
            spec_type = config.get("spec_type") or config.get("spec")
            if spec_type and str(spec_type) not in ("off", "none"):
                # map friendly names
                mapping = {
                    "ngram": "ngram-simple",
                    "ngram-simple": "ngram-simple",
                    "ngram-mod": "ngram-mod",
                    "mtp": "draft-mtp",
                    "draft-mtp": "draft-mtp",
                    "dflash": "draft-dflash",
                    "draft-dflash": "draft-dflash",
                    "eagle3": "draft-eagle3",
                }
                st = mapping.get(str(spec_type), str(spec_type))
                args += ["--spec-type", st]
                # ngram extra
                if st.startswith("ngram"):
                    if "spec_ngram_min" in config:
                        args += ["--spec-ngram-mod-n-min", str(config["spec_ngram_min"])]
                    if "spec_ngram_max" in config:
                        args += ["--spec-ngram-mod-n-max", str(config["spec_ngram_max"])]
                # draft model for mtp/dflash
                if st.startswith("draft"):
                    draft = config.get("draft_model") or config.get("spec_draft_model")
                    if draft:
                        args += ["--spec-draft-model", str(draft)]
                    if "spec_draft_n_max" in config:
                        args += ["--spec-draft-n-max", str(config["spec_draft_n_max"])]
                    if "spec_draft_p_min" in config:
                        args += ["--spec-draft-p-min", str(config["spec_draft_p_min"])]
            elif spec_type in ("off", "none"):
                args += ["--spec-type", "none"]
            # reasoning/thinking mode is a server-level setting for managed runs
            args += build_server_reasoning_args(config)
            if emit:
                await emit("phase", {"name": "server-start", "argv": args, "url": url})
            run_dir.mkdir(parents=True, exist_ok=True)
            log_path = run_dir / "llama-server.log"
            log_file = open(log_path, "wb")
            proc = await asyncio.create_subprocess_exec(
                *args, stdout=log_file, stderr=asyncio.subprocess.STDOUT
            )
            server = ManagedServer(url, proc, log_path, model)
            ok = await server.wait_health(timeout=90)
            if not ok:
                # capture log tail
                try:
                    log_file.flush()
                    tail = open(log_path).read()[-3000:]
                except Exception:
                    tail = ""
                await server.stop()
                raise RuntimeError(f"managed server failed to become healthy at {url}. log tail: {tail[-1000:]}")
            self.current = server
            if emit:
                await emit("phase", {"name": "server-ready", "url": url})
            return server

    async def stop(self):
        if self.current:
            try:
                await self.current.stop()
            finally:
                self.current = None

    def get_url(self) -> str | None:
        return self.current.url if self.current else None

    def is_running(self) -> bool:
        return self.current is not None and self.current.proc.returncode is None


server_manager = ServerManager()
