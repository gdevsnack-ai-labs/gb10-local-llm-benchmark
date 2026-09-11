# Qwen3.6 35B Full Benchmark v1

- Cycle ID: `qwen36-35b-v1-full-20260905-172506-182855`
- Window: `2026-09-05T08:25:06Z` – `2026-09-05T09:28:55Z`
- Platform commit: `61c9af1f0eacc9b828a7014ab2bb300a5546f79f`
- Total: 3 models × 7 suites = 21 runs

All runs completed without interruption. Existing recipes and scoring were used. Server-performance used MTP for the native MTP TURBO file and explicit no-MTP (`spec_type: none`, `spec: off`) for the two non-MTP files.

## Run index and evidence

Each run directory contains the resolved recipe/config, environment, events, and suite-specific result/raw evidence: [cycle manifest](../runs/full-cycles/qwen36-35b-v1-full-20260905-172506-182855/manifest.json).

| Model | performance | server-performance | knowledge | coding | tool-call | agent-single | agent-multi |
|---|---|---|---|---|---|---|---|
| NVFP4-MTP-TURBO | `20260905-172506-7319bf` | `20260905-172758-ece708` (MTP) | `20260905-173704-0371da` | `20260905-173719-61c62e` | `20260905-173908-c582e3` | `20260905-173949-a13e50` | `20260905-174038-6afc66` |
| Q8_0 | `20260905-174127-3d55c5` | `20260905-174519-9fe463` (non-MTP) | `20260905-175818-7cb152` | `20260905-175911-e3d9fa` | `20260905-180317-c9ab26` | `20260905-180504-35a184` | `20260905-180721-40d489` |
| Uncensored APEX-I Balanced | `20260905-180921-b11e6a` | `20260905-181248-c9a2b9` (non-MTP) | `20260905-182327-12e2cd` | `20260905-182343-4283d9` | `20260905-182635-5eea9f` | `20260905-182736-128e1f` | `20260905-182855-9c746f` |

## Performance

Tokens/s; PP = prompt processing, TG = text generation.

| Model | PP512 | PP2K | PP8K | PP32K | TG512 |
|---|---:|---:|---:|---:|---:|
| TURBO MTP | 2495.3 | 2476.2 | 2427.9 | 2241.2 | 77.2 |
| Q8_0 | 1941.3 | 1935.1 | 1894.9 | 1779.2 | 58.7 |
| APEX-I | 2002.3 | 1990.4 | 1952.3 | 1829.5 | 68.5 |

## Server-performance

Aggregate generation throughput in tokens/s; all failure rates were 0%.

| Model | mode | c=1 | c=2 | c=4 | c=8 |
|---|---|---:|---:|---:|---:|
| TURBO | MTP | 87.0 | 127.6 | 167.0 | 217.3 |
| Q8_0 | non-MTP | 55.1 | 80.9 | 119.7 | 182.6 |
| APEX-I | non-MTP | 64.4 | 98.5 | 152.5 | 195.3 |

Per-request throughput, p50/p95 latency, and raw request samples are in each server run's `result.json` and `samples.jsonl`.

## Evaluator suites

| Model | Knowledge | Coding | Tool-call | Agent-single | Agent-multi |
|---|---:|---:|---:|---:|---:|
| TURBO MTP | 13/25 (52%) | 11/12 (91.67%) | 12/15 (80%) | 7/12 (58.33%) | 3/10 (30%) |
| Q8_0 | 12/25 (48%) | 11/12 (91.67%) | 11/15 (73.33%) | 7/12 (58.33%) | 1/10 (10%) |
| APEX-I | 14/25 (56%) | 10/12 (83.33%) | 10/15 (66.67%) | 7/12 (58.33%) | 2/10 (20%) |

Agent-single averages (steps/tool calls): TURBO `3.08/2.08`, Q8_0 `3.00/2.00`, APEX-I `2.92/1.92`.

Agent-multi handoff/role participation: TURBO `60%/60%`, Q8_0 `50%/50%`, APEX-I `70%/70%`.

## Provenance

Raw results and traces are preserved under all 21 run directories. The MTP/non-MTP distinction applies only to server-performance runtime configuration; the other suites use their established recipes. No historical artifact was overwritten.
