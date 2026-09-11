# Gemma4 26B QAT MTP Comparison

- Cycle: `gemma4-qat-mtp-compare-20260905-212404-213513`
- Draft model: `gemma-4-26B-A4B-it-qat-assistant-MTP-Q8_0.gguf`
- Base models: QAT NVFP4 and QAT Q4_0
- Existing non-MTP runs are compared with new MTP-draft runs; no historical base result was overwritten.

## Runs

| Base | non-MTP | MTP draft |
|---|---|---|
| QAT NVFP4 | `20260905-201504-70bab9` | `20260905-212404-c6e555` |
| QAT Q4_0 | `20260905-204454-8fee22` | `20260905-213513-340ca6` |

All four runs use the server-performance v1 workload (concurrency 1/2/4/8, 4 requests, 3 repetitions, 512 generation tokens). MTP runs use `spec_type: mtp`, `spec_draft_n_max: 3`, and the draft model above. Non-MTP runs use `spec_type: none`, `spec: off`.

## Aggregate throughput / p50 latency

Values are `aggregate tokens/s / p50 seconds`; failure rate is shown separately.

| Base | Mode | c=1 | c=2 | c=4 | c=8 |
|---|---|---:|---:|---:|---:|
| NVFP4 | non-MTP | 36.1 / 14.18 | 63.0 / 16.22 | 114.8 / 17.75 | 175.4 / 23.34 |
| NVFP4 | MTP draft | 64.0 / 7.98 | 90.5 / 11.14 | 149.6 / 12.24 | 183.3 / 18.63 |
| Q4_0 | non-MTP | 49.7 / 10.25 | 79.1 / 12.95 | 137.0 / 14.78 | 193.0 / 21.34 |
| Q4_0 | MTP draft | 90.9 / 5.62 | 128.7 / 7.11 | 208.4 / 8.81 | 297.8 / 12.21 |

Failure rate: NVFP4 non-MTP 0%, NVFP4 MTP draft 1.04% (one request), Q4_0 non-MTP 0%, Q4_0 MTP draft 0%. The NVFP4 MTP result is retained as observed; it was not rescored or rerun.

Raw evidence, `resolved-config.yaml`, `environment.json`, `events.jsonl`, `llama-server.log`, `result.json`, and request samples are preserved under each run directory. The machine-readable index is retained in canonical local evidence and is not distributed here.

## Other v1 suite results (original non-MTP full runs)

MTP draft is a server runtime option; it is not applied to the evaluator suites here. The remaining full-benchmark results below are the original non-MTP runs, retained as-is for capability comparison.

| Base | Knowledge | Coding | Tool-call | Agent-single | Agent-multi |
|---|---:|---:|---:|---:|---:|
| QAT NVFP4 | 9/25 (36%) | 4/12 (33.33%) | 13/15 (86.67%) | 6/12 (50%) | 0/10 (0%) |
| QAT Q4_0 | 10/25 (40%) | 3/12 (25%) | 11/15 (73.33%) | 5/12 (41.67%) | 2/10 (20%) |

Original run IDs: NVFP4 `20260905-201154-565aad`, `20260905-202945-a45b05`, `20260905-203019-49bf2b`, `20260905-203541-bd1bc1`, `20260905-203710-72453a`, `20260905-203946-ef14b1`; Q4_0 `20260905-204203-52bb92`, `20260905-205657-ff3167`, `20260905-205718-854c2d`, `20260905-210124-e8c4b6`, `20260905-210237-14f288`, `20260905-210433-645a83` (in suite order: performance, knowledge, coding, tool-call, agent-single, agent-multi). Their performance results are the base measurements used alongside the MTP/non-MTP server comparison above.
