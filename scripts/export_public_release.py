#!/usr/bin/env python3
"""Build the sanitized public GB10 benchmark release snapshot.

The exporter reads canonical public evaluator summaries plus historical full-cycle
run artifacts, reconciles the 18 x 7 matrix, and writes an immutable JSON release.
It never publishes to Supabase, Blogger, or Vercel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASE_ID = "gb10-llm-benchmark-v1-20260906"
RELEASE_DATE = "2026-09-06"
SUMMARY_PATH = ROOT / "results-public/models/summary-20260906.json"
METHODOLOGY_PATH = ROOT / "results-public/methodology.json"
RUN_ROOT = ROOT / "runs"

SUITES = (
    "performance",
    "server_performance",
    "knowledge",
    "coding",
    "tool_call",
    "agent_single",
    "agent_multi",
)

EVALUATOR_SUITES = {
    "knowledge": "knowledge",
    "tool_call": "tool-call",
    "agent_single": "agent-single",
    "agent_multi": "agent-multi",
}

# Historical source runs are declared explicitly so a changed local directory
# cannot silently change the release's provenance.
HISTORICAL_RUNS: dict[str, dict[str, str]] = {
    "Ornith 1.5|Q5_K_M": {
        "performance": "20260905-131958-3cfdfd",
        "server_performance": "20260905-132350-d86bcf",
        "coding": "20260905-133625-26bbb8",
    },
    "Ornith 1.5|Q6_K": {
        "performance": "20260905-134111-76e244",
        "server_performance": "20260905-134533-c5b64a",
        "coding": "20260905-135918-37492a",
    },
    "Ornith 1.5|Q8_0": {
        "performance": "20260905-140444-106393",
        "server_performance": "20260905-140846-2c88a0",
        "coding": "20260905-142222-7d90b3",
    },
    "North Mini|MXFP4": {
        "performance": "20260905-183924-10553d",
        "server_performance": "20260905-184209-003ab1",
        "coding": "20260905-185126-78fe5a",
    },
    "North Mini|UD-Q4": {
        "performance": "20260905-185701-b2d23b",
        "server_performance": "20260905-185954-c24ba2",
        "coding": "20260905-190857-ccec3d",
    },
    "North Mini|UD-Q5": {
        "performance": "20260905-191515-5b2b06",
        "server_performance": "20260905-191832-4bd7c6",
        "coding": "20260905-192841-b07e97",
    },
    "North Mini|UD-Q6": {
        "performance": "20260905-193540-0c3ce7",
        "server_performance": "20260905-193918-79dcd0",
        "coding": "20260905-195043-f17e76",
    },
    "N2 Mini|UD-Q4": {
        "performance": "20260905-153010-ec5db8",
        "server_performance": "20260905-161120-b37a54",
        "coding": "20260905-153414-41f495",
    },
    "N2 Mini|UD-Q5XL": {
        "performance": "20260905-153800-d9d315",
        "server_performance": "20260905-162247-e466ce",
        "coding": "20260905-154314-4cdc32",
    },
    "N2 Mini|Q5_K_M": {
        "performance": "20260905-154830-2ed4f8",
        "server_performance": "20260905-163531-7e5f86",
        "coding": "20260905-155244-eaa71f",
    },
    "N2 Mini|Q6_K": {
        "performance": "20260905-155619-88ff7e",
        "server_performance": "20260905-164726-020f2f",
        "coding": "20260905-160053-23c1f9",
    },
    "Gemma4|NVFP4": {
        "performance": "20260905-201154-565aad",
        "server_performance": "20260905-201504-70bab9",
        "coding": "20260905-203019-49bf2b",
    },
    "Gemma4|Q4_0": {
        "performance": "20260905-204203-52bb92",
        "server_performance": "20260905-204454-8fee22",
        "coding": "20260905-205718-854c2d",
    },
    "Qwen3.6 35B-A3B|HQ": {
        "performance": "20260905-115655-385b40",
        "server_performance": "20260905-115943-c5d61a",
        "coding": "20260905-120944-4cc44e",
    },
    "Qwen3.6 35B-A3B|TURBO": {
        "performance": "20260905-172506-7319bf",
        "server_performance": "20260905-172758-ece708",
        "coding": "20260905-173719-61c62e",
    },
    "Qwen3.6 35B-A3B|Q8": {
        "performance": "20260905-174127-3d55c5",
        "server_performance": "20260905-174519-9fe463",
        "coding": "20260905-175911-e3d9fa",
    },
    "Qwen3.6 35B-A3B|APEX": {
        "performance": "20260905-180921-b11e6a",
        "server_performance": "20260905-181248-c9a2b9",
        "coding": "20260905-182343-4283d9",
    },
    "Qwen3.8 Flash Next|UD-IQ4_XS": {
        "performance": "20260905-223427-189e4d",
        "server_performance": "20260905-225405-d84cc2",
        "coding": "20260905-232058-c7aa39",
    },
}

SERVER_ALTERNATES: dict[str, list[str]] = {
    "Gemma4|NVFP4": ["20260905-212404-c6e555"],
    "Gemma4|Q4_0": ["20260905-213513-340ca6"],
}

MODEL_MATCHERS: dict[str, tuple[str, ...]] = {
    "Ornith 1.5|Q5_K_M": ("Ornith-1.5-35B-A3B-MTP.Q5_K_M",),
    "Ornith 1.5|Q6_K": ("Ornith-1.5-35B-A3B-MTP.Q6_K",),
    "Ornith 1.5|Q8_0": ("Ornith-1.5-35B-A3B-MTP.Q8_0",),
    "North Mini|MXFP4": ("North-Mini-Code-1.0-MXFP4_MOE",),
    "North Mini|UD-Q4": ("North-Mini-Code-1.0-UD-Q4_K_M",),
    "North Mini|UD-Q5": ("North-Mini-Code-1.0-UD-Q5_K_M",),
    "North Mini|UD-Q6": ("North-Mini-Code-1.0-UD-Q6_K_XL",),
    "N2 Mini|UD-Q4": ("Nex-N2-mini-UD-Q4_K_M",),
    "N2 Mini|UD-Q5XL": ("Nex-N2-mini-UD-Q5_K_XL",),
    "N2 Mini|Q5_K_M": ("nex-agi_Nex-N2-mini-Q5_K_M",),
    "N2 Mini|Q6_K": ("nex-agi_Nex-N2-mini-Q6_K",),
    "Gemma4|NVFP4": ("gemma-4-26B-A4B-it-qat-q4_0-uncensored-heretic-NVFP4",),
    "Gemma4|Q4_0": ("gemma-4-26B-A4B-it-qat-q4_0-uncensored-heretic-Q4_0",),
    "Qwen3.6 35B-A3B|HQ": ("Qwen3.6-35B-A3B-NVFP4-MTP-HQ",),
    "Qwen3.6 35B-A3B|TURBO": ("Qwen3.6-35B-A3B-NVFP4-MTP-TURBO",),
    "Qwen3.6 35B-A3B|Q8": ("Qwen3.6-35B-A3B-Q8_0",),
    "Qwen3.6 35B-A3B|APEX": ("Qwen3.6-35B-A3B-uncensored-heretic-APEX-I-Balanced",),
    "Qwen3.8 Flash Next|UD-IQ4_XS": ("Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003",),
}

SAFE_CONFIG_KEYS = {
    "thinking_mode", "thinking_budget", "request_timeout_s", "spec_type", "spec",
    "spec_draft_n_max", "spec_draft_p_min", "concurrencies", "requests_per_concurrency",
    "repetitions", "gen_tokens", "prompt_tokens", "cache_prompt", "parallel", "ctx_size",
    "n_gpu_layers", "flash_attn", "batch_size", "ubatch_size", "threads", "cache_type_k",
    "cache_type_v", "dataset_version", "max_tokens", "max_steps",
}

PRIVATE_MARKERS = (
    "/home/", "/media/", "~/", "/tmp/", "127.0.0.1", "localhost", "SUPABASE_SERVICE",
    "BEGIN PRIVATE KEY", "ghp_", "AIza", "Bearer ", "raw_response", "raw_model_responses",
    "generated_code", "llama-server.log", "environment.json", "dataset-snapshot.jsonl",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_dir(run_id: str) -> Path:
    path = RUN_ROOT / run_id
    if not path.is_dir():
        raise ValueError(f"source run directory missing: {run_id}")
    return path


def load_run(run_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    directory = run_dir(run_id)
    manifest_path = directory / "manifest.json"
    result_path = directory / "result.json"
    if not manifest_path.exists() or not result_path.exists():
        raise ValueError(f"source run evidence incomplete: {run_id}")
    return load_json(manifest_path), load_json(result_path)


def source_model_name(manifest: dict[str, Any]) -> str:
    config = manifest.get("resolved_config") or manifest.get("config") or {}
    return Path(str(config.get("model_path") or "")).name


def safe_condition(manifest: dict[str, Any]) -> dict[str, Any]:
    config = manifest.get("resolved_config") or manifest.get("config") or {}
    return {key: config[key] for key in sorted(SAFE_CONFIG_KEYS) if key in config}


def validate_run(run_id: str, expected_suite: str, model_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest, result = load_run(run_id)
    actual_suite = str(manifest.get("suite") or "")
    allowed_suites = {expected_suite.replace("_", "-")}
    if expected_suite == "server_performance":
        allowed_suites.add("server-performance-no-mtp")
    if actual_suite not in allowed_suites:
        raise ValueError(f"{run_id}: expected {expected_suite}, got {actual_suite}")
    model_name = source_model_name(manifest)
    if not any(matcher in model_name for matcher in MODEL_MATCHERS[model_key]):
        raise ValueError(f"{run_id}: model mismatch for {model_key}: {model_name}")
    return manifest, result


def compact_performance(result: dict[str, Any]) -> dict[str, Any]:
    representative = result.get("formal_summary", {}).get("representative", {})
    metrics: dict[str, Any] = {}
    for key, value in representative.items():
        if not isinstance(value, dict):
            continue
        label = "pp" if key.startswith("pp_") else "tg" if key.startswith("tg_") else key
        metrics[label] = {
            "token_count": value.get("n_prompt") or value.get("n_gen"),
            "mean_tps": value.get("mean"),
            "stddev_tps": value.get("stddev"),
            "repetitions": value.get("repetitions") and len(value["repetitions"]),
            "unit": value.get("unit", "tokens/s"),
        }
    return {"metrics": metrics, "repetitions": result.get("formal_summary", {}).get("repetitions", 0)}


def compact_server(result: dict[str, Any]) -> dict[str, Any]:
    conditions = []
    for condition in result.get("conditions", []):
        conditions.append({
            "concurrency": condition.get("concurrency"),
            "repetitions": condition.get("repetitions"),
            "requests_per_repetition": condition.get("requests_per_repetition"),
            "successful_requests": condition.get("successful_requests"),
            "failed_requests": condition.get("failed_requests"),
            "failure_rate": condition.get("failure_rate"),
            "aggregate_generation_throughput_tps": condition.get("aggregate_generation_throughput_tps"),
            "per_request_generation_throughput_tps": condition.get("per_request_generation_throughput_tps"),
            "latency_p50_s": condition.get("latency_p50_s"),
            "latency_p95_s": condition.get("latency_p95_s"),
            "latency_p99_s": condition.get("latency_p99_s"),
        })
    return {
        "formal": result.get("formal", False),
        "concurrencies": result.get("concurrencies"),
        "requests_per_concurrency": result.get("requests_per_concurrency"),
        "repetitions": result.get("repetitions"),
        "gen_tokens": result.get("gen_tokens"),
        "samples_count": result.get("samples_count"),
        "conditions": conditions,
    }


def compact_result(suite: str, result: dict[str, Any]) -> dict[str, Any]:
    if suite == "performance":
        return compact_performance(result)
    if suite == "server_performance":
        return compact_server(result)
    keys_by_suite = {
        "knowledge": ("version", "total", "correct", "accuracy", "pass_rate", "categories", "difficulties"),
        "coding": ("version", "total", "passed", "pass_rate", "categories", "failure_types"),
        "tool_call": ("version", "total", "passed", "pass_rate", "tool_selection_accuracy", "argument_accuracy", "execution_success_rate", "tool_rate", "args_rate", "exec_rate", "failure_types"),
        "agent_single": ("version", "total", "passed", "correct", "pass_rate", "avg_steps", "avg_tool_calls", "tool_calls_total", "failed_tool_calls", "repeated_tool_calls", "failure_types"),
        "agent_multi": ("version", "total", "passed", "correct", "pass_rate", "handoff_success_rate", "role_participation_success_rate", "avg_steps", "avg_tool_calls", "tool_calls_total", "failed_tool_calls", "invalid_tool_calls", "handoffs", "failure_types"),
    }
    return {key: result[key] for key in keys_by_suite[suite] if key in result}


def public_methodology() -> dict[str, Any]:
    methodology = load_json(METHODOLOGY_PATH)
    datasets = []
    for dataset_id, value in methodology.get("datasets", {}).items():
        datasets.append({
            "id": dataset_id,
            "version": value.get("historical_compatibility"),
            "public_path": value.get("path"),
            "sha256": value.get("sha256"),
            "scoring_type": value.get("scoring_type"),
            "reasoning": value.get("reasoning"),
        })
    return {
        "evaluator_versions": {
            "performance": "existing-v1",
            "server_performance": "existing-v1",
            "knowledge": "1.2",
            "coding": "existing-v1",
            "tool_call": "1.1",
            "agent_single": "1.1",
            "agent_multi": "1.1",
        },
        "datasets": datasets,
        "limitations": [
            "Performance and server-performance are reused historical runs, while Knowledge/Tool-call/Agent suites use the 2026-09-06 revalidation lane.",
            "Scores are fixed-harness observations, not universal product quality or safety scores.",
            "Agent-multi is a role/tool handoff evaluator in this release, not an independent-agent deployment benchmark.",
            "Raw runs, raw prompts/responses, and local model artifacts are not public.",
        ],
    }


def build_release() -> dict[str, Any]:
    summary = load_json(SUMMARY_PATH)
    models = summary.get("models", [])
    if len(models) != 18:
        raise ValueError(f"expected 18 summary models, got {len(models)}")

    public_models = []
    used_run_ids: set[str] = set()
    revalidated_ids: set[str] = set()
    reused_ids: set[str] = set()
    for item in models:
        model_key = f"{item['model']}|{item['variant']}"
        if model_key not in HISTORICAL_RUNS or model_key not in MODEL_MATCHERS:
            raise ValueError(f"missing historical source map for {model_key}")
        source_runs = item.get("source_runs", {})
        suites: dict[str, Any] = {}
        for suite in SUITES:
            if suite in EVALUATOR_SUITES:
                run_id = source_runs.get(suite)
                if not run_id:
                    raise ValueError(f"{model_key}: missing revalidated source run for {suite}")
                manifest, result = validate_run(run_id, EVALUATOR_SUITES[suite], model_key)
                revalidated_ids.add(run_id)
                source_type = "revalidated_evaluator"
            else:
                run_id = HISTORICAL_RUNS[model_key][suite]
                manifest, result = validate_run(run_id, suite, model_key)
                reused_ids.add(run_id)
                source_type = "reused_historical"
            if run_id in used_run_ids:
                raise ValueError(f"duplicate source run used twice: {run_id}")
            used_run_ids.add(run_id)
            suite_entry = {
                "status": "available",
                "source_type": source_type,
                "source_run_id": run_id,
                "evaluator_version": public_methodology()["evaluator_versions"][suite],
                "condition": safe_condition(manifest),
                **compact_result(suite, result),
            }
            alternatives = SERVER_ALTERNATES.get(model_key, []) if suite == "server_performance" else []
            if alternatives:
                alt_entries = []
                for alt_id in alternatives:
                    alt_manifest, alt_result = validate_run(alt_id, suite, model_key)
                    alt_entries.append({
                        "source_run_id": alt_id,
                        "condition": safe_condition(alt_manifest),
                        **compact_result(suite, alt_result),
                    })
                suite_entry["alternatives"] = alt_entries
            suites[suite] = suite_entry
        public_models.append({
            "model_id": re.sub(r"[^a-z0-9]+", "-", model_key.lower()).strip("-"),
            "model": item["model"],
            "variant": item["variant"],
            "quantization": item["quantization"],
            "benchmark_versions": public_methodology()["evaluator_versions"],
            "suites": suites,
            "provenance": {
                "hardware": "NVIDIA DGX Spark GB10",
                "reasoning_mode": "off",
                "raw_artifacts_public": False,
            },
        })

    methodology = public_methodology()
    release = {
        "schema_version": "gb10-benchmark-public-v1",
        "release_id": RELEASE_ID,
        "generated_at": RELEASE_DATE,
        "title": "GB10 LLM Benchmark v1 통합 재검증 결과",
        "status": "published-candidate",
        "scope": {
            "hardware": "NVIDIA DGX Spark GB10",
            "runtime": "llama.cpp",
            "reasoning_mode": "off",
            "raw_runs_public": False,
            "model_variant_count": len(public_models),
            "suite_count": len(SUITES),
            "revalidated_evaluator_runs": len(revalidated_ids),
            "reused_source_runs": len(reused_ids),
            "source_run_references": len(used_run_ids),
        },
        "suite_versions": methodology["evaluator_versions"],
        "methodology": methodology,
        "source_policy": {
            "revalidated_lane": "Knowledge 1.2, Tool-call 1.1, Agent-single 1.1, Agent-multi 1.1",
            "reused_lane": "Existing Performance, Server-performance, and Coding v1 runs",
            "source_run_id_semantics": "Each suite points to the exact local run used for this public projection.",
        },
        "models": public_models,
        "counts": {
            "models": len(public_models),
            "suites": len(SUITES),
            "revalidated_evaluator_runs": len(revalidated_ids),
            "reused_source_runs": len(reused_ids),
            "source_run_references": len(used_run_ids),
        },
    }
    validate_release(release)
    return release


def validate_release(release: dict[str, Any]) -> None:
    if len(release["models"]) != 18 or release["scope"]["suite_count"] != 7:
        raise ValueError("release count contract failed")
    if release["scope"]["revalidated_evaluator_runs"] != 72:
        raise ValueError("expected 72 revalidated evaluator runs")
    if release["scope"]["reused_source_runs"] != 54:
        raise ValueError("expected 54 reused source runs")
    if release["scope"]["source_run_references"] != 126:
        raise ValueError("expected 126 source run references")
    ids = [model["model_id"] for model in release["models"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate model_id")
    for model in release["models"]:
        if set(model["suites"]) != set(SUITES):
            raise ValueError(f"suite matrix incomplete for {model['model_id']}")
        for suite, entry in model["suites"].items():
            if entry["status"] == "available" and not entry.get("source_run_id"):
                raise ValueError(f"available suite has no source run: {model['model_id']} {suite}")
            if entry["status"] != "available" and any(key in entry for key in ("score", "pass_rate", "metrics")):
                raise ValueError(f"unavailable suite contains metrics: {model['model_id']} {suite}")


def scan_public_safety(payload: dict[str, Any]) -> list[str]:
    text = json.dumps(payload, ensure_ascii=False)
    return [marker for marker in PRIVATE_MARKERS if marker in text]


def write_release(output: Path, manifest_path: Path | None = None) -> dict[str, Any]:
    release = build_release()
    leaked = scan_public_safety(release)
    if leaked:
        raise ValueError(f"public safety scan failed: {leaked}")
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(release, ensure_ascii=False, indent=2) + "\n"
    output.write_text(encoded, encoding="utf-8")
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    manifest = {
        "release_id": RELEASE_ID,
        "schema_version": release["schema_version"],
        "sha256": digest,
        "counts": release["counts"],
        "raw_runs_public": False,
        "generated_from": [
            "results-public/models/summary-20260906.json",
            "results-public/methodology.json",
            "runs/full-cycles/*/manifest.json",
            "runs/<source-run-id>/manifest.json + result.json",
        ],
    }
    if manifest_path is None:
        manifest_path = output.with_suffix(".manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    manifest = write_release(args.output, args.manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
