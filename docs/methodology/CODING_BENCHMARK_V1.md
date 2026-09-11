# Coding Benchmark v1

The Coding suite runs a fixed dataset through actual Python code generation and pytest evaluation. Version 1 is a small formal benchmark for validating the platform execution path and artifact contract, not a comprehensive leaderboard.

It contains 12 questions across four categories—`basic`, `string`, `collection`, and `edge_case`—with three questions per category. The dataset is [coding-v1.jsonl](../../datasets/coding-v1/coding-v1.jsonl), version 1, and the recipe is [`../../recipes/coding-v1.yaml`](../../recipes/coding-v1.yaml).

For each question, generated code is saved to a workspace and pytest is executed. The runner records total, passed, pass rate, and per-question pass/fail values overall and by category. Failures are classified as `extraction_error`, `syntax_error`, `test_failure`, `runtime_error`, or `timeout`.

A run records recipe, configuration, manifest, environment, result, events, and a dataset snapshot/hash. Per-question prompt/task specifications, generated source, pytest files, stdout/stderr, and result metadata are stored in the canonical execution evidence under `artifacts/coding/<task-id>/`.

The evaluation currently uses a constrained execution environment with process-level workspace isolation and timeouts. Model comparisons use the same recipe and dataset; expanding or materially changing the dataset requires a new version.
