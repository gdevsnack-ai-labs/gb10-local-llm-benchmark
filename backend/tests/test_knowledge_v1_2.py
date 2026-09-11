from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

from app.runners.knowledge import score_answer

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "datasets/knowledge-v1.2/knowledge-v1.2.jsonl"


def test_knowledge_v1_2_dataset_and_hash_contract():
    records = [json.loads(line) for line in DATASET.read_text().splitlines() if line.strip()]
    assert len(records) == 100
    assert Counter(item["category"] for item in records) == {x: 20 for x in ("general", "korea", "math", "science", "logic")}
    assert Counter(item["difficulty"] for item in records) == {"easy": 25, "medium": 40, "hard": 35}
    assert hashlib.sha256(DATASET.read_bytes()).hexdigest() == "66e691da99a416fdf59887930d40c0dd7d12538b9f81b818e15e5bd0f6584079"


def test_knowledge_v1_2_recipe_contract():
    recipe = yaml.safe_load((ROOT / "recipes/knowledge-v1.2.yaml").read_text())
    assert recipe["version"] == 1.2
    assert recipe["config"]["thinking_mode"] == "no-think"
    assert recipe["config"]["max_tokens"] == 128


def test_knowledge_v1_2_scores_final_answer_only_and_tolerance():
    assert score_answer({"scoring_type": "multiple_choice", "expected": "B", "choices": [{"id": "A"}, {"id": "B"}]}, "<think>A</think>\nB")[0]
    assert not score_answer({"scoring_type": "numeric", "expected": 10}, "<think>2</think>\n2")[0]
    assert score_answer({"scoring_type": "numeric", "expected": 10, "tolerance": 0.2}, "10.1")[0]
    assert score_answer({"scoring_type": "numeric", "expected": 14}, "2 + 3 × 4 = 14.")[0]
    assert score_answer({"scoring_type": "numeric", "expected": 14}, "14")[0]
    assert score_answer({"scoring_type": "numeric", "expected": 14}, "14.")[0]
    assert score_answer({"scoring_type": "numeric", "expected": 14}, "Answer: 14")[0]


def test_knowledge_v1_2_normalizes_mc_formats_and_answer_text():
    sample = {
        "scoring_type": "multiple_choice",
        "expected": "B",
        "choices": [{"id": "A", "text": "Berlin"}, {"id": "B", "text": "Paris"}],
    }
    assert score_answer(sample, "B. Paris")[0]
    assert score_answer(sample, "The answer is B.")[0]
    assert score_answer(sample, "Answer: B")[0]
    assert score_answer(sample, "The capital of France is Paris.")[0]


def test_knowledge_v1_2_supports_choice_text_aliases():
    sample = {
        "scoring_type": "multiple_choice",
        "expected": "C",
        "choices": [
            {"id": "A", "text": "Yellow Sea"},
            {"id": "B", "text": "East China Sea"},
            {"id": "C", "text": "East Sea / Sea of Japan"},
            {"id": "D", "text": "South China Sea"},
        ],
    }
    assert score_answer(sample, "The Sea of Japan lies between the Korean Peninsula and Japan.")[0]
