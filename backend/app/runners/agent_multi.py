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

SYSTEM_MULTI = (
    "You are a multi-agent system with Researcher and Calculator roles. Researcher handles kv_get, kv_lookup, and read_file; "
    "Calculator handles calculator. Pass every tool result to the next role, record the handoff, and continue until the task is complete. "
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
    if path.is_absolute() and path.exists(): return path.resolve()
    for candidate in (settings.run_root.parent / path, settings.recipe_root.parent / path, path):
        if candidate.exists(): return candidate.resolve()
    raise FileNotFoundError(f"dataset not found: {dataset} (resolved {path})")


def role_for_tool(name: str | None) -> str:
    return "researcher" if name in {"kv_get", "kv_lookup", "read_file"} else "calculator"


def calculate_handoff_success_rate(successful_handoffs: int, expected_handoffs: int) -> float:
    """Return the task-level handoff success ratio, never a raw transition ratio."""
    if expected_handoffs <= 0:
        return 0.0
    return min(max(successful_handoffs, 0) / expected_handoffs, 1.0)


def score_multi_task(sample: dict, calls: list[dict], handoffs: list[dict], final_answer: str, steps: int, max_steps: int) -> dict:
    expected = sample.get("expected") or {"required_tools": sample.get("expected_tools", []), "final": sample.get("expected_answer", "")}
    expected_tools = expected.get("required_tools") or expected.get("sequence") or sample.get("expected_tools", [])
    successful_calls = [call for call in calls if call.get("execution", {}).get("error") is None]
    actual_tools = [call.get("name") for call in successful_calls]
    expected_roles = expected.get("roles", [])
    actual_roles = []
    for role in [role_for_tool(name) for name in actual_tools]:
        if not actual_roles or actual_roles[-1] != role: actual_roles.append(role)
    role_participation = all(role in actual_roles for role in expected_roles) if expected_roles else bool(actual_roles)
    role_order_correct = actual_roles == expected_roles if expected_roles else True
    tools_correct = actual_tools == expected_tools
    handoff_success = (not expected.get("handoff")) or (len(handoffs) >= 1 and role_participation)
    transfer_success = (not expected.get("dependency")) or all(handoff.get("transferred_context") is not None for handoff in handoffs)
    failed_calls = sum(1 for call in calls if call.get("execution", {}).get("error"))
    invalid_calls = sum(1 for call in calls if not call.get("name") or not isinstance(call.get("arguments"), dict))
    repeated_calls = sum(1 for left, right in zip(actual_tools, actual_tools[1:]) if left == right)
    if "final" in expected:
        final_success = str(expected["final"]).casefold() in final_answer.casefold()
    elif expected.get("final_type") == "numeric":
        final_success = bool(re.search(r"[-+]?\d+(?:\.\d+)?", final_answer))
    else:
        final_success = bool(final_answer.strip())
    passed = tools_correct and role_participation and role_order_correct and handoff_success and transfer_success and final_success
    if passed: failure_type = None
    elif failed_calls: failure_type = "tool_error"
    elif invalid_calls: failure_type = "wrong_arguments"
    elif not role_participation: failure_type = "missing_role"
    elif expected.get("handoff") and not handoff_success: failure_type = "handoff_failure"
    elif expected.get("dependency") and not transfer_success: failure_type = "context_transfer_failure"
    elif steps >= max_steps and not final_answer: failure_type = "max_steps_exceeded"
    elif repeated_calls and len(actual_tools) > len(expected_tools): failure_type = "repeated_loop"
    elif len(actual_tools) < len(expected_tools): failure_type = "missing_required_step"
    elif not tools_correct or not role_order_correct: failure_type = "wrong_tool"
    elif not final_success: failure_type = "final_answer_error"
    else: failure_type = "incomplete_task"
    return {"task_complete": passed, "tools_correct": tools_correct, "role_participation": role_participation, "role_order_correct": role_order_correct, "handoff_success": handoff_success, "context_transfer_success": transfer_success, "failed_tool_calls": failed_calls, "invalid_tool_calls": invalid_calls, "repeated_tool_calls": repeated_calls, "final_success": final_success, "failure_type": failure_type}


class AgentMultiRunner(BenchmarkRunner):
    name = "agent-multi"

    async def run(self, ctx: RunContext) -> dict:
        c = {**ctx.config, "thinking_mode": "no-think", "thinking_budget": 0}; ctx.config.update({"thinking_mode": "no-think", "thinking_budget": 0}); dataset_name = c.get("dataset", "data/agent/multi-v1.jsonl")
        ds_path = _resolve_dataset(dataset_name); dataset_hash = hashlib.sha256(ds_path.read_bytes()).hexdigest()
        snapshot = ctx.run_dir / "dataset-snapshot.jsonl"; snapshot.write_bytes(ds_path.read_bytes())
        max_steps_default = int(c.get("max_steps", 8)); url = c.get("server_url") or settings.llama_server_url
        thinking = normalize_thinking_config(c); max_tokens = int(c.get("max_tokens", 256))
        await ctx.emit("phase", {"name": "agent-multi-load", "dataset": str(ds_path), "url": url, **thinking_metadata(c)})
        samples = []
        with ds_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    try: samples.append(json.loads(line))
                    except json.JSONDecodeError as exc: raise ValueError(f"invalid dataset JSON at line {line_number}: {exc}") from exc
        if not samples: raise ValueError("no samples in dataset")
        await ctx.emit("phase", {"name": "agent-multi-start", "count": len(samples)})
        results, failure_types = [], {}; total_steps = total_calls = total_failed = total_invalid = total_handoffs = total_roles_ok = 0
        async with httpx.AsyncClient(base_url=url, timeout=thinking.request_timeout_s) as client:
            try:
                health = await client.get("/health", timeout=5); health.raise_for_status()
            except Exception as exc: raise RuntimeError(f"server health failed at {url}: {exc}") from exc
            for index, sample in enumerate(samples):
                if ctx.cancel_event and ctx.cancel_event.is_set(): raise asyncio.CancelledError("agent-multi cancelled")
                max_steps = int(sample.get("max_steps", max_steps_default)); messages = [{"role": "system", "content": SYSTEM_MULTI}, {"role": "user", "content": sample["prompt"]}]
                trace, raw_responses, calls, handoffs, final_text = [], [], [], [], ""; previous_role = None; steps = 0; started = time.perf_counter()
                for step in range(max_steps):
                    steps += 1
                    try:
                        response = await client.post("/v1/chat/completions", json=build_chat_payload(messages, c, max_tokens=max_tokens, temperature=0, tools=TOOLS_DEF, tool_choice="auto"))
                        response.raise_for_status(); body = response.json(); raw_responses.append(body)
                    except Exception as exc:
                        trace.append({"step": step, "role": "error", "content": str(exc)}); break
                    choices = body.get("choices") or []
                    if not choices: trace.append({"step": step, "role": "error", "content": "no choices"}); break
                    message = choices[0].get("message") or {}; content, reasoning, _ = extract_chat_message(body); tool_payloads = message.get("tool_calls") or []
                    trace.append({"step": step, "role": "assistant", "agent_role": previous_role, "content": content, "reasoning": reasoning[:1000], "tool_calls": tool_payloads})
                    if not tool_payloads and content:
                        parsed_name, parsed_args = parse_tool_call(content)
                        if parsed_name and parsed_args is not None: tool_payloads = [{"id": f"parsed-{step}", "function": {"name": parsed_name, "arguments": json.dumps(parsed_args)}}]
                    if tool_payloads:
                        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_payloads})
                        payload = tool_payloads[0]; function = payload.get("function", {}); name = function.get("name"); role = role_for_tool(name)
                        try: args = json.loads(function.get("arguments") or "{}")
                        except Exception: args = {}
                        execution = simulator(name, args); call = {"name": name, "role": role, "arguments": args, "execution": execution, "call_id": payload.get("id")}; calls.append(call)
                        if previous_role and previous_role != role:
                            handoff = {"from_role": previous_role, "to_role": role, "step": step, "transferred_context": calls[-2].get("execution") if len(calls) >= 2 else None, "source_call": calls[-2].get("name") if len(calls) >= 2 else None, "target_call": name}; handoffs.append(handoff); trace.append({"step": step, "role": "handoff", **handoff})
                        previous_role = role; trace.append({"step": step, "role": "tool", "agent_role": role, "tool": name, "arguments": args, "result": execution})
                        messages.append({"role": "tool", "tool_call_id": payload.get("id", f"call-{step}"), "name": name, "content": json.dumps(execution, ensure_ascii=False)})
                        continue
                    final_text = content; break
                final_answer = extract_final(final_text) if final_text else ""
                scoring = score_multi_task(sample, calls, handoffs, final_answer, steps, max_steps)
                total_steps += steps; total_calls += len(calls); total_failed += scoring["failed_tool_calls"]; total_invalid += scoring["invalid_tool_calls"]; total_handoffs += len(handoffs); total_roles_ok += int(scoring["role_participation"])
                if scoring["task_complete"]: pass
                if scoring["failure_type"]: failure_types[scoring["failure_type"]] = failure_types.get(scoring["failure_type"], 0) + 1
                artifact = ctx.run_dir / "artifacts" / "agent-multi" / sample["id"]; artifact.mkdir(parents=True, exist_ok=True)
                (artifact / "task.json").write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")
                (artifact / "raw_responses.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in raw_responses) + "\n", encoding="utf-8")
                (artifact / "agent_trace.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in trace) + "\n", encoding="utf-8")
                (artifact / "handoffs.json").write_text(json.dumps(handoffs, indent=2, ensure_ascii=False), encoding="utf-8")
                (artifact / "tool_calls.json").write_text(json.dumps(calls, indent=2, ensure_ascii=False), encoding="utf-8")
                (artifact / "final_answer.txt").write_text(final_answer, encoding="utf-8")
                (artifact / "scoring.json").write_text(json.dumps(scoring, indent=2, ensure_ascii=False), encoding="utf-8")
                expected_handoff = bool((sample.get("expected") or {}).get("handoff"))
                result = {"id": sample["id"], "category": sample.get("category", "unknown"), "prompt": sample["prompt"], "participating_roles": sorted({call["role"] for call in calls}), "expected_handoff": expected_handoff, "handoff_success": scoring["handoff_success"], "handoffs": handoffs, "transferred_context": [item.get("transferred_context") for item in handoffs], "tool_calls": calls, "tool_results": [call["execution"] for call in calls], "raw_model_responses": raw_responses, "trace": trace, "final_answer": final_answer, "steps": steps, "tool_call_count": len(calls), "pass": scoring["task_complete"], "correct": scoring["task_complete"], "failure_type": scoring["failure_type"], "failed_tool_calls": scoring["failed_tool_calls"], "invalid_tool_calls": scoring["invalid_tool_calls"], "repeated_tool_calls": scoring["repeated_tool_calls"], "elapsed_s": time.perf_counter() - started, "artifact_path": str(artifact)}
                results.append(result); await ctx.emit("progress", {"completed": index + 1, "total": len(samples), "passed": sum(int(item["pass"]) for item in results), "sample": result})
        categories = {}
        for result in results:
            summary = categories.setdefault(result["category"], {"total": 0, "passed": 0}); summary["total"] += 1; summary["passed"] += int(result["pass"])
        for summary in categories.values(): summary["pass_rate"] = summary["passed"] / summary["total"]
        passed = sum(int(item["pass"]) for item in results)
        (ctx.run_dir / "samples.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in results) + "\n", encoding="utf-8")
        expected_handoffs = sum(int(item["expected_handoff"]) for item in results)
        successful_handoffs = sum(int(item["handoff_success"]) for item in results if item["expected_handoff"])
        return {"kind": "agent-multi", "version": 1.1, **thinking_metadata(c), "dataset_provenance": {"path": str(ds_path), "version": str(c.get("dataset_version", "1")), "sha256": dataset_hash, "snapshot": str(snapshot)}, "dataset": str(ds_path), "total": len(samples), "passed": passed, "correct": passed, "pass_rate": passed / len(samples), "categories": categories, "handoff_success_rate": calculate_handoff_success_rate(successful_handoffs, expected_handoffs), "handoff_successful_tasks": successful_handoffs, "handoff_expected_tasks": expected_handoffs, "role_participation_success_rate": total_roles_ok / len(samples), "avg_steps": total_steps / len(samples), "avg_tool_calls": total_calls / len(samples), "tool_calls_total": total_calls, "failed_tool_calls": total_failed, "invalid_tool_calls": total_invalid, "handoffs": total_handoffs, "failure_types": failure_types, "samples": results}
