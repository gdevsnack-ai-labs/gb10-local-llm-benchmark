# N2 Mini Full Benchmark v1

- Cycle ID: `n2mini-v1-full-20260905-063010-070449`
- Model family: N2 Mini (4 local GGUF variants)
- Window: `2026-09-05T06:30:10Z` – `2026-09-05T07:04:49Z`
- Platform commit: `3b1f357b5aebf4aa34d370c781f32ab0a7c0db13`
- llama.cpp: `e107984bcffcfd701e82738092a2b000b6fda7a2`

This is a new sequential full-cycle run using the existing v1 recipes and scoring rules. No dataset or recipe was changed.

## Run index

| Model | performance | server-performance | knowledge | coding | tool-call | agent-single | agent-multi |
|---|---|---|---|---|---|---|---|
| Q4_K_M UD | `20260905-153010-ec5db8` | `20260905-153342-4eaed8` **failed** | `20260905-153353-afa7fa` | `20260905-153414-41f495` | `20260905-153606-057aee` | `20260905-153637-30f7d7` | `20260905-153718-7cd28f` |
| Q5_K_XL UD | `20260905-153800-d9d315` | `20260905-154151-16d75d` **failed** | `20260905-154223-f00975` | `20260905-154314-4cdc32` | `20260905-154506-38acb9` | `20260905-154607-f68559` | `20260905-154718-4a9bd7` |
| Q5_K_M | `20260905-154830-2ed4f8` | `20260905-155211-86727c` **failed** | `20260905-155223-0a2ebc` | `20260905-155244-eaa71f` | `20260905-155415-83958b` | `20260905-155457-902dfa` | `20260905-155538-390e8e` |
| Q6_K | `20260905-155619-88ff7e` | `20260905-160021-b40dc1` **failed** | `20260905-160032-42773f` | `20260905-160053-23c1f9` | `20260905-160235-6e14ca` | `20260905-160316-a313e5` | `20260905-160358-d4338d` |

Every run directory contains `manifest.json`, `recipe.yaml`, `resolved-config.yaml`, `environment.json`, `events.jsonl`, and suite-specific `result.json`/raw evidence where applicable. The complete machine-readable index is [the cycle manifest](../runs/full-cycles/n2mini-v1-full-20260905-063010-070449/manifest.json).

## Performance

Throughput is tokens/s; `±` is the recorded sample standard deviation.

| Model | PP512 | PP2K | PP8K | PP32K | TG512 |
|---|---:|---:|---:|---:|---:|
| Q4_K_M UD | 2091.12 ±38.34 | 2015.56 ±10.20 | 1966.65 ±13.80 | 1808.51 ±2.96 | 63.76 ±0.09 |
| Q5_K_XL UD | 1531.38 ±266.48 | 1866.22 ±9.91 | 1818.71 ±51.28 | 1691.70 ±10.26 | 59.35 ±0.08 |
| Q5_K_M | 1929.54 ±120.79 | 1858.83 ±52.18 | 1854.38 ±24.46 | 1732.16 ±2.22 | 64.08 ±0.12 |
| Q6_K | 1750.12 ±57.25 | 1725.22 ±3.43 | 1671.91 ±9.70 | 1565.13 ±3.66 | 58.68 ±0.12 |

## Server-performance

The first four server-performance runs used the recipe's original `spec_type: mtp` and failed before serving requests because each N2 Mini GGUF lacks MTP layers. Their raw logs are preserved and are not overwritten. For the requested model-aware execution, four new runs used the same formal recipe and workload with an explicit no-speculative override (`spec_type: none`, `spec: off`). These are the valid server-performance results below.

| Model | no-MTP Run ID | c=1 aggregate / per-request / p50 / p95 | c=2 aggregate / per-request / p50 / p95 | c=4 aggregate / per-request / p50 / p95 | c=8 aggregate / per-request / p50 / p95 | failure rate |
|---|---|---|---|---|---|---:|
| Q4_K_M UD | `20260905-161120-b37a54` | 60.04 / 60.04 / 8.522 / 8.583 | 91.63 / 45.82 / 11.177 / 11.232 | 141.43 / 35.43 / 14.409 / 15.386 | 180.38 / 22.79 / 22.141 / 23.568 | 0% |
| Q5_K_XL UD | `20260905-162247-e466ce` | 56.46 / 56.46 / 9.068 / 9.144 | 85.01 / 42.51 / 12.037 / 12.093 | 135.91 / 34.01 / 15.065 / 15.551 | 162.91 / 20.55 / 24.734 / 26.052 | 0% |
| Q5_K_M | `20260905-163531-7e5f86` | 60.50 / 60.50 / 8.459 / 8.531 | 89.92 / 44.97 / 11.396 / 11.465 | 137.38 / 34.44 / 14.911 / 15.850 | 170.99 / 21.58 / 23.381 / 24.862 | 0% |
| Q6_K | `20260905-164726-020f2f` | 55.36 / 55.36 / 9.233 / 9.308 | 82.01 / 41.02 / 12.445 / 12.667 | 130.10 / 32.58 / 15.771 / 16.368 | 157.37 / 19.87 / 25.600 / 26.603 | 0% |

Values are `aggregate throughput / per-request throughput / p50 latency / p95 latency`; throughput is tokens/s and latency is seconds. The original failed run IDs remain in the run index as provenance: `20260905-153342-4eaed8`, `20260905-154151-16d75d`, `20260905-155211-86727c`, and `20260905-160021-b40dc1`.

## Knowledge

| Model | Result | general | korea | math | science | logic |
|---|---:|---:|---:|---:|---:|---:|
| Q4_K_M UD | 14/25 (56%) | 60% | 40% | 80% | 20% | 80% |
| Q5_K_XL UD | 13/25 (52%) | 40% | 40% | 80% | 20% | 80% |
| Q5_K_M | 13/25 (52%) | 40% | 40% | 80% | 20% | 80% |
| Q6_K | 13/25 (52%) | 40% | 40% | 80% | 20% | 80% |

Dataset snapshot/hash is recorded in each result: `44883816f2b11f8560c69a6c28933c2496ea137a5b98860dd102d397349f650c`.

## Coding

| Model | Result | basic | string | collection | edge_case | failure types |
|---|---:|---:|---:|---:|---:|---|
| Q4_K_M UD | 10/12 (83.33%) | 100% | 100% | 66.67% | 66.67% | syntax_error 2 |
| Q5_K_XL UD | 9/12 (75%) | 100% | 100% | 33.33% | 66.67% | syntax_error 2, test_failure 1 |
| Q5_K_M | 9/12 (75%) | 100% | 66.67% | 66.67% | 66.67% | syntax_error 3 |
| Q6_K | 8/12 (66.67%) | 100% | 66.67% | 33.33% | 66.67% | syntax_error 4 |

Dataset hash: `53a283316be1ab63ee04c051d5194decbc3c7e27b76e5c177293bcab87dccbbd`.

## Tool-call

| Model | pass rate | selection | arguments | execution |
|---|---:|---:|---:|---:|
| Q4_K_M UD | 53.33% | 60% | 53.33% | 66.67% |
| Q5_K_XL UD | 46.67% | 60% | 46.67% | 60% |
| Q5_K_M | 46.67% | 53.33% | 46.67% | 60% |
| Q6_K | 53.33% | 66.67% | 53.33% | 66.67% |

Dataset hash: `8c0c1abefa2825c97341afaee620adbbf60cf43add20e0535c599872733065d5`. Per-run failure types and raw tool-call responses are retained under each run directory.

## Agent-single

| Model | pass rate | avg steps | avg tool calls | failures |
|---|---:|---:|---:|---|
| Q4_K_M UD | 25% | 3.08 | 2.08 | tool_error 5, missing_required_step 4 |
| Q5_K_XL UD | 41.67% | 3.33 | 2.33 | tool_error 4, missing_required_step 3 |
| Q5_K_M | 25% | 3.25 | 2.25 | tool_error 5, missing_required_step 4 |
| Q6_K | 16.67% | 3.08 | 2.08 | tool_error 4, missing_required_step 5, final_answer_error 1 |

Dataset hash: `188a63368a0631cc6cc6a80a8eed165f559f8131b5196ba28a951c428479b5d5`.

## Agent-multi

| Model | pass rate | handoff | role participation | avg steps | avg calls | failures |
|---|---:|---:|---:|---:|---:|---|
| Q4_K_M UD | 50% | 80% | 80% | 3.00 | 2.00 | missing_required_step 1, tool_error 3, missing_role 1 |
| Q5_K_XL UD | 60% | 90% | 90% | 3.00 | 2.00 | missing_required_step 2, missing_role 1, tool_error 1 |
| Q5_K_M | 70% | 80% | 80% | 2.70 | 1.70 | missing_required_step 1, missing_role 2 |
| Q6_K | 50% | 90% | 90% | 3.30 | 2.30 | missing_required_step 2, tool_error 2, missing_role 1 |

Dataset hash: `ee9bc5035f9ca17be36a3749e62322d767232570960ae80d3041b2b1741a010a`. Handoff and role metrics are ratios in `[0,1]` as defined by the v1 scorer.

## Validation and provenance

The run artifacts preserve the resolved recipe/config, environment, event stream, raw model responses/traces, and scoring summaries. The four failed server runs preserve their exact `llama-server.log` and failed events. No historical run artifact was overwritten. Regression results are recorded with the completion report/commit; the existing `test_api.py::test_health` environment hang, if reproduced by the full backend suite, is unrelated to this cycle.
