from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
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

ALLOWED_SCORING_TYPES = {"multiple_choice", "numeric", "exact_match"}


def resolve_dataset(dataset: str) -> Path:
    path = Path(dataset)
    if path.is_absolute() and path.exists():
        return path.resolve()
    for candidate in (settings.run_root.parent / path, settings.recipe_root.parent / path, path):
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"dataset not found: {dataset} (resolved {path})")


def _normalize_text(value: object) -> str:
    return " ".join(str(value).strip().casefold().split())


def _normalize_numeric(value: object) -> str:
    matches = re.findall(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", str(value).strip().replace(",", ""))
    if not matches:
        return ""
    number = float(matches[-1])
    return str(int(number)) if number.is_integer() else format(number, "g")


def score_answer(sample: dict, raw_response: str) -> tuple[bool, str, dict]:
    answer = next((line.strip() for line in reversed(raw_response.strip().splitlines()) if line.strip()), "")
    answer = re.sub(r"^(?:final answer|answer)\s*[:：]\s*", "", answer, flags=re.I).strip()
    scoring_type = sample["scoring_type"]
    expected = sample["expected"]
    if scoring_type == "multiple_choice":
        choice_ids = [str(choice["id"]).strip() for choice in sample["choices"]]
        by_folded = {choice.casefold(): choice for choice in choice_ids}
        selected = next((by_folded.get(token.casefold(), "") for token in re.findall(r"\b[A-Za-z0-9]+\b", answer) if token.casefold() in by_folded), "")
        if not selected:
            answer_text = _normalize_text(answer)
            text_matches = []
            for choice in sample["choices"]:
                variants = [part.strip() for part in re.split(r"\s*/\s*", choice.get("text", "") or "")]
                if any(_normalize_text(variant) and _normalize_text(variant) in answer_text for variant in variants):
                    text_matches.append(choice)
            if len(text_matches) == 1:
                selected = str(text_matches[0]["id"]).strip()
        normalized = selected.casefold()
        evidence = {"method": "choice_id_or_text", "choice_ids": choice_ids}
    elif scoring_type == "numeric":
        normalized = _normalize_numeric(answer)
        evidence = {"method": "numeric_normalization"}
    else:
        normalized = _normalize_text(answer)
        evidence = {"method": "trim_casefold_whitespace"}
    expected_normalized = _normalize_numeric(expected) if scoring_type == "numeric" else _normalize_text(expected)
    if scoring_type == "numeric" and sample.get("tolerance") is not None:
        try:
            passed = abs(float(normalized) - float(expected)) <= float(sample["tolerance"])
        except (TypeError, ValueError):
            passed = False
    else:
        passed = normalized == expected_normalized
    evidence.update({"expected_normalized": expected_normalized, "normalized_answer": normalized})
    return passed, normalized, evidence


class KnowledgeRunner(BenchmarkRunner):
    name = "knowledge"

    async def run(self, ctx: RunContext) -> dict:
        c = {**ctx.config, "thinking_mode": "no-think", "thinking_budget": 0}
        ctx.config.update({"thinking_mode": "no-think", "thinking_budget": 0})
        dataset_name = c.get("dataset", "data/knowledge/sample-v1.jsonl")
        ds_path = resolve_dataset(dataset_name)
        dataset_hash = hashlib.sha256(ds_path.read_bytes()).hexdigest()
        dataset_version = str(c.get("dataset_version", "1"))
        snapshot_path = ctx.run_dir / "dataset-snapshot.jsonl"
        shutil.copyfile(ds_path, snapshot_path)
        url = c.get("server_url") or settings.llama_server_url
        thinking = normalize_thinking_config(c)
        default_max_tokens = {"think": 512, "no-think": 128, "auto": 32}[thinking.mode]
        max_tokens = int(c.get("max_tokens", c.get("gen_tokens", 128 if dataset_version == "1.2" else default_max_tokens)))
        await ctx.emit("phase", {"name": "knowledge-load", "dataset": str(ds_path), "url": url, **thinking_metadata(c)})

        samples = []
        with ds_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    sample = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid dataset JSON at line {line_number}: {exc}") from exc
                if "scoring_type" not in sample:
                    sample["scoring_type"] = sample.get("type", "exact_match")
                sample.setdefault("category", sample.get("domain", "unknown"))
                if sample.get("scoring_type") not in ALLOWED_SCORING_TYPES:
                    sample["scoring_type"] = sample.get("type", sample.get("scoring_type"))
                if "expected" not in sample:
                    sample["expected"] = sample.get("answer")
                if isinstance(sample.get("choices"), list) and sample["choices"] and isinstance(sample["choices"][0], str):
                    sample["choices"] = [{"id": item.split(".", 1)[0].strip(), "text": item.split(".", 1)[1].strip()} for item in sample["choices"] if "." in item]
                if sample.get("scoring_type") not in ALLOWED_SCORING_TYPES:
                    raise ValueError(f"unsupported scoring_type for {sample.get('id')}")
                samples.append(sample)
        if not samples:
            raise ValueError("no samples in dataset")
        await ctx.emit("phase", {"name": "knowledge-start", "count": len(samples)})

        results = []
        correct = 0
        timeout = thinking.request_timeout_s
        reasoning_tokens_total = 0
        reasoning_token_samples = 0
        async with httpx.AsyncClient(base_url=url, timeout=timeout) as client:
            try:
                health = await client.get("/health", timeout=5)
                health.raise_for_status()
            except Exception as exc:
                raise RuntimeError(f"server health failed at {url}: {exc}") from exc
            for idx, sample in enumerate(samples):
                if ctx.cancel_event and ctx.cancel_event.is_set():
                    raise asyncio.CancelledError("knowledge cancelled")
                prompt = sample.get("prompt") or sample.get("question") or ""
                if sample["scoring_type"] == "multiple_choice" and sample.get("choices"):
                    options = "\n".join(f"{choice['id']}. {choice.get('text', '')}" for choice in sample["choices"])
                    prompt = f"{prompt}\n{options}"
                if sample["scoring_type"] == "multiple_choice":
                    prompt += "\n\nRespond with only the final choice letter (A, B, C, or D)."
                elif sample["scoring_type"] == "numeric":
                    prompt += "\n\nRespond with only the final numeric answer."
                else:
                    prompt += "\n\nRespond with only the exact final answer."
                started = time.perf_counter()
                raw_response = ""
                reasoning = ""
                reasoning_tokens = None
                try:
                    if thinking.mode != "auto":
                        payload = build_chat_payload([{"role": "user", "content": prompt}], c, max_tokens=max_tokens, temperature=0)
                        response = await client.post("/v1/chat/completions", json=payload)
                        response.raise_for_status()
                        body = response.json()
                        raw_response, reasoning, _ = extract_chat_message(body)
                        reasoning_tokens = extract_reasoning_tokens(body)
                    else:
                        response = await client.post("/completion", json={"prompt": prompt, "n_predict": max_tokens, "temperature": 0, "stream": False})
                        response.raise_for_status()
                        body = response.json()
                        raw_output = body.get("content", "") or body.get("completion", "") or ""
                        raw_response, reasoning, _ = extract_chat_message({"choices": [{"message": {"content": raw_output}}]})
                        reasoning_tokens = extract_reasoning_tokens(body)
                except Exception as exc:
                    if thinking.mode == "auto":
                        try:
                            payload = build_chat_payload([{"role": "user", "content": prompt}], c, max_tokens=max_tokens, temperature=0)
                            response = await client.post("/v1/chat/completions", json=payload)
                            response.raise_for_status()
                            body = response.json()
                            raw_response, reasoning, _ = extract_chat_message(body)
                            reasoning_tokens = extract_reasoning_tokens(body)
                        except Exception as fallback_exc:
                            raw_response = f"ERROR: {fallback_exc} / {exc}"
                    else:
                        raw_response = f"ERROR: {exc}"
                if reasoning_tokens is not None:
                    reasoning_tokens_total += reasoning_tokens
                    reasoning_token_samples += 1
                try:
                    passed, normalized, scoring_evidence = score_answer(sample, raw_response)
                except Exception as exc:
                    # A malformed model response must remain auditable and must not abort the batch.
                    passed, normalized = False, ""
                    scoring_evidence = {"method": "scoring_error", "error": str(exc)}
                correct += int(passed)
                category = sample.get("category", "unknown")
                result = {
                    "id": sample.get("id"), "category": category, "domain": category,
                    "scoring_type": sample["scoring_type"], "prompt": prompt,
                    "expected_answer": sample["expected"], "expected": sample["expected"],
                    "raw_response": raw_response, "output": raw_response,
                    "normalized_answer": normalized, "pass": passed, "correct": passed,
                    "scoring_evidence": scoring_evidence, "reasoning_preview": reasoning[:1000],
                    "reasoning_tokens": reasoning_tokens, "reasoning_chars": len(reasoning),
                    "output_chars": len(raw_response), "elapsed_s": time.perf_counter() - started,
                }
                results.append(result)
                await ctx.emit("progress", {"completed": idx + 1, "total": len(samples), "correct": correct, "sample": result})

        categories = {}
        difficulties = {}
        for result in results:
            summary = categories.setdefault(result["category"], {"total": 0, "correct": 0})
            summary["total"] += 1
            summary["correct"] += int(result["pass"])
            difficulty = next((item.get("difficulty") for item in samples if item.get("id") == result["id"]), "unknown")
            dsummary = difficulties.setdefault(difficulty, {"total": 0, "correct": 0})
            dsummary["total"] += 1; dsummary["correct"] += int(result["pass"])
        for summary in categories.values():
            summary["accuracy"] = summary["correct"] / summary["total"] if summary["total"] else 0
            summary["pass_rate"] = summary["accuracy"]
        for summary in difficulties.values():
            summary["accuracy"] = summary["correct"] / summary["total"] if summary["total"] else 0
            summary["pass_rate"] = summary["accuracy"]
        (ctx.run_dir / "samples.jsonl").write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in results) + "\n", encoding="utf-8")
        return {
            "kind": "knowledge", "version": 1.2 if dataset_version == "1.2" else 1.1, **thinking_metadata(c),
            "reasoning_tokens_total": reasoning_tokens_total if reasoning_token_samples else None,
            "reasoning_token_samples": reasoning_token_samples,
            "dataset_provenance": {"path": str(ds_path), "version": dataset_version, "sha256": dataset_hash, "snapshot": str(snapshot_path)},
            "total": len(samples), "correct": correct, "accuracy": correct / len(samples),
            "pass_rate": correct / len(samples), "categories": categories, "domains": categories, "difficulties": difficulties,
            "samples": results,
        }
