# North Mini Code 1.0 Full Benchmark v1

- Cycle ID: `north-mini-v1-full-20260905-183924-195711`
- 4 models × 7 suites = 28 runs
- Window: `2026-09-05T09:39:24Z` – `2026-09-05T10:57:11Z`
- Platform commit: `c440309`
- Runtime: all server-performance runs non-MTP (`spec_type: none`, `spec: off`)

## Run index

| Model | performance | server-performance | knowledge | coding | tool-call | agent-single | agent-multi |
|---|---|---|---|---|---|---|---|
| MXFP4_MOE | `20260905-183924-10553d` | `20260905-184209-003ab1` | `20260905-185057-318db7` | `20260905-185126-78fe5a` | `20260905-185303-ea2053` | `20260905-185401-8a0e03` | `20260905-185526-a6b909` |
| UD-Q4_K_M | `20260905-185701-b2d23b` | `20260905-185954-c24ba2` | `20260905-190823-140d05` | `20260905-190857-ccec3d` | `20260905-191039-94de35` | `20260905-191156-ea1a7d` | `20260905-191329-ce8d59` |
| UD-Q5_K_M | `20260905-191515-5b2b06` | `20260905-191832-4bd7c6` | `20260905-192752-53edd7` | `20260905-192841-b07e97` | `20260905-193033-247745` | `20260905-193158-342e65` | `20260905-193345-cd84bc` |
| UD-Q6_K_XL | `20260905-193540-0c3ce7` | `20260905-193918-79dcd0` | `20260905-194946-63547e` | `20260905-195043-f17e76` | `20260905-195301-12c124` | `20260905-195446-9a8b70` | `20260905-195711-74cf2f` |

Full machine-readable index: [cycle manifest](../runs/full-cycles/north-mini-v1-full-20260905-183924-195711/manifest.json). Each run directory preserves recipe, resolved config, environment, events, result, and raw suite evidence.

## Performance (tokens/s: PP512 / PP2K / PP8K / PP32K / TG512)

| Model | Results |
|---|---|
| MXFP4_MOE | 2675.9 / 2816.8 / 2783.1 / 2454.9 / 68.8 |
| UD-Q4_K_M | 2158.9 / 2607.7 / 2554.4 / 2299.1 / 71.7 |
| UD-Q5_K_M | 2050.5 / 2359.8 / 2341.1 / 2127.3 / 66.0 |
| UD-Q6_K_XL | 2066.4 / 2134.0 / 2124.5 / 1969.3 / 60.8 |

## Server-performance

Aggregate throughput tokens/s at concurrency 1/2/4/8; all failure rates were 0%.

| Model | c=1 | c=2 | c=4 | c=8 |
|---|---:|---:|---:|---:|
| MXFP4_MOE | 69.2 | 114.5 | 192.9 | 269.9 |
| UD-Q4_K_M | 68.5 | 115.7 | 194.8 | 299.8 |
| UD-Q5_K_M | 63.4 | 105.9 | 177.7 | 272.3 |
| UD-Q6_K_XL | 58.3 | 98.1 | 154.2 | 250.7 |

Per-request throughput, p50/p95 latency, and request samples are in each server run's `result.json`/`samples.jsonl`.

## Evaluator results

| Model | Knowledge | Coding | Tool-call | Agent-single | Agent-multi |
|---|---:|---:|---:|---:|---:|
| MXFP4_MOE | 5/25 (20%) | 11/12 (91.67%) | 11/15 (73.33%) | 7/12 (58.33%) | 5/10 (50%) |
| UD-Q4_K_M | 8/25 (32%) | 12/12 (100%) | 11/15 (73.33%) | 6/12 (50%) | 4/10 (40%) |
| UD-Q5_K_M | 8/25 (32%) | 11/12 (91.67%) | 11/15 (73.33%) | 8/12 (66.67%) | 6/10 (60%) |
| UD-Q6_K_XL | 6/25 (24%) | 11/12 (91.67%) | 11/15 (73.33%) | 4/12 (33.33%) | 3/10 (30%) |

Agent-single average steps/tool calls: MXFP4 `3.17/2.17`, Q4 `3.25/2.25`, Q5 `3.17/2.17`, Q6 `3.58/2.58`. Agent-multi handoff/role participation: MXFP4 `100%/100%`, Q4 `90%/90%`, Q5 `90%/90%`, Q6 `90%/90%`.

No historical artifacts were overwritten; all raw evidence remains under `runs/<run-id>/`.
