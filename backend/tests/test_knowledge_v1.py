from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from app.runners.knowledge import score_answer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "datasets/knowledge-v1/knowledge-v1.jsonl"


def load_dataset():
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_knowledge_v1_dataset_contract():
    records = load_dataset()
    assert len(records) == 25
    assert len({record["id"] for record in records}) == 25
    assert Counter(record["category"] for record in records) == {category: 5 for category in ("general", "korea", "math", "science", "logic")}
    assert {record["scoring_type"] for record in records} <= {"multiple_choice", "numeric", "exact_match"}
    for record in records:
        assert all(field in record for field in ("id", "category", "prompt", "scoring_type", "expected"))
        if record["scoring_type"] == "multiple_choice":
            assert record["choices"]
            assert record["expected"] in {choice["id"] for choice in record["choices"]}
        if record["scoring_type"] == "numeric":
            float(record["expected"])


def test_knowledge_v1_recipe_contract_and_provenance():
    recipe_path = PROJECT_ROOT / "recipes/knowledge-v1.yaml"
    recipe = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    dataset = PROJECT_ROOT / recipe["config"]["dataset"]
    assert recipe["suite"] == "knowledge"
    assert dataset.is_file()
    assert recipe["config"]["dataset_version"] == 1
    assert len(hashlib.sha256(dataset.read_bytes()).hexdigest()) == 64


def test_knowledge_v1_scoring_and_category_summary_shape():
    records = load_dataset()
    category_summary = {category: {"total": 0, "correct": 0} for category in ("general", "korea", "math", "science", "logic")}
    for record in records:
        response = str(record["expected"])
        passed, normalized, evidence = score_answer(record, response)
        assert passed is True
        assert normalized
        assert evidence["expected_normalized"] == normalized.casefold() if record["scoring_type"] != "numeric" else normalized == evidence["expected_normalized"]
        category_summary[record["category"]]["total"] += 1
        category_summary[record["category"]]["correct"] += int(passed)
    assert all(summary["total"] == 5 and summary["correct"] == 5 for summary in category_summary.values())


def test_knowledge_v1_scoring_ignores_non_choice_tokens_and_think_markers():
    sample = {"scoring_type": "multiple_choice", "expected": "B", "choices": [{"id": "A"}, {"id": "B"}]}
    assert score_answer(sample, "reasoning token 1\nB")[0] is True
    exact = {"scoring_type": "exact_match", "expected": "Y"}
    assert score_answer(exact, "\n<think>\n</think>\nY")[0] is True
    assert score_answer({"scoring_type": "numeric", "expected": 14}, "<think>2 + 3 * 4</think>\n14")[0] is True
    assert score_answer({"scoring_type": "numeric", "expected": 14}, "<think>2 + 3 * 4")[0] is False
