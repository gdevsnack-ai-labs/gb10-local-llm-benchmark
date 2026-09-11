from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import operator
import re
import time
from pathlib import Path

import httpx

from app.core.config import settings
from app.runners.base import BenchmarkRunner, RunContext
from app.runners.reasoning import build_chat_payload, extract_chat_message, extract_reasoning_tokens, normalize_thinking_config, thinking_metadata


def _eval_expression(expression: str):
    tree = ast.parse(expression, mode="eval").body
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in ops:
            return ops[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op) in (ast.UAdd, ast.USub):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        raise ValueError("unsupported calculator expression")

    value = evaluate(tree)
    return int(value) if isinstance(value, float) and value.is_integer() else value


def simulator(tool: str, args: dict) -> dict:
    try:
        if tool == "calculator":
            if "expression" in args:
                return {"result": _eval_expression(str(args["expression"]))}
            a, b, op = int(args.get("a", 0)), int(args.get("b", 0)), args.get("op", "+")
            op_aliases = {
                "add": "+", "plus": "+", "subtract": "-", "minus": "-",
                "multiply": "*", "mul": "*", "times": "*", "divide": "/",
            }
            op = op_aliases.get(str(op).lower(), op)
            if op == "+": return {"result": a + b}
            if op == "-": return {"result": a - b}
            if op == "*": return {"result": a * b}
            if op == "/": return {"result": a // b if b else None}
            return {"error": "unknown op"}
        if tool in {"kv_get", "kv_lookup"}:
            values = {"capital:japan": "Tokyo", "capital:france": "Paris", "capital:korea": "Seoul", "japan_capital": "Tokyo", "france_capital": "Paris"}
            key = args.get("key", "")
            return {"result": values.get(key)} if key in values else {"error": "key not found"}
        if tool == "read_file":
            return {"result": "hello world"} if args.get("path") == "/tmp/data.txt" else {"error": "file not found"}
    except Exception as exc:
        return {"error": str(exc)}
    return {"error": "unknown tool"}


TOOLS_DEF = [
    {"type": "function", "function": {"name": "calculator", "description": "Calculate an expression or two integers; op accepts +, -, *, / or add, subtract, multiply, divide.", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}, "a": {"type": "integer"}, "b": {"type": "integer"}, "op": {"type": "string", "enum": ["+", "-", "*", "/", "add", "subtract", "multiply", "divide"]}}}}},
    {"type": "function", "function": {"name": "kv_get", "description": "Get a value from the key-value store", "parameters": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read an allowed file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
]


def parse_tool_call(text: str) -> tuple[str | None, dict | None]:
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            if "name" in obj: return obj.get("name"), obj.get("arguments") or obj.get("args") or {}
            if "tool" in obj: return obj.get("tool"), obj.get("args") or obj.get("arguments") or {}
            if "a" in obj and "b" in obj: return "calculator", obj
        except Exception:
            pass
    for tool in ("calculator", "kv_get", "kv_lookup", "read_file"):
        if tool in text:
            return tool, {}
    return None, None


def _resolve_dataset(dataset: str) -> Path:
    path = Path(dataset)
    if path.is_absolute() and path.exists(): return path.resolve()
    for candidate in (settings.run_root.parent / path, settings.recipe_root.parent / path, path):
        if candidate.exists(): return candidate.resolve()
    raise FileNotFoundError(f"dataset not found: {dataset} (resolved {path})")


def _norm(value) -> str:
    return " ".join(str(value).strip().casefold().split())


def score_task(sample: dict, calls: list[dict], final_answer: str) -> dict:
    expected = sample["expected"]
    expected_tools = expected.get("tools", [])
    expected_sequence = expected.get("sequence", [item.get("name") for item in expected_tools])
    actual_names = [call.get("name") for call in calls]
    selection_correct = (actual_names == expected_sequence) if expected_sequence else len(calls) == expected.get("tool_calls", 0)
    argument_checks = []
    for index, expected_call in enumerate(expected_tools):
        if index < len(calls) and expected_call.get("arguments") is not None:
            argument_checks.append(calls[index].get("arguments") == expected_call["arguments"])
    arguments_correct = all(argument_checks) if argument_checks else selection_correct and bool(calls) == bool(expected_sequence)
    execution_success = bool(calls) and all(call.get("execution", {}).get("error") is None for call in calls)
    if expected.get("first_may_fail") and len(calls) >= 2:
        execution_success = all(call.get("execution", {}).get("error") is None for call in calls[1:])
    if not calls and expected.get("tool_calls") == 0:
        execution_success = True
    final_norm = _norm(final_answer)
    if "final" in expected:
        expected_final = _norm(expected["final"])
        final_success = final_norm == expected_final or expected_final in final_norm
    elif expected.get("final_from_tool"):
        expected_final = _norm(calls[-1].get("execution", {}).get("result", "")) if calls else ""
        final_success = bool(expected_final) and (final_norm == expected_final or expected_final in final_norm)
    elif expected.get("final_type") == "numeric":
        final_success = bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?", final_norm))
    else:
        final_success = True
    if selection_correct and arguments_correct and not execution_success:
        failure_type = "execution_error"
    elif not selection_correct:
        if expected_sequence and any(name not in expected_sequence for name in actual_names): failure_type = "unnecessary_tool_call" if not expected_sequence else "wrong_tool"
        elif expected_sequence and len(actual_names) < len(expected_sequence): failure_type = "missing_tool_call" if len(actual_names) == 0 else "incomplete_sequence"
        else: failure_type = "wrong_tool"
    elif not arguments_correct:
        failure_type = "wrong_arguments"
    elif not final_success:
        failure_type = "final_answer_error"
    else:
        failure_type = None
    passed = selection_correct and arguments_correct and execution_success and final_success
    return {"selection_correct": selection_correct, "arguments_correct": arguments_correct, "execution_success": execution_success, "final_success": final_success, "passed": passed, "failure_type": failure_type}


class ToolCallRunner(BenchmarkRunner):
    name = "tool-call"

    async def run(self, ctx: RunContext) -> dict:
        c = {**ctx.config, "thinking_mode": "no-think", "thinking_budget": 0}
        ctx.config.update({"thinking_mode": "no-think", "thinking_budget": 0})
        dataset_name = c.get("dataset", "data/tool/sample-v1.jsonl")
        ds_path = _resolve_dataset(dataset_name)
        dataset_hash = hashlib.sha256(ds_path.read_bytes()).hexdigest()
        snapshot = ctx.run_dir / "dataset-snapshot.jsonl"
        snapshot.write_bytes(ds_path.read_bytes())
        url = c.get("server_url") or settings.llama_server_url
        thinking = normalize_thinking_config(c)
        max_tokens = int(c.get("max_tokens", 256))
        max_steps = int(c.get("max_steps", 6))
        await ctx.emit("phase", {"name": "tool-load", "dataset": str(ds_path), "url": url, **thinking_metadata(c)})
        samples = []
        with ds_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    try: samples.append(json.loads(line))
                    except json.JSONDecodeError as exc: raise ValueError(f"invalid dataset JSON at line {line_number}: {exc}") from exc
        for sample in samples:
            if "expected" not in sample and "expected_tool" in sample:
                sample["expected"] = {"tools": [{"name": sample["expected_tool"], "arguments": sample["expected_args"]}], "final": str(sample["expected_result"])}
        if not samples: raise ValueError("no samples in dataset")
        await ctx.emit("phase", {"name": "tool-start", "count": len(samples)})
        results, failure_types = [], {}
        selection_correct = arguments_correct = execution_success = 0
        async with httpx.AsyncClient(base_url=url, timeout=thinking.request_timeout_s) as client:
            try:
                health = await client.get("/health", timeout=5); health.raise_for_status()
            except Exception as exc: raise RuntimeError(f"server health failed at {url}: {exc}") from exc
            for index, sample in enumerate(samples):
                started = time.perf_counter(); messages = [{"role": "user", "content": sample["prompt"]}]
                calls, raw_responses, final_answer = [], [], ""
                step_limit = 1 if "expected_tool" in sample else max_steps
                for _ in range(step_limit):
                    try:
                        response = await client.post("/v1/chat/completions", json=build_chat_payload(messages, c, max_tokens=max_tokens, temperature=0, tools=TOOLS_DEF, tool_choice="auto"))
                        response.raise_for_status(); body = response.json(); raw_responses.append(body)
                        choices = body.get("choices") or []
                        if not choices: break
                        message = choices[0].get("message") or {}
                        tool_calls = message.get("tool_calls") or []
                        if not tool_calls:
                            final_answer, _, _ = extract_chat_message(body)
                            parsed_tool, parsed_args = parse_tool_call(final_answer)
                            if parsed_tool:
                                tool_calls = [{"function": {"name": parsed_tool, "arguments": json.dumps(parsed_args or {})}}]
                            else:
                                break
                        messages.append({"role": "assistant", "content": message.get("content") or "", "tool_calls": tool_calls})
                        for tool_call in tool_calls:
                            function = tool_call.get("function", {}); name = function.get("name")
                            arguments_raw = function.get("arguments", {})
                            try: arguments = json.loads(arguments_raw) if isinstance(arguments_raw, str) else (arguments_raw or {})
                            except Exception: arguments = {}
                            execution = simulator(name, arguments)
                            call = {"name": name, "arguments": arguments, "execution": execution, "call_id": tool_call.get("id")}
                            calls.append(call)
                            messages.append({"role": "tool", "tool_call_id": tool_call.get("id", f"call-{len(calls)}"), "name": name, "content": json.dumps(execution, ensure_ascii=False)})
                    except Exception as exc:
                        raw_responses.append({"error": str(exc)}); break
                if not final_answer and calls:
                    final_answer = str(calls[-1]["execution"].get("result", ""))
                scoring = score_task(sample, calls, final_answer)
                selection_correct += int(scoring["selection_correct"]); arguments_correct += int(scoring["arguments_correct"]); execution_success += int(scoring["execution_success"])
                if scoring["failure_type"]: failure_types[scoring["failure_type"]] = failure_types.get(scoring["failure_type"], 0) + 1
                artifact = ctx.run_dir / "artifacts" / "tool-call" / sample["id"]; artifact.mkdir(parents=True, exist_ok=True)
                (artifact / "task.json").write_text(json.dumps(sample, indent=2, ensure_ascii=False), encoding="utf-8")
                (artifact / "raw_responses.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in raw_responses) + "\n", encoding="utf-8")
                (artifact / "tool_calls.json").write_text(json.dumps(calls, indent=2, ensure_ascii=False), encoding="utf-8")
                (artifact / "tool_results.json").write_text(json.dumps([call["execution"] for call in calls], indent=2, ensure_ascii=False), encoding="utf-8")
                (artifact / "final_answer.txt").write_text(final_answer, encoding="utf-8")
                (artifact / "scoring.json").write_text(json.dumps(scoring, indent=2, ensure_ascii=False), encoding="utf-8")
                result = {"id": sample["id"], "category": sample.get("category", "unknown"), "prompt": sample["prompt"], "expected": sample["expected"], "expected_sequence": sample["expected"].get("sequence", [x.get("name") for x in sample["expected"].get("tools", [])]), "actual_tool_calls": calls, "raw_model_responses": raw_responses, "final_answer": final_answer, **scoring, "elapsed_s": time.perf_counter() - started, "artifact_path": str(artifact)}
                results.append(result)
                await ctx.emit("progress", {"completed": index + 1, "total": len(samples), "passed": sum(int(item["passed"]) for item in results), "sample": result})
        categories = {}
        for result in results:
            summary = categories.setdefault(result["category"], {"total": 0, "passed": 0}); summary["total"] += 1; summary["passed"] += int(result["passed"])
        for summary in categories.values(): summary["pass_rate"] = summary["passed"] / summary["total"]
        (ctx.run_dir / "samples.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in results) + "\n", encoding="utf-8")
        passed = sum(int(item["passed"]) for item in results)
        return {"kind": "tool-call", "version": 1.1, **thinking_metadata(c), "dataset_provenance": {"path": str(ds_path), "version": str(c.get("dataset_version", "1")), "sha256": dataset_hash, "snapshot": str(snapshot)}, "total": len(samples), "passed": passed, "pass_rate": passed / len(samples), "categories": categories, "tool_selection_accuracy": selection_correct / len(samples), "argument_accuracy": arguments_correct / len(samples), "execution_success_rate": execution_success / len(samples), "tool_correct": selection_correct, "tool_rate": selection_correct / len(samples), "args_correct": arguments_correct, "args_rate": arguments_correct / len(samples), "exec_correct": execution_success, "exec_rate": execution_success / len(samples), "failure_types": failure_types, "samples": results}
