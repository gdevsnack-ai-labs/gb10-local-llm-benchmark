# Ling 3.0 Flash Heretic MXFP4 Full Benchmark v1

- Model: `Ling-3.0-flash-heretic-MXFP4_MOE` (`bailingmoe3`, 124B.A5.1B MXFP4 MoE)
- Model files: 4-part GGUF (`00001-of-00004` through `00004-of-00004`)
- Reference environment: NVIDIA DGX Spark GB10, CUDA, llama.cpp `e107984bcffcfd701e82738092a2b000b6fda7a2`
- MTP: **present**. GGUF metadata contains `bailingmoe3.nextn_predict_layers = 1`.
- Server-performance: native MTP, `spec_type: mtp`, `spec_draft_n_max: 3`
- Evaluator reasoning: OFF (`thinking_mode: no-think`, `thinking_budget: 0`)
- Cycle: `ling30-flash-mxfp4-v1-full-20260907-183412-190139`
- Started: `2026-09-07T09:34:12.831711Z`
- Finished: `2026-09-07T10:03:46.326370Z`

## Results

### Performance

Run: `20260907-183412-cb965c`

| Metric | Mean |
|---|---:|
| PP 512 | 1009.34 tokens/s |
| PP 2K | 1022.02 tokens/s |
| PP 8K | 999.71 tokens/s |
| PP 32K | 882.04 tokens/s |
| TG 512 | 28.84 tokens/s |

Evidence: `runs/20260907-183412-cb965c/{manifest.json,resolved-config.yaml,result.json,environment.json}`

### Server-performance (native MTP)

Run: `20260907-184142-479c75` · 4 requests × 3 repetitions per concurrency · generation 512

| Concurrency | Aggregate tok/s | Per-request tok/s | p50 latency | p95 latency | Failure rate |
|---:|---:|---:|---:|---:|---:|
| 1 | 41.04 | 41.06 | 6.54 s | 6.71 s | 0% |
| 2 | 68.10 | 34.61 | 8.85 s | 9.33 s | 0% |
| 4 | 79.65 | 21.12 | 9.04 s | 14.84 s | 0% |
| 8 | 101.71 | 14.10 | 21.13 s | 35.30 s | 0% |

Evidence: `runs/20260907-184142-479c75/{manifest.json,resolved-config.yaml,result.json,environment.json,llama-server.log,events.jsonl}`. Runtime events recorded `speculative.types: none,draft-mtp`.

### Knowledge v1.2

Run: `20260907-185311-238e8f` · 99/100 · **99%**

| Category | Result |
|---|---:|
| General | 20/20 |
| Korea | 20/20 |
| Math | 19/20 |
| Science | 20/20 |
| Logic | 20/20 |

Dataset SHA256: `66e691da99a416fdf59887930d40c0dd7d12538b9f81b818e15e5bd0f6584079`

### Coding v1

Run: `20260907-185512-0edd5c` · 12/12 · **100%**

All categories passed: basic 3/3, string 3/3, collection 3/3, edge_case 3/3. Failure types: none.

### Tool-call v1.1

Run: `20260907-185748-bc7549` · 12/15 · **80%**

- Tool selection accuracy: 100%
- Argument accuracy: 86.67%
- Execution success rate: 93.33%
- Failure types: wrong arguments 2, execution error 1

### Agent-single v1.1

Run: `20260907-185938-e9c680` · 11/12 · **91.67%**

- Average steps: 3.58
- Average tool calls: 2.58
- Failure types: missing required step 1

### Agent-multi v1.1

Run: `20260907-190139-b1c4e0` · 8/10 · **80%**

- Handoff success rate: 0.80 (8/10)
- Role participation success rate: 0.80
- Average steps: 3.20
- Average tool calls: 2.20
- Failure types: missing role 2

## Full-cycle manifest

Machine-readable local manifest: `runs/full-cycles/ling30-flash-mxfp4-v1-full-20260907-183412-190139/manifest.json`.

The raw run directories, resolved configs, environment snapshots, events, server log, and suite-specific artifacts remain under `runs/`. No historical run artifact was overwritten.
