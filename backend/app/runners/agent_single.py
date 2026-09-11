from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path

import httpx

from app.core.config import settings
from app.runners.base import BenchmarkRunner, RunContext
from app.runners.reasoning import build_chat_payload, extract_chat_message, extract_reasoning_tokens, normalize_thinking_config, thinking_metadata
from app.runners.tool_call import TOOLS_DEF, parse_tool_call, simulator

SYSTEM_PROMPT = (
    "You are a helpful single agent. Use the available tools when needed, feed each tool result into the next step, "
    "and continue until the task is complete. Available tools: calculator, kv_get, kv_lookup, read_file. "
    "When done, provide the final answer."
)


def extract_final(text: str) -> str:
    match = re.search(r"FINAL:\s*(.+)", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else text.strip()


def _resolve_dataset(dataset: str) -> Path:
    path = Path(dataset)
    if path.is_absolute() and path.exists():
        return path.resolve()
    for candidate in (settings.run_root.parent / path, settings.recipe_root.parent / path, path):
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"dataset not found: {dataset} (resolved {path})")


def score_agent_task(sample: dict, tool_calls: list[dict], final_answer: str, steps: int, max_steps: int) -> dict:
    expected = sample.get("expected") or {"sequence": sample.get("expected_tools", []), "final": sample.get("expected_answer", "")}
    expected_sequence = expected.get("sequence") or expected.get("required_tools") or sample.get("expected_tools", [])
    successful_calls = [call for call in tool_calls if call.get("execution", {}).get("error") is None]
    actual_sequence = [call.get("name") for call in successful_calls]
    sequence_correct = actual_sequence == expected_sequence
    failed_calls = sum(1 for call in tool_calls if call.get("execution", {}).get("error"))
    repeated_calls = sum(1 for left, right in zip(actual_sequence, actual_sequence[1:]) if left == right)
    if "final" in expected:
        target = str(expected["final"]).casefold()
        final_success = target in final_answer.casefold()
    elif expected.get("final_type") == "numeric":
        final_success = bool(re.search(r"[-+]?\d+(?:\.\d+)?", final_answer))
    else:
        final_success = bool(final_answer.strip())
    task_complete = sequence_correct and final_success
    if task_complete:
        failure_type = None
    elif failed_calls:
        failure_type = "tool_error"
    elif repeated_calls and (len(actual_sequence) > len(expected_sequence) or steps >= max_steps):
        failure_type = "repeated_loop"
    elif not actual_sequence:
        failure_type = "missing_required_step"
    elif steps >= max_steps and not final_answer:
        failure_type = "max_steps_exceeded"
    elif len(actual_sequence) < len(expected_sequence):
        failure_type = "missing_required_step"
    elif not sequence_correct:
        failure_type = "wrong_tool"
    else:
        failure_type = "final_answer_error"
    return {
        "task_complete": task_complete, "sequence_correct": sequence_correct,
        "failed_tool_calls": failed_calls, "repeated_tool_calls": repeated_calls,
        "final_success": final_success, "failure_type": failure_type,
    }


class AgentSingleRunner(BenchmarkRunner):
    name = "agent-single"

    async def run(self, ctx: RunContext) -> dict:
        c = {**ctx.config, "thinking_mode": "no-think", "thinking_budget": 0}
        ctx.config.update({"thinking_mode": "no-think", "thinking_budget": 0})
        dataset_name = c.get("dataset", "data/agent/single-v1.jsonl")
        ds_path = _resolve_dataset(dataset_name)
        dataset_hash = hashlib.sha256(ds_path.read_bytes()).hexdigest()
        snapshot = ctx.run_dir / "dataset-snapshot.jsonl"
        snapshot.write_bytes(ds_path.read_bytes())
        max_steps_default = int(c.get("max_steps", 6))
        url = c.get("server_url") or settings.llama_server_url
        thinking = normalize_thinking_config(c)
        max_tokens = int(c.get("max_tokens", 256))
        await ctx.emit("phase", {"name": "agent-load", "dataset": str(ds_path), "url": url, "max_steps": max_steps_default, **thinking_metadata(c)})
        samples = []
        with ds_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    try: samples.append(json.loads(line))
                    except json.JSONDecodeError as exc: raise ValueError(f"invalid dataset JSON at line {line_number}: {exc}") from exc
        if not samples: raise ValueError("no samples in dataset")
        await ctx.emit("phase", {"name": "agent-start", "count": len(samples)})
        results, failure_types = [], {}
        total_steps = total_tool_calls = total_failed_calls = total_repeated_calls = correct = 0
        reasoning_tokens_total = reasoning_token_samples = 0
        async with httpx.AsyncClient(base_url=url, timeout=thinking.request_timeout_s) as client:
            try:
                health = await client.get("/health", timeout=5); health.raise_for_status()
            except Exception as exc: raise RuntimeError(f"server health failed at {url}: {exc}") from exc
            for index, sample in enumerate(samples):
                if ctx.cancel_event and ctx.cancel_event.is_set(): raise asyncio.CancelledError("agent-single cancelled")
                steps = 0; messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": sample["prompt"]}]
                trace, raw_responses, tool_calls, final_text = [], [], [], ""
                max_steps = int(sample.get("max_steps", max_steps_default))
                started = time.perf_counter()
                for step in range(max_steps):
                    steps += 1
                    try:
                        response = await client.post("/v1/chat/completions", json=build_chat_payload(messages, c, max_tokens=max_tokens, temperature=0, tools=TOOLS_DEF, tool_choice="auto"))
                        response.raise_for_status(); body = response.json(); raw_responses.append(body)
                    except Exception as exc:
                        trace.append({"step": step, "role": "error", "content": str(exc)}); break
                    choices = body.get("choices") or []
                    if not choices:
                        trace.append({"step": step, "role": "error", "content": "no choices"}); break
                    message = choices[0].get("message") or {}; content, reasoning, _ = extract_chat_message(body)
                    reasoning_tokens = extract_reasoning_tokens(body)
                    if reasoning_tokens is not None: reasoning_tokens_total += reasoning_tokens; reasoning_token_samples += 1
                    tool_payloads = message.get("tool_calls") or []
                    trace.append({"step": step, "role": "assistant", "content": content, "reasoning": reasoning[:1000], "reasoning_tokens": reasoning_tokens, "tool_calls": tool_payloads})
                    if not tool_payloads and content:
                        parsed_name, parsed_args = parse_tool_call(content)
                        if parsed_name and parsed_args is not None:
                            tool_payloads = [{"id": f"parsed-{step}", "function": {"name": parsed_name, "arguments": json.dumps(parsed_args)}}]
                    if tool_payloads:
                        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_payloads})
                        tool_payload = tool_payloads[0]; function = tool_payload.get("function", {}); name = function.get("name")
                        try: args = json.loads(function.get("arguments") or "{}")
                        except Exception: args = {}
                        execution = simulator(name, args)
                        call = {"name": name, "arguments": args, "execution": execution, "call_id": tool_payload.get("id")}
                        tool_calls.append(call)
                        trace.append({"step": step, "role": "tool", "tool": name, "arguments": args, "result": execution})
                        messages.append({"role": "tool", "tool_call_id": tool_payload.get("id", f"call-{step}"), "name": name, "content": json.dumps(execution, ensure_ascii=False)})
                        continue
                    final_text = content; break
                final_answer = extract_final(final_text) if final_text else ""
                scoring = score_agent_task(sample, tool_calls, final_answer, steps, max_steps)
                correct += int(scoring["task_complete"]); total_steps += steps; total_tool_calls += len(tool_calls); total_failed_calls += scoring["failed_tool_calls"]; total_repeated_calls += scoring["repeated_tool_calls"]
                if scoring["failure_type"]: failure_types[scoring["failure_type"]] = failure_types.get(scoring["failure_type"], 0) + 1
                artifact = ctx.run_dir / "artifacts" / "agent-single" / sample["id"]; artifact.mkdir(parents=True, exist_ok=True)
                (artifact / "task.json").write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")
                (artifact / "raw_responses.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in raw_responses) + "\n", encoding="utf-8")
                (artifact / "agent_trace.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in trace) + "\n", encoding="utf-8")
                (artifact / "tool_calls.json").write_text(json.dumps(tool_calls, indent=2, ensure_ascii=False), encoding="utf-8")
                (artifact / "final_answer.txt").write_text(final_answer, encoding="utf-8")
                (artifact / "scoring.json").write_text(json.dumps(scoring, indent=2, ensure_ascii=False), encoding="utf-8")
                result = {"id": sample["id"], "category": sample.get("category", "unknown"), "prompt": sample["prompt"], "steps": steps, "tool_call_count": len(tool_calls), "tool_calls": tool_calls, "tool_sequence": [call["name"] for call in tool_calls], "tool_results": [call["execution"] for call in tool_calls], "raw_model_responses": raw_responses, "trace": trace, "final_text": final_text, "final_answer": final_answer, "correct": scoring["task_complete"], "pass": scoring["task_complete"], "failure_type": scoring["failure_type"], "failed_tool_calls": scoring["failed_tool_calls"], "repeated_tool_calls": scoring["repeated_tool_calls"], "elapsed_s": time.perf_counter() - started, "artifact_path": str(artifact)}
                results.append(result)
                await ctx.emit("progress", {"completed": index + 1, "total": len(samples), "correct": correct, "sample": result})
        categories = {}
        for result in results:
            summary = categories.setdefault(result["category"], {"total": 0, "passed": 0}); summary["total"] += 1; summary["passed"] += int(result["correct"])
        for summary in categories.values(): summary["pass_rate"] = summary["passed"] / summary["total"]
        (ctx.run_dir / "samples.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in results) + "\n", encoding="utf-8")
        return {"kind": "agent-single", "version": 1.1, **thinking_metadata(c), "dataset_provenance": {"path": str(ds_path), "version": str(c.get("dataset_version", "1")), "sha256": dataset_hash, "snapshot": str(snapshot)}, "total": len(samples), "passed": correct, "correct": correct, "pass_rate": correct / len(samples), "categories": categories, "avg_steps": total_steps / len(samples), "avg_tool_calls": total_tool_calls / len(samples), "tool_calls_total": total_tool_calls, "failed_tool_calls": total_failed_calls, "repeated_tool_calls": total_repeated_calls, "failure_types": failure_types, "reasoning_tokens_total": reasoning_tokens_total if reasoning_token_samples else None, "reasoning_token_samples": reasoning_token_samples, "dataset": str(ds_path), "samples": results}
