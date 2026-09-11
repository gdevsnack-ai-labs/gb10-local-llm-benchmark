# Knowledge Benchmark v1

## Purpose

The Knowledge suite runs a fixed dataset through a reproducible execution path and deterministic scoring rules so that model results can be compared under the same conditions. Version 1 is a small formal benchmark for validating the platform execution path, not a comprehensive model leaderboard.

## Dataset

The suite contains 25 questions across five categories: `general`, `korea`, `math`, `science`, and `logic`, with five questions per category. The dataset is [knowledge-v1.jsonl](../../datasets/knowledge-v1/knowledge-v1.jsonl), version 1, and the recipe is defined in [`../../recipes/knowledge-v1.yaml`](../../recipes/knowledge-v1.yaml).

## Scoring

- `multiple_choice`: extract the answer choice ID and compare it with the expected choice ID
- `numeric`: normalize the number in the response and compare it with the expected number
- `exact_match`: compare after trimming, case-folding, and whitespace normalization

No LLM-as-a-judge is used. The runner records total, correct, and accuracy values overall and by category.

## Evidence and comparison rule

A canonical run records `recipe.yaml`, `resolved-config.yaml`, `manifest.json`, `environment.json`, `result.json`, `events.jsonl`, `samples.jsonl`, and a dataset snapshot. `result.json` and per-question evidence include the dataset path/version/SHA-256, raw response, normalized answer, expected answer, scoring type, and pass/fail result.

Model comparisons must use the same recipe and dataset and should consider each run's environment, configuration, and evidence. This v1 dataset is a small formal dataset for platform validation. Expanding or materially changing its questions requires a new dataset version.
