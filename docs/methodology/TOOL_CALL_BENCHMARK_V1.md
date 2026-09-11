# Tool-call Benchmark v1

The Tool-call suite runs a fixed dataset with a deterministic tool simulator. Version 1 is a small formal benchmark for stabilizing and comparing execution paths, not a comprehensive function-calling leaderboard.

It contains 15 questions: `single_tool` 5, `tool_selection` 3, `multi_step` 3, `recovery` 2, and `no_tool` 2. The dataset is [tool-call-v1.jsonl](../../datasets/tool-call-v1/tool-call-v1.jsonl), version 1, and the recipe is [`../../recipes/tool-call-v1.yaml`](../../recipes/tool-call-v1.yaml).

The scorer evaluates tool selection, arguments, execution success, and final task success. Multi-step cases check the expected sequence and dependency; recovery cases check retry behavior after an error; no-tool cases check that unnecessary calls are avoided. Failures are classified as `wrong_tool`, `wrong_arguments`, `execution_error`, `missing_tool_call`, `unnecessary_tool_call`, `incomplete_sequence`, or `final_answer_error`.

A run preserves recipe, configuration, manifest, environment, result, events, and a dataset snapshot/hash. Per-question prompts/tasks, raw model responses, parsed tool calls and arguments, tool execution results, final answers, and scoring metadata are stored in canonical execution evidence under `artifacts/tool-call/<task-id>/`.

Model comparisons use the same recipe and dataset. Changing or extending the dataset requires a new version.
