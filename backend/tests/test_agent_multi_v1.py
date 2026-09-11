from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from app.runners.agent_multi import calculate_handoff_success_rate, score_multi_task


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "datasets/agent-multi-v1/agent-multi-v1.jsonl"


def records():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_agent_multi_v1_dataset_contract():
    items = records()
    assert len(items) == 10
    assert len({item["id"] for item in items}) == 10
    assert Counter(item["category"] for item in items) == {"lookup_calculate": 3, "file_calculate": 2, "mixed_handoff": 3, "role_dependency": 2}
    for item in items:
        assert all(field in item for field in ("id", "category", "prompt", "expected"))
        assert item["expected"].get("roles")
        assert item["expected"].get("required_tools")
        assert item["expected"].get("handoff") is True


def test_agent_multi_v1_recipe_contract_and_provenance():
    recipe = yaml.safe_load((PROJECT_ROOT / "recipes/agent-multi-v1.yaml").read_text(encoding="utf-8"))
    dataset = PROJECT_ROOT / recipe["config"]["dataset"]
    assert recipe["suite"] == "agent-multi"
    assert dataset.is_file()
    assert recipe["config"]["dataset_version"] == 1
    assert len(hashlib.sha256(dataset.read_bytes()).hexdigest()) == 64


def test_agent_multi_v1_scoring_handoff_and_transfer():
    calls = [
        {"name": "kv_get", "role": "researcher", "arguments": {"key": "capital:japan"}, "execution": {"result": "Tokyo"}},
        {"name": "calculator", "role": "calculator", "arguments": {"expression": "5 * 3"}, "execution": {"result": 15}},
    ]
    handoffs = [{"from_role": "researcher", "to_role": "calculator", "transferred_context": {"result": "Tokyo"}}]
    task = {"expected": {"roles": ["researcher", "calculator"], "handoff": True, "required_tools": ["kv_get", "calculator"], "dependency": True, "final": "15"}}
    result = score_multi_task(task, calls, handoffs, "The final answer is 15.", 2, 8)
    assert result["task_complete"] is True
    assert result["handoff_success"] is True
    assert result["context_transfer_success"] is True


def test_handoff_success_rate_uses_task_denominator_and_ratio_convention():
    assert calculate_handoff_success_rate(10, 10) == 1.0
    assert calculate_handoff_success_rate(7, 10) == 0.7
    # Multiple role transitions are not multiple successful tasks.
    assert calculate_handoff_success_rate(11, 10) == 1.0
    assert calculate_handoff_success_rate(0, 0) == 0.0


def test_agent_multi_v1_recovers_after_failed_tool_call():
    calls = [
        {"name": "kv_get", "role": "researcher", "arguments": {"key": "capital:japan"}, "execution": {"result": "Tokyo"}},
        {"name": "calculator", "role": "calculator", "arguments": {"op": "add"}, "execution": {"error": "bad args"}},
        {"name": "calculator", "role": "calculator", "arguments": {"expression": "5 + 3"}, "execution": {"result": 8}},
    ]
    handoffs = [{"from_role": "researcher", "to_role": "calculator", "transferred_context": {"result": "Tokyo"}}]
    task = {"expected": {"roles": ["researcher", "calculator"], "handoff": True, "required_tools": ["kv_get", "calculator"], "dependency": True, "final": "8"}}
    result = score_multi_task(task, calls, handoffs, "FINAL: 8", 3, 8)
    assert result["task_complete"] is True
    assert result["failed_tool_calls"] == 1
