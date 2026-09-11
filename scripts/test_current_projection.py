#!/usr/bin/env python3
"""Validate the current public benchmark projection without reading raw responses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTION = ROOT / "results-public/releases/gb10-local-llm-benchmark.json"
MANIFEST = ROOT / "results-public/releases/gb10-local-llm-benchmark.manifest.json"

PRIVATE_MARKERS = (
    "/home/", "/media/", "/tmp/", "127.0.0.1", "localhost", "SUPABASE_SERVICE",
    "BEGIN PRIVATE KEY", "Bearer ", "raw_response", "raw_model_responses",
    "llama-server.log", "environment.json",
)


def main() -> int:
    encoded = PROJECTION.read_bytes()
    projection = json.loads(encoded)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert projection["release_id"] == "gb10-local-llm-benchmark"
    assert projection["scope"]["model_variant_count"] == len(projection["models"]) == 23
    assert projection["scope"]["suite_count"] == 7
    assert projection["scope"]["source_run_references"] == 161
    assert projection["scope"]["fresh_full_cycle_runs"] == 28
    assert projection["counts"] == {
        "models": 23,
        "suites": 7,
        "revalidated_evaluator_runs": 76,
        "reused_source_runs": 57,
        "fresh_full_cycle_runs": 28,
        "source_run_references": 161,
    }

    model_ids = {model["model_id"] for model in projection["models"]}
    assert len(model_ids) == 23
    ling = next(model for model in projection["models"] if model["model_family_slug"] == "ling-3-0-flash")
    assert ling["variant"] == "Heretic MXFP4"
    assert ling["quantization"] == "MXFP4_MOE"
    assert ling["mtp_mode"] == "mtp"
    assert ling["suites"]["knowledge"]["source_run_id"] == "20260907-185311-238e8f"
    assert ling["suites"]["server_performance"]["condition"]["spec_type"] == "mtp"
    assert ling["suites"]["agent_multi"]["source_run_id"] == "20260907-190139-b1c4e0"
    assert len(ling["suites"]) == 7

    n25 = next(model for model in projection["models"] if model["model_family_slug"] == "n2-5-mini")
    assert n25["model"] == "N2.5 Mini"
    assert n25["mtp_mode"] == "non-mtp"
    assert n25["suites"]["tool_call"]["source_run_id"] == "20260910-175508-09d7a2"
    assert n25["suites"]["tool_call"]["source_type"] == "fresh_full_cycle"
    assert n25["suites"]["server_performance"]["condition"]["spec_type"] == "none"
    assert len(n25["suites"]) == 7

    text = encoded.decode("utf-8")
    leaked = [marker for marker in PRIVATE_MARKERS if marker in text]
    assert not leaked, leaked

    digest = hashlib.sha256(encoded).hexdigest()
    assert digest == manifest["sha256"]
    assert manifest["counts"] == projection["counts"]

    print(json.dumps({"status": "pass", "release_id": projection["release_id"], "sha256": digest, "counts": projection["counts"], "ling_model_id": ling["model_id"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
