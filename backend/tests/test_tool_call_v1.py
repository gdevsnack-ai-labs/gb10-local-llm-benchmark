from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from app.runners.tool_call import score_task, simulator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "datasets/tool-call-v1/tool-call-v1.jsonl"


def records():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_tool_call_v1_dataset_contract():
    items = records()
    assert len(items) == 15
    assert len({item["id"] for item in items}) == 15
    assert Counter(item["category"] for item in items) == {"single_tool": 5, "tool_selection": 3, "multi_step": 3, "recovery": 2, "no_tool": 2}
    for item in items:
        assert all(field in item for field in ("id", "category", "prompt", "expected"))
        expected = item["expected"]
        assert expected.get("tools", expected.get("sequence", [])) is not None
        if item["category"] == "no_tool":
            assert expected["tool_calls"] == 0


def test_tool_call_v1_recipe_contract_and_provenance():
    recipe = yaml.safe_load((PROJECT_ROOT / "recipes/tool-call-v1.yaml").read_text(encoding="utf-8"))
    dataset = PROJECT_ROOT / recipe["config"]["dataset"]
    assert recipe["suite"] == "tool-call"
    assert dataset.is_file()
    assert recipe["config"]["dataset_version"] == 1
    assert len(hashlib.sha256(dataset.read_bytes()).hexdigest()) == 64


def test_tool_call_v1_simulator_and_scoring():
    calls = [{"name": "calculator", "arguments": {"expression": "15 * 23"}, "execution": simulator("calculator", {"expression": "15 * 23"})}]
    task = {"expected": {"tools": [{"name": "calculator", "arguments": {"expression": "15 * 23"}}], "final": "345"}}
    assert calls[0]["execution"] == {"result": 345}
    assert score_task(task, calls, "345")["passed"] is True
    assert score_task({"expected": {"tool_calls": 0, "final": "7"}}, [], "7")["passed"] is True
    assert score_task({"expected": {"tools": [{"name": "kv_get", "arguments": {"key": "capital:japan"}}], "final": "Tokyo"}}, [{"name": "kv_get", "arguments": {"key": "capital:japan"}, "execution": {"result": "Tokyo"}}], "The answer is Tokyo.")["passed"] is True
    recovery = {"expected": {"sequence": ["read_file", "read_file"], "first_may_fail": True}}
    recovery_calls = [{"name": "read_file", "arguments": {}, "execution": {"error": "file not found"}}, {"name": "read_file", "arguments": {}, "execution": {"result": "hello world"}}]
    assert score_task(recovery, recovery_calls, "hello world")["execution_success"] is True
