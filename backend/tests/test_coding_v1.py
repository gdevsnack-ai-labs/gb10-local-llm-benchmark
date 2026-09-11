from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from app.runners.coding import _failure_type, run_tests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "datasets/coding-v1/coding-v1.jsonl"


def records():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_coding_v1_dataset_contract():
    items = records()
    assert len(items) == 12
    assert len({item["id"] for item in items}) == 12
    assert Counter(item["category"] for item in items) == {category: 3 for category in ("basic", "string", "collection", "edge_case")}
    for item in items:
        assert all(field in item for field in ("id", "category", "prompt", "function_name", "signature", "tests"))
        assert len(item["tests"]) >= 3


def test_coding_v1_recipe_contract_and_provenance():
    recipe = yaml.safe_load((PROJECT_ROOT / "recipes/coding-v1.yaml").read_text(encoding="utf-8"))
    dataset = PROJECT_ROOT / recipe["config"]["dataset"]
    assert recipe["suite"] == "coding"
    assert dataset.is_file()
    assert recipe["config"]["dataset_version"] == 1
    assert len(hashlib.sha256(dataset.read_bytes()).hexdigest()) == 64


def test_coding_v1_evaluator_runs_list_tests_and_preserves_result(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "solution.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    result = run_tests(workspace, ["assert add(2, 3) == 5", "assert add(0, 0) == 0", "assert add(-1, 1) == 0"], function_name="add")
    assert result["passed"] is True
    assert result["exit_code"] == 0
    assert result["stdout"]
    assert result["failure_type"] is None
    assert "from solution import add" in (workspace / "test_solution.py").read_text()


def test_coding_v1_failure_classification():
    assert _failure_type(1, "IndentationError: unexpected indent") == "syntax_error"
    assert _failure_type(1, "AssertionError") == "test_failure"
    assert _failure_type(124, "", timed_out=True) == "timeout"
