# Nex N2.5 Mini Full Benchmark v1

- Models: `Nex-N2.5-mini` Q4_K_M, Q5_K_M, Q6_K, Q8_0
- Hardware: NVIDIA DGX Spark GB10
- Runtime: all Server-performance runs **non-MTP** (`spec_type: none`, `spec: off`)
- Evaluator: Knowledge v1.2, Tool-call/Agent-single/Agent-multi v1.1
- Reasoning: OFF (`no-think`, budget 0)
- Cycle: `n25-mini-v1-full-20260910-174334-184806`
- All 28 runs completed; no failure or retry.

## Summary

| Variant | Knowledge | Coding | Tool-call | Agent-single | Agent-multi |
|---|---:|---:|---:|---:|---:|
| Q4_K_M | 93/100 | 11/12 | 10/15 | 8/12 | 9/10 |
| Q5_K_M | 94/100 | 11/12 | 12/15 | 7/12 | 10/10 |
| Q6_K | 95/100 | 11/12 | 12/15 | 8/12 | 10/10 |
| Q8_0 | 94/100 | 11/12 | 12/15 | 8/12 | 9/10 |

## Performance

Values are mean tokens/s from five repetitions.

| Variant | PP 512 | PP 2K | PP 8K | PP 32K | TG 512 |
|---|---:|---:|---:|---:|---:|
| Q4_K_M | 2127.23 | 2093.13 | 2018.27 | 1861.98 | 81.94 |
| Q5_K_M | 2051.63 | 2017.19 | 1933.98 | 1793.96 | 74.37 |
| Q6_K | 1807.14 | 1763.72 | 1699.86 | 1587.22 | 67.46 |
| Q8_0 | 1856.43 | 1810.47 | 1744.69 | 1619.87 | 44.16 |

Run IDs: Q4 `20260910-174334-9bb21b`, Q5 `20260910-175644-784a73`, Q6 `20260910-181038-5d1ff2`, Q8 `20260910-182659-76dd48`.

## Server-performance (non-MTP)

Aggregate generation throughput in tokens/s; failure rate was 0% for every condition.

| Variant | c1 | c2 | c4 | c8 |
|---|---:|---:|---:|---:|
| Q4_K_M | 76.18 | 110.76 | 144.97 | 164.90 |
| Q5_K_M | 70.50 | 108.56 | 151.14 | 165.45 |
| Q6_K | 64.03 | 88.57 | 117.57 | 142.41 |
| Q8_0 | 56.05 | 79.66 | 107.21 | 126.57 |

Server run IDs: Q4 `20260910-174650-2168e3`, Q5 `20260910-180010-0c4a09`, Q6 `20260910-181435-73c41c`, Q8 `20260910-183125-aa4903`.

## Evaluator details

| Variant | Knowledge run | Coding run | Tool-call run | Agent-single run | Agent-multi run |
|---|---|---|---|---|---|
| Q4_K_M | `20260910-175413-59ebd4` | `20260910-175443-2af329` | `20260910-175508-09d7a2` | `20260910-175533-8c63a3` | `20260910-175603-9863f9` |
| Q5_K_M | `20260910-180812-604dfb` | `20260910-180843-38eced` | `20260910-180908-45f26d` | `20260910-180933-4f2858` | `20260910-181003-fdfc40` |
| Q6_K | `20260910-182358-e5c565` | `20260910-182438-2abd83` | `20260910-182513-e7a954` | `20260910-182538-9ab661` | `20260910-182618-ba3d48` |
| Q8_0 | `20260910-184339-9b28e5` | `20260910-184450-350303` | `20260910-184555-1c6a43` | `20260910-184655-892cf8` | `20260910-184806-466376` |

Tool-call selection/argument/execution accuracy were respectively Q4 86.67/73.33/93.33%, and Q5/Q6/Q8 93.33/80/100%. Agent-multi handoff and role participation were Q4 90/90%, Q5/Q6 100/100%, Q8 90/90%.

## Evidence

Each run preserves `manifest.json`, `recipe.yaml`, `resolved-config.yaml`, `environment.json`, `result.json`, `events.jsonl`, raw response/trace, and suite-specific artifacts under `runs/<run-id>/`. Local cycle manifest: `runs/full-cycles/n25-mini-v1-full-20260910-174334-184806/manifest.json`.

The `mmproj-Nex-N2.5-mini-F16.gguf` file was not used; these benchmark suites are text-only. Historical runs were not modified.
