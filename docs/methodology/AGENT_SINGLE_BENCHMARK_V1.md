# Agent-single Benchmark v1

The Agent-single suite evaluates a reproducible path in which one agent selects tools across multiple steps and uses previous results to complete a task. Version 1 is a small formal benchmark for platform validation, not a leaderboard.

It contains 12 questions: `arithmetic_chain`, `lookup_transform`, `file_transform`, and `mixed_task`, with three questions in each category. The dataset is [agent-single-v1.jsonl](../../datasets/agent-single-v1/agent-single-v1.jsonl), version 1, and the recipe is [`../../recipes/agent-single-v1.yaml`](../../recipes/agent-single-v1.yaml).

The runner records task completion, required tool sequence/dependencies, final answer, step count, tool-call count, failed or invalid calls, and repeated calls. Failures are classified as `wrong_tool`, `wrong_arguments`, `tool_error`, `missing_required_step`, `incomplete_task`, `repeated_loop`, `final_answer_error`, or `max_steps_exceeded`.

A run preserves recipe, configuration, manifest, environment, result, events, and a dataset snapshot/hash. Per-question prompts, raw model responses, ordered agent traces, parsed tool calls/arguments/results, final answers, and scoring metadata are stored in canonical execution evidence under `artifacts/agent-single/<task-id>/`.

Execution uses a process-local deterministic tool simulator and a maximum-step limit. Model comparisons use the same recipe and dataset; changing or extending the dataset requires a new version.
