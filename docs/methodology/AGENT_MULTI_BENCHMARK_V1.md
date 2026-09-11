# Agent-multi Benchmark v1

The Agent-multi suite evaluates a reproducible path in which agents divide Researcher and Calculator roles and pass prior results through handoffs to complete a task. Version 1 is a small formal benchmark for platform execution-path validation, not a comprehensive leaderboard.

It contains 10 questions: `lookup_calculate` 3, `file_calculate` 2, `mixed_handoff` 3, and `role_dependency` 2. The dataset is [agent-multi-v1.jsonl](../../datasets/agent-multi-v1/agent-multi-v1.jsonl), version 1, and the recipe is [`../../recipes/agent-multi-v1.yaml`](../../recipes/agent-multi-v1.yaml).

The runner records task completion, required role participation, handoffs and context transfer, required tool sequence, final answer, total steps/tool calls, and failed or invalid calls. Failures are classified as `missing_role`, `handoff_failure`, `context_transfer_failure`, `wrong_tool`, `wrong_arguments`, `tool_error`, `missing_required_step`, `incomplete_task`, `repeated_loop`, `final_answer_error`, or `max_steps_exceeded`.

A run preserves recipe, configuration, manifest, environment, result, events, and a dataset snapshot/hash. Per-question prompts, raw model responses, ordered multi-agent traces, role-transition/handoff payloads, parsed tool calls/results, final answers, and scoring metadata are stored in canonical execution evidence under `artifacts/agent-multi/<task-id>/`.

Model comparisons use the same recipe and dataset. Changing or extending the dataset requires a new version.
