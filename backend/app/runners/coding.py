from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

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


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text.strip()


def _failure_type(returncode: int, output: str, timed_out: bool = False) -> str | None:
    if timed_out:
        return "timeout"
    if returncode == 0:
        return None
    if "SyntaxError" in output or "IndentationError" in output:
        return "syntax_error"
    if "ImportError" in output or "ModuleNotFoundError" in output:
        return "runtime_error"
    if "FAILED" in output or "AssertionError" in output:
        return "test_failure"
    return "runtime_error"


def _test_source(tests: str | list[str], function_name: str | None = None) -> str:
    if isinstance(tests, list):
        body_lines = "\n".join(tests).splitlines()
        body = "def test_generated_solution():\n"
        if function_name:
            body += f"    from solution import {function_name}\n"
        body += "\n".join((f"    {line}" if line.strip() else "") for line in body_lines)
        return body.rstrip() + "\n"
    body = tests
    if function_name and "from solution import" not in body:
        body = f"from solution import {function_name}\n\n{body}"
    return body.rstrip() + "\n"


def run_tests(workspace: Path, tests: str | list[str], entry: str = "solution.py", timeout: int = 5, function_name: str | None = None) -> dict:
    test_path = workspace / "test_solution.py"
    test_source = _test_source(tests, function_name)
    test_path.write_text(test_source, encoding="utf-8")
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v"],
            cwd=workspace, capture_output=True, text=True, timeout=timeout,
        )
        stdout, stderr = completed.stdout, completed.stderr
        combined = stdout + stderr
        return {
            "passed": completed.returncode == 0,
            "success": completed.returncode == 0,
            "returncode": completed.returncode,
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "output": combined[-3000:],
            "timed_out": False,
            "timeout": False,
            "failure_type": _failure_type(completed.returncode, combined),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        return {
            "passed": False, "success": False, "returncode": 124, "exit_code": 124,
            "stdout": stdout, "stderr": stderr, "output": "timeout", "timed_out": True,
            "timeout": True, "failure_type": "timeout",
        }
    except Exception as exc:
        message = str(exc)
        return {
            "passed": False, "success": False, "returncode": 1, "exit_code": 1,
            "stdout": "", "stderr": message, "output": message, "timed_out": False,
            "timeout": False, "failure_type": "runtime_error",
        }


def _resolve_dataset(dataset: str) -> Path:
    path = Path(dataset)
    if path.is_absolute() and path.exists():
        return path.resolve()
    for candidate in (settings.run_root.parent / path, settings.recipe_root.parent / path, path):
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"dataset not found: {dataset} (resolved {path})")


class CodingRunner(BenchmarkRunner):
    name = "coding"

    async def run(self, ctx: RunContext) -> dict:
        c = ctx.config
        dataset_name = c.get("dataset", "data/coding/sample-v1.jsonl")
        ds_path = _resolve_dataset(dataset_name)
        dataset_hash = hashlib.sha256(ds_path.read_bytes()).hexdigest()
        dataset_version = str(c.get("dataset_version", "1"))
        snapshot_path = ctx.run_dir / "dataset-snapshot.jsonl"
        snapshot_path.write_bytes(ds_path.read_bytes())
        url = c.get("server_url") or settings.llama_server_url
        thinking = normalize_thinking_config(c)
        max_tokens = int(c.get("max_tokens", 512))
        await ctx.emit("phase", {"name": "coding-load", "dataset": str(ds_path), "url": url, **thinking_metadata(c)})
        samples = []
        with ds_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    samples.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid dataset JSON at line {line_number}: {exc}") from exc
        if not samples:
            raise ValueError("no samples in dataset")
        await ctx.emit("phase", {"name": "coding-start", "count": len(samples)})

        results = []
        total_pass = 0
        failure_types: dict[str, int] = {}
        async with httpx.AsyncClient(base_url=url, timeout=thinking.request_timeout_s) as client:
            try:
                health = await client.get("/health", timeout=5)
                health.raise_for_status()
            except Exception as exc:
                raise RuntimeError(f"server health failed at {url}: {exc}") from exc
            for idx, sample in enumerate(samples):
                if ctx.cancel_event and ctx.cancel_event.is_set():
                    raise asyncio.CancelledError("coding cancelled")
                prompt = sample["prompt"]
                entry = sample.get("entry", "solution.py")
                tests = sample["tests"]
                timeout = int(sample.get("timeout", c.get("test_timeout_s", 10)))
                started = time.perf_counter()
                output, reasoning, reasoning_tokens = "", "", None
                extraction_error = None
                try:
                    response = await client.post("/v1/chat/completions", json=build_chat_payload(
                        [{"role": "user", "content": prompt}], c,
                        max_tokens=max_tokens, temperature=c.get("temperature", 0.2),
                    ))
                    if response.status_code == 200:
                        body = response.json()
                        output, reasoning, _ = extract_chat_message(body)
                        reasoning_tokens = extract_reasoning_tokens(body)
                    if not output.strip():
                        response = await client.post("/completion", json={"prompt": prompt, "n_predict": max_tokens, "temperature": 0.2, "stream": False})
                        response.raise_for_status()
                        body = response.json()
                        raw_output = body.get("content", "") or body.get("completion", "") or ""
                        output, reasoning, _ = extract_chat_message({"choices": [{"message": {"content": raw_output}}]})
                        reasoning_tokens = extract_reasoning_tokens(body)
                except Exception as exc:
                    extraction_error = str(exc)
                    output = f"ERROR: {exc}"
                try:
                    code = extract_code(output)
                    if not code:
                        raise ValueError("empty generated code")
                except Exception as exc:
                    code = ""
                    extraction_error = str(exc)
                workspace = ctx.run_dir / "artifacts" / "coding" / sample["id"]
                workspace.mkdir(parents=True, exist_ok=True)
                (workspace / entry).write_text(code, encoding="utf-8")
                (workspace / "prompt.txt").write_text(prompt, encoding="utf-8")
                (workspace / "task.json").write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")
                (workspace / "raw_output.txt").write_text(output, encoding="utf-8")
                test_res = run_tests(workspace, tests, entry, timeout=timeout, function_name=sample.get("function_name"))
                (workspace / "test_solution.py").write_text(_test_source(tests, sample.get("function_name")), encoding="utf-8")
                (workspace / "pytest_stdout.txt").write_text(test_res["stdout"], encoding="utf-8")
                (workspace / "pytest_stderr.txt").write_text(test_res["stderr"], encoding="utf-8")
                (workspace / "test_output.txt").write_text(test_res["output"], encoding="utf-8")
                passed = test_res["passed"] and extraction_error is None
                failure_type = None if passed else ("extraction_error" if extraction_error else test_res["failure_type"])
                if passed:
                    total_pass += 1
                elif failure_type:
                    failure_types[failure_type] = failure_types.get(failure_type, 0) + 1
                result = {
                    "id": sample["id"], "category": sample.get("category", "unknown"),
                    "function_name": sample.get("function_name"), "signature": sample.get("signature"),
                    "prompt": prompt, "generated_code": code, "code": code,
                    "extraction_error": extraction_error, "pytest_exit_code": test_res["exit_code"],
                    "passed": passed, "pass": passed, "stdout": test_res["stdout"],
                    "stderr": test_res["stderr"], "test_output": test_res["output"],
                    "timeout": test_res["timeout"], "timed_out": test_res["timed_out"],
                    "failure_type": failure_type, "reasoning_preview": reasoning[:1000],
                    "reasoning_tokens": reasoning_tokens, "elapsed_s": time.perf_counter() - started,
                    "artifact_path": str(workspace),
                }
                results.append(result)
                await ctx.emit("progress", {"completed": idx + 1, "total": len(samples), "passed": total_pass, "sample": result})

        categories = {}
        for result in results:
            summary = categories.setdefault(result["category"], {"total": 0, "passed": 0})
            summary["total"] += 1
            summary["passed"] += int(result["passed"])
        for summary in categories.values():
            summary["pass_rate"] = summary["passed"] / summary["total"] if summary["total"] else 0
        (ctx.run_dir / "samples.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in results) + "\n", encoding="utf-8")
        return {
            "kind": "coding", "version": 1, **thinking_metadata(c),
            "dataset_provenance": {"path": str(ds_path), "version": dataset_version, "sha256": dataset_hash, "snapshot": str(snapshot_path)},
            "total": len(samples), "passed": total_pass, "pass_rate": total_pass / len(samples),
            "categories": categories, "failure_types": failure_types, "samples": results,
        }
