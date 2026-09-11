from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from app.runners.agent_single import score_agent_task


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "datasets/agent-single-v1/agent-single-v1.jsonl"


def records():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_agent_single_v1_dataset_contract():
    items = records()
    assert len(items) == 12
    assert len({item["id"] for item in items}) == 12
    assert Counter(item["category"] for item in items) == {category: 3 for category in ("arithmetic_chain", "lookup_transform", "file_transform", "mixed_task")}
    for item in items:
        assert all(field in item for field in ("id", "category", "prompt", "expected"))
        expected = item["expected"]
        assert expected.get("sequence") or expected.get("required_tools")
        assert expected.get("dependency") is True


def test_agent_single_v1_recipe_contract_and_provenance():
    recipe = yaml.safe_load((PROJECT_ROOT / "recipes/agent-single-v1.yaml").read_text(encoding="utf-8"))
    dataset = PROJECT_ROOT / recipe["config"]["dataset"]
    assert recipe["suite"] == "agent-single"
    assert dataset.is_file()
    assert recipe["config"]["dataset_version"] == 1
    assert len(hashlib.sha256(dataset.read_bytes()).hexdigest()) == 64


def test_agent_single_v1_scoring_metrics():
    calls = [
        {"name": "calculator", "execution": {"result": 345}},
        {"name": "calculator", "execution": {"result": 352}},
    ]
    task = {"expected": {"sequence": ["calculator", "calculator"], "final": "352"}}
    result = score_agent_task(task, calls, "FINAL: 352", 2, 6)
    assert result["task_complete"] is True
    assert result["failed_tool_calls"] == 0
    assert result["repeated_tool_calls"] == 1


def test_agent_single_v1_recovers_after_failed_tool_call():
    calls = [
        {"name": "calculator", "execution": {"error": "bad op"}},
        {"name": "calculator", "execution": {"result": 5}},
    ]
    result = score_agent_task({"expected": {"sequence": ["calculator"], "final": "5"}}, calls, "FINAL: 5", 2, 6)
    assert result["task_complete"] is True
    assert result["failed_tool_calls"] == 1
