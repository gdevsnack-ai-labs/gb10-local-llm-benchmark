from __future__ import annotations
import asyncio
import json
from pathlib import Path

from app.core.config import settings
from app.runners.base import BenchmarkRunner, RunContext


def normalize_llama_bench_rows(rows: list[dict], run_id: str) -> list[dict]:
    """Normalize llama-bench JSON rows into metric records per FULL_DESIGN 19."""
    metrics: list[dict] = []
    for r in rows:
        # r contains fields per test::get_fields + samples_ns/samples_ts
        n_prompt = int(r.get("n_prompt", 0))
        n_gen = int(r.get("n_gen", 0))
        test_label = "pp" if n_prompt and not n_gen else "tg" if n_gen and not n_prompt else "pg" if n_prompt and n_gen else "unknown"
        # Determine tokens for t/s metric
        avg_ts = float(r.get("avg_ts", 0) or 0)
        std_ts = float(r.get("stddev_ts", 0) or 0)
        avg_ns = int(r.get("avg_ns", 0) or 0)
        # tokens per second metric name
        if test_label == "pp":
            name = "perf.prompt_tps"
            unit = "tokens/s"
        elif test_label == "tg":
            name = "perf.decode_tps"
            unit = "tokens/s"
        else:
            name = "perf.combined_tps"
            unit = "tokens/s"
        metrics.append({
            "name": name,
            "value": avg_ts,
            "unit": unit,
            "extra": {
                "run_id": run_id,
                "test": test_label,
                "n_prompt": n_prompt,
                "n_gen": n_gen,
                "n_batch": r.get("n_batch"),
                "n_ubatch": r.get("n_ubatch"),
                "n_threads": r.get("n_threads"),
                "flash_attn": r.get("flash_attn"),
                "build_commit": r.get("build_commit"),
                "model_filename": r.get("model_filename"),
                "model_type": r.get("model_type"),
                "avg_ns": avg_ns,
                "stddev_ns": int(r.get("stddev_ns", 0) or 0),
                "avg_ts": avg_ts,
                "stddev_ts": std_ts,
                "samples_ns": r.get("samples_ns"),
            },
        })
        # also latency metric
        if avg_ts and (n_prompt + n_gen) > 0:
            # avg latency = tokens / tps
            tokens = n_prompt + n_gen
            latency_ms = avg_ns / 1e6 if avg_ns else (tokens / avg_ts * 1000 if avg_ts else None)
            if latency_ms:
                metrics.append({
                    "name": "perf.request_latency_ms" if test_label != "pp" else "perf.prompt_latency_ms",
                    "value": latency_ms,
                    "unit": "ms",
                    "extra": {"test": test_label, "n_prompt": n_prompt, "n_gen": n_gen},
                })
    return metrics


def summarize_llama_bench_rows(rows: list[dict]) -> dict:
    """Expose formal PP/TG statistics while retaining the raw rows unchanged."""
    representative: dict[str, dict] = {}
    repetition_counts: set[int] = set()
    for row in rows:
        n_prompt = int(row.get("n_prompt", 0) or 0)
        n_gen = int(row.get("n_gen", 0) or 0)
        if n_prompt and not n_gen:
            key = f"pp_{n_prompt}"
        elif n_gen and not n_prompt:
            key = f"tg_{n_gen}"
        else:
            continue
        samples = list(row.get("samples_ts") or [])
        repetition_counts.add(len(samples))
        representative[key] = {
            "mean": float(row.get("avg_ts", 0) or 0),
            "stddev": float(row.get("stddev_ts", 0) or 0),
            "repetitions": samples,
            "n_prompt": n_prompt,
            "n_gen": n_gen,
            "unit": "tokens/s",
        }
    return {
        "repetitions": max(repetition_counts) if repetition_counts else 0,
        "representative": representative,
    }


class LlamaBenchRunner(BenchmarkRunner):
    name = "performance"

    async def run(self, ctx: RunContext) -> dict:
        c = ctx.config
        model = c.get("model_path")
        if not model:
            raise KeyError("model_path is required for performance suite")
        # validate model exists early for clearer error
        if not Path(model).exists():
            raise FileNotFoundError(f"model not found: {model}")
        prompt = c.get("prompt_tokens", [512, 2048])
        gen = c.get("gen_tokens", [128])
        reps = int(c.get("repetitions", 3))
        args = [settings.llama_bench, "-m", model, "-o", "json", "-r", str(reps)]
        for p in prompt:
            args += ["-p", str(p)]
        for n in gen:
            args += ["-n", str(n)]
        for flag, key in [("-b", "batch_size"), ("-ub", "ubatch_size")]:
            if key in c:
                args += [flag, str(c[key])]
        if "n_gpu_layers" in c:
            args += ["-ngl", str(c["n_gpu_layers"])]
        if c.get("flash_attn") is not None:
            args += ["-fa", "on" if c["flash_attn"] else "off"]
        # optional threads
        if "threads" in c:
            args += ["-t", str(c["threads"])]
        if "cache_type_k" in c:
            args += ["-ctk", str(c["cache_type_k"])]
        if "cache_type_v" in c:
            args += ["-ctv", str(c["cache_type_v"])]

        await ctx.emit("command", {"argv": args})
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        # cancellation-aware wait
        stdout = b""
        stderr = b""
        try:
            if ctx.cancel_event is not None:
                comm_task = asyncio.create_task(proc.communicate())
                cancel_task = asyncio.create_task(ctx.cancel_event.wait())
                done, pending = await asyncio.wait(
                    [comm_task, cancel_task], return_when=asyncio.FIRST_COMPLETED
                )
                if cancel_task in done:
                    proc.terminate()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                    comm_task.cancel()
                    try:
                        await comm_task
                    except asyncio.CancelledError:
                        pass
                    raise asyncio.CancelledError("llama-bench cancelled")
                else:
                    cancel_task.cancel()
                    try:
                        await cancel_task
                    except asyncio.CancelledError:
                        pass
                    stdout, stderr = comm_task.result()
            else:
                stdout, stderr = await proc.communicate()
        finally:
            # ensure logs written even on cancel
            try:
                (ctx.run_dir / "llama-bench.stderr.log").write_bytes(stderr or b"")
                (ctx.run_dir / "llama-bench.stdout.json").write_bytes(stdout or b"")
            except Exception:
                pass
        if proc.returncode != 0:
            # check if cancelled
            if ctx.cancel_event and ctx.cancel_event.is_set():
                raise asyncio.CancelledError("llama-bench cancelled")
            raise RuntimeError(f"llama-bench exited {proc.returncode}: {stderr.decode(errors='replace')[-2000:]}")
        try:
            rows = json.loads(stdout.decode() or "[]")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"llama-bench JSON parse failed: {e}: {stdout[:2000]!r}")
        if not isinstance(rows, list):
            rows = [rows]
        await ctx.emit("metric", {"rows": len(rows)})
        # emit per-row metric
        for r in rows:
            await ctx.emit("metric", {"test": f"{r.get('n_prompt',0)}/{r.get('n_gen',0)}", "avg_ts": r.get("avg_ts"), "avg_ns": r.get("avg_ns")})
        return {
            "kind": "llama-bench",
            "rows": rows,
            "formal_summary": summarize_llama_bench_rows(rows),
        }
