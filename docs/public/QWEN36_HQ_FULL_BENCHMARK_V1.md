# Qwen3.6 HQ Full Benchmark v1

## Cycle

- Cycle ID: `qwen36-hq-v1-full-20260905-115655-121304`
- Model: `Qwen3.6-35B-A3B-NVFP4-MTP-HQ.gguf`
- Model path: `<model-root>/qwen3.6-35b-a3b/Qwen3.6-35B-A3B-NVFP4-MTP-HQ.gguf` (portable notation; local absolute path omitted)
- Started: `2026-09-05T02:56:55.814953Z`
- Finished: `2026-09-05T03:14:02.868026Z`
- Platform commit: `0adf3c8294df3fbfaa1857192e5e9b58108e9335`
- llama.cpp: `e107984bc` (build 10788), NVIDIA GB10, CUDA, aarch64
- Execution: seven suites run consecutively in the requested order. Recipes and scoring conditions were not changed; the model path was supplied as the run configuration override.
- Retries: none. Platform failures: none. All seven runs completed.

All paths below are relative to the project root unless shown as absolute paths. Each run contains `manifest.json`, `recipe.yaml`, `resolved-config.yaml`, `environment.json`, `events.jsonl`, `result.json`, and raw server/log artifacts. Dataset suites additionally contain `dataset-snapshot.jsonl`.

## Results

### 1. Performance

- Run ID: `20260905-115655-385b40`
- Status: `completed`
- Evidence: `runs/20260905-115655-385b40/`
- Scoring summary (tokens/s, mean ± stddev over 5 repetitions):

| Condition | Result |
|---|---:|
| PP 512 | 2282.108 ± 78.250 |
| PP 2K | 2240.548 ± 5.264 |
| PP 8K | 2246.775 ± 18.578 |
| PP 32K | 2091.597 ± 9.099 |
| TG 512 | 68.730 ± 0.581 |

Raw benchmark output: `runs/20260905-115655-385b40/llama-bench.stdout.json` and `llama-bench.stderr.log`.

### 2. Server-performance

- Run ID: `20260905-115943-c5d61a`
- Status: `completed`
- Evidence: `runs/20260905-115943-c5d61a/`
- Three repetitions, four requests per repetition, 512 generated tokens per request. Aggregate/per-request throughput is tokens/s; latency is seconds.

| Concurrency | Aggregate throughput | Per-request throughput | P50 | P95 | P99 | Failure rate |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 87.120 | 87.136 | 5.861 | 5.956 | 5.969 | 0% (0/12) |
| 2 | 119.365 | 59.885 | 8.522 | 8.959 | 9.075 | 0% (0/24) |
| 4 | 153.259 | 38.793 | 13.164 | 13.972 | 14.136 | 0% (0/48) |
| 8 | 201.806 | 25.849 | 20.041 | 22.277 | 22.745 | 0% (0/96) |

Raw server log and samples: `runs/20260905-115943-c5d61a/llama-server.log` and `samples.jsonl`.

### 3. Knowledge

- Run ID: `20260905-120928-50c35c`
- Status: `completed`
- Result: 25 total, 13 correct, accuracy/pass rate **52.00%**
- Dataset provenance: SHA-256 `44883816f2b11f8560c69a6c28933c2496ea137a5b98860dd102d397349f650c`; snapshot `runs/20260905-120928-50c35c/dataset-snapshot.jsonl`

| Category | Correct / total | Accuracy |
|---|---:|---:|
| general | 2 / 5 | 40% |
| korea | 1 / 5 | 20% |
| math | 5 / 5 | 100% |
| science | 1 / 5 | 20% |
| logic | 4 / 5 | 80% |

Evidence: `runs/20260905-120928-50c35c/` (including `result.json`, `events.jsonl`, `samples.jsonl`, raw log).

### 4. Coding

- Run ID: `20260905-120944-4cc44e`
- Status: `completed`
- Result: 12 total, 10 passed, pass rate **83.33%**
- Dataset provenance: SHA-256 `53a283316be1ab63ee04c051d5194decbc3c7e27b76e5c177293bcab87dccbbd`; snapshot `runs/20260905-120944-4cc44e/dataset-snapshot.jsonl`

| Category | Passed / total | Pass rate |
|---|---:|---:|
| basic | 3 / 3 | 100% |
| string | 3 / 3 | 100% |
| collection | 3 / 3 | 100% |
| edge_case | 1 / 3 | 33.33% |

Failure type: `syntax_error` (2). Evidence: `runs/20260905-120944-4cc44e/` including repository snapshots and raw samples.

### 5. Tool-call

- Run ID: `20260905-121126-449f81`
- Status: `completed`
- Result: 15 total, 11 passed, pass rate **73.33%**
- Tool selection accuracy: **80.00%**
- Argument accuracy: **73.33%**
- Execution success rate: **86.67%**
- Dataset provenance: SHA-256 `8c0c1abefa2825c97341afaee620adbbf60cf43add20e0535c599872733065d5`; snapshot `runs/20260905-121126-449f81/dataset-snapshot.jsonl`

Category pass rates: `single_tool` 4/5 (80%), `tool_selection` 2/3 (66.67%), `multi_step` 1/3 (33.33%), `recovery` 2/2 (100%), `no_tool` 2/2 (100%). Failure types: `wrong_arguments` 1, `missing_tool_call` 1, `incomplete_sequence` 2.

Evidence: `runs/20260905-121126-449f81/`.

### 6. Agent-single

- Run ID: `20260905-121207-1eae93`
- Status: `completed`
- Result: 12 total, 8 passed, pass rate **66.67%**
- Average steps: **3.25**; average tool calls: **2.25**
- Dataset provenance: SHA-256 `188a63368a0631cc6cc6a80a8eed165f559f8131b5196ba28a951c428479b5d5`; snapshot `runs/20260905-121207-1eae93/dataset-snapshot.jsonl`

Category pass rates: `arithmetic_chain` 3/3 (100%), `lookup_transform` 2/3 (66.67%), `file_transform` 0/3 (0%), `mixed_task` 3/3 (100%). Failure types: `tool_error` 2, `missing_required_step` 2.

Evidence: `runs/20260905-121207-1eae93/` including per-case trace artifacts under `artifacts/agent-single/`.

### 7. Agent-multi

- Run ID: `20260905-121304-b0b78c`
- Status: `completed`
- Result: 10 total, 4 passed, pass rate **40.00%**
- Handoff success rate: **70.00%**
- Role participation success rate: **60.00%**
- Average steps: **2.80**; average tool calls: **1.80**
- Dataset provenance: SHA-256 `ee9bc5035f9ca17be36a3749e62322d767232570960ae80d3041b2b1741a010a`; snapshot `runs/20260905-121304-b0b78c/dataset-snapshot.jsonl`

Category pass rates: `lookup_calculate` 1/3 (33.33%), `file_calculate` 1/2 (50%), `mixed_handoff` 1/3 (33.33%), `role_dependency` 1/2 (50%). Failure types: `missing_role` 4, `missing_required_step` 1, `tool_error` 1.

Evidence: `runs/20260905-121304-b0b78c/` including per-case traces under `artifacts/agent-multi/`.

## Regression

- Targeted v1/backend regression: **33 passed**, 1 deprecation warning (`httpx`/Starlette TestClient).
- `python3 -m compileall -q app`: passed.
- Frontend `npm run build`: passed.
- Full `python3 -m pytest tests -q`: reproduced the existing `tests/test_api.py::test_health` environment hang; the command was stopped by a 20-second timeout after six tests had started (`EXIT 124`). This is recorded as a pre-existing test-environment issue, distinct from the full-cycle runs: all seven benchmark Run IDs completed successfully and their managed servers shut down normally.

## Evidence index

The machine-readable cycle manifest is `runs/full-cycles/qwen36-hq-v1-full-20260905-115655-121304/manifest.json`. The seven run directories preserve status events, recipe/resolved config, environment, result, and raw response/log artifacts. The four dataset-based runs preserve their exact dataset snapshot and SHA-256 provenance.
