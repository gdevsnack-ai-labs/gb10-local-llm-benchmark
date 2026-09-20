from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTION = ROOT / "results-public/releases/gb10-local-llm-benchmark.json"
MANIFEST = ROOT / "results-public/releases/gb10-local-llm-benchmark.manifest.json"
EXPECTED_SHA256 = "96e742cecc408f408a6b6f9ce19fd91db2463390a3afa0b49398a01db1b11927"
EXPECTED_SUITES = {
    "performance", "server_performance", "knowledge", "coding",
    "tool_call", "external_tool_eval", "agent_single", "agent_multi",
}

PRIVATE_VALUE_PATTERNS = [
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"BEGIN (?:RSA |EC )?PRIVATE KEY"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
]


def test_current_projection_contract_and_hash():
    encoded = PROJECTION.read_bytes()
    projection = json.loads(encoded)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert projection["release_id"] == "gb10-local-llm-benchmark"
    assert projection["schema_version"] == "gb10-benchmark-public-v1"
    assert projection["scope"]["model_variant_count"] == len(projection["models"]) == 32
    assert projection["scope"]["suite_count"] == 8
    assert set(projection["suite_versions"]) == EXPECTED_SUITES
    assert projection["scope"]["source_run_references"] == 241
    assert projection["scope"]["external_evaluator_runs"] == 17
    assert projection["scope"]["raw_runs_public"] is False
    assert manifest["sha256"] == EXPECTED_SHA256
    assert hashlib.sha256(encoded).hexdigest() == EXPECTED_SHA256
    assert manifest["counts"] == projection["counts"]


def test_public_projection_has_no_private_values():
    text = PROJECTION.read_text(encoding="utf-8") + MANIFEST.read_text(encoding="utf-8")
    forbidden = ["/home/", "/media/", "127.0.0.1", "localhost", "/tmp/", "raw_response", "raw_model_responses"]
    assert not [marker for marker in forbidden if marker in text]
    assert not [pattern.pattern for pattern in PRIVATE_VALUE_PATTERNS if pattern.search(text)]


def test_available_suites_have_source_references():
    projection = json.loads(PROJECTION.read_text(encoding="utf-8"))
    for model in projection["models"]:
        assert set(model["suites"]) == EXPECTED_SUITES
        for suite in model["suites"].values():
            assert suite["status"] in {"available", "unavailable", "not_in_public_export"}
            if suite["status"] == "available":
                assert suite.get("source_run_id")
