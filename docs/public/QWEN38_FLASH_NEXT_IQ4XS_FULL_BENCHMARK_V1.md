# Qwen3.8 Flash Next UD-IQ4_XS Full Benchmark v1

- Cycle ID: `qwen38-flash-next-iq4xs-v1-full-20260905-223427-233252`
- Model: `Qwen3.8-Flash-Next-UD-IQ4_XS` multipart (3 shards, ~88GB)
- Window: `2026-09-05T13:34:27Z` – `2026-09-05T14:32:52Z`
- Platform commit: `5045e2f`
- Runtime: non-MTP (`spec_type: none`, `spec: off`)

## Runs and evidence

| Suite | Run ID | Status |
|---|---|---|
| performance | `20260905-223427-189e4d` | completed |
| server-performance | `20260905-225405-d84cc2` | completed |
| knowledge | `20260905-231907-d642b1` | completed |
| coding | `20260905-232058-c7aa39` | completed |
| tool-call | `20260905-232616-89f863` | completed |
| agent-single | `20260905-232905-7eaa17` | completed |
| agent-multi | `20260905-233252-2e154c` | completed |

All run directories preserve `manifest.json`, `recipe.yaml`, `resolved-config.yaml`, `environment.json`, `events.jsonl`, suite result, and raw evidence. See the [cycle manifest](../runs/full-cycles/qwen38-flash-next-iq4xs-v1-full-20260905-223427-233252/manifest.json).

## Results

Performance tokens/s (PP512 / PP2K / PP8K / PP32K / TG512): **215.1 / 235.2 / 233.8 / 280.1 / 25.8**.

Server-performance aggregate throughput tokens/s at concurrency 1/2/4/8: **26.8 / 42.4 / 63.5 / 93.7**. Per-request throughput: **26.8 / 21.2 / 15.9 / 11.7**. p50 latency seconds: **18.90 / 24.27 / 32.34 / 43.72**. Failure rate: **0%** at every concurrency.

| Suite | Result |
|---|---:|
| Knowledge | 3/25 (12%) |
| Coding | 10/12 (83.33%), syntax_error 2 |
| Tool-call | 11/15 (73.33%); selection 80%, arguments 73.33%, execution 86.67% |
| Agent-single | 4/12 (33.33%); avg 3.58 steps, 2.58 tool calls |
| Agent-multi | 3/10 (30%); handoff 100%, role participation 100%, avg 4.30 steps, 3.30 tool calls |

Agent-single failures: tool_error 4, missing_required_step 3, repeated_loop 1. Agent-multi failures: tool_error 7. The three shards were successfully loaded as one multipart model; no run failed or was interrupted.
