from __future__ import annotations

import asyncio
import json
import math
import statistics
import time
from typing import Any

import httpx

from app.core.config import settings
from app.runners.base import BenchmarkRunner, RunContext
from app.runners.reasoning import (
    build_chat_payload,
    extract_chat_message,
    extract_reasoning_tokens,
    normalize_thinking_config,
    thinking_metadata,
)


class ServerPerformanceRunner(BenchmarkRunner):
    name = "server-performance"

    async def _check_health(self, client: httpx.AsyncClient) -> dict:
        try:
            r = await client.get("/health", timeout=5)
            r.raise_for_status()
            return {"ok": True, "body": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _slots(self, client: httpx.AsyncClient) -> Any:
        try:
            r = await client.get("/slots", timeout=3)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    async def _metrics(self, client: httpx.AsyncClient) -> str | None:
        try:
            r = await client.get("/metrics", timeout=3)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return None

    async def _one(self, client: httpx.AsyncClient, prompt: str, n_predict: int, cache_prompt: bool, config: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        thinking = normalize_thinking_config(config)
        endpoint = "/v1/chat/completions" if thinking.mode != "auto" else "/completion"
        try:
            if thinking.mode != "auto":
                payload = build_chat_payload([{"role": "user", "content": prompt}], config, max_tokens=n_predict, temperature=0)
                r = await client.post(endpoint, json=payload)
                r.raise_for_status()
                body = r.json()
                answer, reasoning, _ = extract_chat_message(body)
            else:
                r = await client.post(endpoint, json={"prompt": prompt, "n_predict": n_predict, "temperature": 0, "cache_prompt": cache_prompt, "stream": False})
                r.raise_for_status()
                body = r.json()
                raw_output = body.get("content", "") or body.get("completion", "") or ""
                answer, reasoning, _ = extract_chat_message({"choices": [{"message": {"content": raw_output}}]})
            elapsed = time.perf_counter() - started
            timings = body.get("timings", {})
            predicted_tokens = timings.get("predicted_n")
            return {
                "elapsed_s": elapsed,
                "latency_s": elapsed,
                "endpoint": endpoint,
                "prompt_tokens": timings.get("prompt_n"),
                "prompt_ms": timings.get("prompt_ms"),
                "prompt_tps": timings.get("prompt_per_second"),
                "predicted_tokens": predicted_tokens,
                "predicted_ms": timings.get("predicted_ms"),
                "predicted_tps": timings.get("predicted_per_second"),
                "per_request_generation_tps": (predicted_tokens / elapsed) if predicted_tokens is not None and elapsed > 0 else None,
                "reasoning_tokens": extract_reasoning_tokens(body),
                "reasoning_chars": len(reasoning),
                "output_chars": len(answer),
                "output": answer[:2000],
                "reasoning_preview": reasoning[:2000],
                "error": None,
            }
        except Exception as e:
            elapsed = time.perf_counter() - started
            return {"elapsed_s": elapsed, "latency_s": elapsed, "endpoint": endpoint, "error": str(e), "prompt_tokens": None, "predicted_tokens": None, "reasoning_tokens": None, "reasoning_chars": 0, "output_chars": 0, "per_request_generation_tps": None}

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        if len(ordered) == 1:
            return ordered[0]
        rank = (len(ordered) - 1) * percentile / 100
        lower, upper = math.floor(rank), math.ceil(rank)
        if lower == upper:
            return ordered[lower]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)

    @classmethod
    def _stats(cls, values: list[float]) -> dict[str, float | None]:
        return {
            "mean": statistics.mean(values) if values else None,
            "stddev": statistics.stdev(values) if len(values) > 1 else 0.0 if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }

    async def _batch(self, client: httpx.AsyncClient, ctx: RunContext, prompt: str, n_predict: int, cache_prompt: bool, config: dict[str, Any], concurrency: int, requests: int, repetition: int, slots_samples: list[Any], metrics_samples: list[str]) -> dict[str, Any]:
        sem = asyncio.Semaphore(concurrency)
        done = 0
        failed = 0
        started = time.perf_counter()

        async def task(i: int):
            nonlocal done, failed
            async with sem:
                if ctx.cancel_event and ctx.cancel_event.is_set():
                    raise asyncio.CancelledError("server-perf cancelled")
                sample = await self._one(client, prompt, n_predict, cache_prompt, config)
                sample.update({"concurrency": concurrency, "repetition": repetition, "request_index": i})
                done += 1
                if sample.get("error"):
                    failed += 1
                await ctx.emit("progress", {"concurrency": concurrency, "repetition": repetition, "completed": done, "total": requests, "sample": sample, "failed": failed})
                return sample

        samples = await asyncio.gather(*(task(i) for i in range(requests)))
        wall = time.perf_counter() - started
        ok = [s for s in samples if not s.get("error")]
        latencies = [s["latency_s"] for s in samples]
        predicted = sum(s.get("predicted_tokens") or 0 for s in ok)
        per_request = [s["per_request_generation_tps"] for s in ok if s.get("per_request_generation_tps") is not None]
        failed = len(samples) - len(ok)
        result = {
            "concurrency": concurrency,
            "repetition": repetition,
            "requests": requests,
            "successful_requests": len(ok),
            "failed_requests": failed,
            "failure_rate": failed / requests if requests else None,
            "total_wall_time_s": wall,
            "aggregate_generation_throughput_tps": predicted / wall if wall else None,
            "per_request_generation_throughput_tps": self._stats(per_request),
            "latency_s": self._stats(latencies),
            "latency_p50_s": self._percentile(latencies, 50),
            "latency_p95_s": self._percentile(latencies, 95),
            "latency_p99_s": self._percentile(latencies, 99),
            "prompt_processing_throughput_tps": self._stats([s["prompt_tps"] for s in ok if s.get("prompt_tps") is not None]),
            "samples": samples,
            "slots_samples": len(slots_samples),
        }
        return result

    async def run(self, ctx: RunContext) -> dict[str, Any]:
        c = ctx.config
        url = c.get("server_url", settings.llama_server_url)
        concurrency_values = c.get("concurrencies")
        formal = concurrency_values is not None
        if formal:
            concurrency_values = [int(x) for x in concurrency_values]
            repetitions = int(c.get("repetitions", 1))
            requests_per_concurrency = int(c.get("requests_per_concurrency", 4))
        else:
            concurrency_values = [int(c.get("concurrency", 1))]
            repetitions = 1
            requests_per_concurrency = None
        n_predict = int(c.get("gen_tokens", 128))
        prompt = c.get("prompt", "Benchmark prompt. " * 256)
        cache_prompt = bool(c.get("cache_prompt", False))
        thinking = normalize_thinking_config(c)
        await ctx.emit("phase", {"name": "server-load", "concurrencies": concurrency_values, "repetitions": repetitions, "requests_per_concurrency": requests_per_concurrency, **thinking_metadata(c)})
        limits = httpx.Limits(max_connections=max(concurrency_values), max_keepalive_connections=max(concurrency_values))
        async with httpx.AsyncClient(base_url=url, timeout=thinking.request_timeout_s, limits=limits) as client:
            health = await self._check_health(client)
            await ctx.emit("health", health)
            if not health.get("ok"):
                raise RuntimeError(f"llama-server health check failed at {url}: {health.get('error')}")
            poll_stop = asyncio.Event()
            slots_samples: list[Any] = []
            metrics_samples: list[str] = []

            async def poll_slots():
                while not poll_stop.is_set():
                    slots = await self._slots(client)
                    if slots is not None:
                        slots_samples.append(slots)
                        await ctx.emit("slots", {"slots": slots})
                    metrics = await self._metrics(client)
                    if metrics is not None:
                        metrics_samples.append(metrics[:2000])
                        await ctx.emit("metrics", {"metrics_head": metrics[:1000]})
                    try:
                        await asyncio.wait_for(poll_stop.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass

            poll_task = asyncio.create_task(poll_slots())
            all_samples: list[dict[str, Any]] = []
            condition_results: list[dict[str, Any]] = []
            try:
                for concurrency in concurrency_values:
                    repetition_results = []
                    for repetition in range(1, repetitions + 1):
                        requests = int((requests_per_concurrency or 4) * concurrency if formal else (c.get("requests") or concurrency))
                        batch = await self._batch(client, ctx, prompt, n_predict, cache_prompt, c, concurrency, requests, repetition, slots_samples, metrics_samples)
                        repetition_results.append(batch)
                        all_samples.extend(batch["samples"])
                    if formal:
                        aggregate_tps = [x["aggregate_generation_throughput_tps"] for x in repetition_results if x["aggregate_generation_throughput_tps"] is not None]
                        p50 = [x["latency_p50_s"] for x in repetition_results if x["latency_p50_s"] is not None]
                        p95 = [x["latency_p95_s"] for x in repetition_results if x["latency_p95_s"] is not None]
                        p99 = [x["latency_p99_s"] for x in repetition_results if x["latency_p99_s"] is not None]
                        walls = [x["total_wall_time_s"] for x in repetition_results]
                        per_request_tps = [s["per_request_generation_tps"] for x in repetition_results for s in x["samples"] if s.get("per_request_generation_tps") is not None]
                        failed = sum(x["failed_requests"] for x in repetition_results)
                        total = sum(x["requests"] for x in repetition_results)
                        condition_results.append({"concurrency": concurrency, "requests_per_repetition": int((requests_per_concurrency or 4) * concurrency) if formal else repetition_results[0]["requests"], "request_multiplier": requests_per_concurrency if formal else None, "repetitions": repetitions, "successful_requests": total - failed, "failed_requests": failed, "failure_rate": failed / total if total else None, "aggregate_generation_throughput_tps": self._stats(aggregate_tps), "per_request_generation_throughput_tps": self._stats(per_request_tps), "total_wall_time_s": self._stats(walls), "latency_p50_s": self._stats(p50), "latency_p95_s": self._stats(p95), "latency_p99_s": self._stats(p99), "repetitions_raw": repetition_results})
                    else:
                        condition_results.append({"concurrency": concurrency, "repetitions_raw": repetition_results})
            finally:
                poll_stop.set()
                await poll_task
                final_slots = await self._slots(client)
                if final_slots is not None:
                    await ctx.emit("slots", {"slots": final_slots, "final": True})
            (ctx.run_dir / "samples.jsonl").write_text("\n".join(json.dumps(sample, ensure_ascii=False) for sample in all_samples) + "\n", encoding="utf-8")
            if ctx.cancel_event and ctx.cancel_event.is_set():
                raise asyncio.CancelledError("server-perf cancelled")
        if formal:
            return {"kind": "server-performance", "version": 1, "formal": True, **thinking_metadata(c), "reasoning_tokens_total": sum(s["reasoning_tokens"] for s in all_samples if s.get("reasoning_tokens") is not None) if any(s.get("reasoning_tokens") is not None for s in all_samples) else None, "concurrencies": concurrency_values, "requests_per_concurrency": requests_per_concurrency, "gen_tokens": n_predict, "prompt": prompt, "repetitions": repetitions, "conditions": condition_results, "samples_count": len(all_samples), "slots_samples": len(slots_samples), "health": health}
        batch = condition_results[0]["repetitions_raw"] if condition_results else []
        one = batch[0] if batch else {"failed_requests": 0, "total_wall_time_s": 0, "aggregate_generation_throughput_tps": None, "latency_p50_s": None, "latency_p95_s": None, "latency_p99_s": None}
        return {"kind": "server-performance", **thinking_metadata(c), "reasoning_tokens_total": sum(s["reasoning_tokens"] for s in all_samples if s.get("reasoning_tokens") is not None) if any(s.get("reasoning_tokens") is not None for s in all_samples) else None, "concurrency": concurrency_values[0], "requests": one.get("requests"), "failed": one.get("failed_requests"), "wall_s": one.get("total_wall_time_s"), "aggregate_predicted_tps": one.get("aggregate_generation_throughput_tps"), "latency_mean_s": (one.get("latency_s") or {}).get("mean"), "latency_p50_s": one.get("latency_p50_s"), "latency_p95_s": one.get("latency_p95_s"), "latency_p99_s": one.get("latency_p99_s"), "samples": all_samples, "slots_samples": len(slots_samples), "health": health}
