# GB10 Local LLM Benchmark Platform — Full Design Specification

**Document status:** Architecture intent reconciled with Phase 8 implementation (2026-09-04)
**Target host:** NVIDIA DGX Spark / GB10, 128 GB unified memory, Ubuntu ARM64  
**Primary inference backend:** llama.cpp only  
**Excluded from initial architecture:** vLLM and other persistent inference backends  
**Primary clients:** Web UI, CLI, REST API  
**Primary purpose:** reproducible local-LLM performance, quality, coding, tool-use, agent and real-workload evaluation with preserved evidence and artifacts.

---

## 1. Executive Summary

This project is not a conventional leaderboard and not merely a tokens-per-second dashboard. It is a local-first experiment platform that answers a practical question:

> On this GB10 machine, under a known llama.cpp build and a reproducible configuration, how fast and how well can a model perform an actual workload, and what evidence was produced?

The platform combines six categories of evidence:

1. **Inference performance:** prompt processing/prefill, decode, latency, concurrency, memory/resource telemetry.
2. **Capability evaluation:** general knowledge, mathematics, science, reasoning and selected standard/custom datasets.
3. **Coding evaluation:** isolated coding problems and repository-level tasks, with tests and complete generated artifacts preserved.
4. **Tool-call evaluation:** correct tool selection, schema/argument validity, execution success, recovery and multi-step behavior.
5. **Agent evaluation:** single-agent and multi-agent execution, including complete traces, tool usage, retries, token use and final task success.
6. **Real workloads:** DevOps, research, content, data processing and other practical jobs relevant to the operator's actual local-AI usage.

The **Web UI is a first-class control client**, not a passive dashboard. It launches runs, watches them live, stops/cancels jobs, compares results and inspects artifacts. CLI and REST use the exact same backend core so there is only one benchmark truth.

The design deliberately standardizes on **llama.cpp** for Phase 0–Phase 7. This avoids cross-backend memory behavior and scheduling differences while making GB10 measurements easier to interpret. The platform consumes llama.cpp capabilities rather than reimplementing them: `llama-bench` for controlled prompt-processing and generation microbenchmarks; `llama-server` for OpenAI-compatible serving, parallel decoding, continuous batching, slots and server metrics; and direct llama-server completion timing data for request-level performance measurements.

---

## 2. Product Definition

### 2.1 Working name

`GB10 LLM Bench` is used in the skeleton. The name should remain replaceable. Suggested public-facing classes include “Local LLM Workbench”, “DevSnack LLM Lab”, or a project-specific title.

### 2.2 Product goals

The platform SHALL:

- launch all supported benchmark types from a web browser;
- launch the same benchmark types through CLI and REST API;
- use a shared benchmark core and shared result schema;
- record enough environment/configuration information to reproduce a run;
- separate microbenchmark performance from end-to-end serving performance;
- measure single-request and concurrent-request behavior;
- preserve raw outputs rather than only aggregate scores;
- preserve complete coding artifacts and repository diffs;
- preserve tool and agent traces;
- support custom benchmark recipes;
- make repeated model/quant/config comparison easy;
- generate structured data suitable for DevSnack articles and Lab pages;
- operate locally with no dependency on a commercial cloud benchmark service.

### 2.3 Explicit non-goals for initial releases

The initial platform SHALL NOT:

- support vLLM;
- attempt to become a universal inference-server abstraction layer;
- create one universal “model score” that hides dimension-specific behavior;
- run arbitrary untrusted code on the host without sandbox boundaries;
- automatically publish results to the public site;
- provide distributed multi-node benchmarking;
- optimize llama.cpp itself;
- replace mature benchmark suites where an adapter can be used.

---

## 3. Design Principles

### 3.1 One backend, multiple clients

The Web UI, CLI, external automation and future agent integrations all call the same control plane.

```text
Web UI ──────┐
CLI ─────────┼──> Benchmark API / Core ──> Runner ──> llama.cpp / sandbox
Agent/API ───┘                    │
                                 ├── DB
                                 ├── Event stream
                                 └── Artifact store
```

No benchmark logic should live exclusively inside the browser.

### 3.2 Raw evidence is a first-class product

A run is not merely a score. A run contains:

- manifest;
- normalized metrics;
- raw engine output;
- stdout/stderr;
- prompts and model responses where licensing/privacy allows;
- tool calls;
- agent trace;
- generated source tree;
- patch/diff;
- test output;
- system telemetry;
- evaluator version;
- benchmark dataset version.

### 3.3 Reproducibility over convenience

Every result must identify at minimum:

- model file identity/path and preferably checksum;
- GGUF metadata where available;
- quantization;
- llama.cpp build commit/build number;
- benchmark platform version/git commit;
- command-line inference flags;
- context size;
- batch and micro-batch size;
- GPU offload settings;
- flash-attention setting;
- seed and sampling settings;
- prompt/dataset/recipe version;
- concurrency and server slot count;
- cache policy;
- hardware/OS snapshot;
- timestamp.

### 3.4 Do not mix incomparable metrics

The platform must visibly separate:

- `llama-bench` prompt processing rate from HTTP request throughput;
- decode tokens/s per request from aggregate tokens/s;
- cold-run and warm-run measurements;
- prefix-cache enabled and disabled results;
- single-user latency and saturated throughput;
- quality score and speed score;
- base model result and quantized model result.

### 3.5 Version everything that changes meaning

Recipes, datasets, scorers, agent harnesses and workload definitions carry versions. A `coding-basic-v1` result must remain interpretable after `coding-basic-v2` exists.

---

## 4. llama.cpp Integration Strategy

### 4.1 Why llama.cpp is the only Phase-0 inference backend

For this project the backend is intentionally constrained. GB10 unified-memory behavior, quantization choices and model residency already introduce enough experimental variables. Adding vLLM would introduce allocator, batching, KV-cache and model-loading behavior that can make comparisons harder to interpret. Backend expansion can be revisited only after the llama.cpp methodology becomes stable.

### 4.2 Components to use

#### llama-bench

Use for controlled inference microbenchmarks:

- prompt processing (`pp`);
- text generation (`tg`);
- prompt + generation (`pg`);
- batch and micro-batch sweeps;
- context depth experiments;
- GPU layer/offload experiments;
- repetitions and standard deviation;
- machine-readable JSON/JSONL output.

Important methodological note: llama-bench timing does not include tokenization and sampling time, so its numbers must be labeled as engine microbenchmark numbers, not user-observed request latency.

#### llama-server

Use for serving and workload benchmarks:

- `/v1/chat/completions` for compatibility-based workloads;
- `/completion` when llama.cpp-specific timings are required;
- parallel requests via `--parallel`/`-np`;
- continuous batching;
- `/slots` for per-slot state and live visibility;
- `/metrics` for Prometheus-compatible server metrics when enabled;
- `/health` for lifecycle control;
- tool/function calling for tool evaluation;
- future multimodal suites if required.

### 4.3 Process ownership modes

The platform should support two server ownership modes.

**External server mode:** operator starts llama-server independently and supplies URL. Best for early development and debugging.

**Managed server mode:** benchmark platform launches llama-server with a model preset, waits for `/health`, runs the test, captures logs, then terminates or reuses it according to policy. This is the desired long-term default for reproducible batch testing.

Managed mode is implemented for model-dependent server/evaluator runs. It starts llama-server, waits for health, captures the log, and stops it unless reuse is explicitly requested.

### 4.4 Model lifecycle policy on GB10

For sequential multi-model benchmark queues:

1. verify no active model-dependent run;
2. stop existing managed llama-server;
3. optionally drop/release caches according to recipe policy;
4. record pre-load memory snapshot;
5. launch requested model configuration;
6. wait until health is ready;
7. run an explicit warmup if required;
8. execute benchmark;
9. capture post-run telemetry;
10. terminate or retain server according to the next queued compatible job.

Never silently reuse a warm server when the recipe requests a cold run.

---

## 5. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                         WEB UI                              │
│ Launcher | Queue | Live Monitor | Results | Compare | Files│
└───────────────────────────┬─────────────────────────────────┘
                            │ REST + SSE/WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│                    BENCHMARK CONTROL PLANE                  │
│ API | Auth(local) | Recipe Resolver | Run Manager | Queue   │
└────────────┬─────────────────────┬───────────────────────────┘
             │                     │
        ┌────▼────┐          ┌────▼────────┐
        │ Runners │          │ Event Bus   │
        └────┬────┘          └────┬────────┘
             │                     │
   ┌─────────┼──────────┐          │
   │         │          │          │
┌──▼───┐ ┌──▼────┐ ┌───▼──────┐  │
│Perf  │ │Coding │ │Agent/Tool│  │
└──┬───┘ └──┬────┘ └───┬──────┘  │
   │        │            │         │
   ▼        ▼            ▼         │
llama.cpp Sandbox     llama-server  │
   │        │            │         │
   └────────┴─────┬──────┘         │
                  ▼                ▼
            Result Normalizer   Live UI
                  │
          ┌───────┴────────┐
          ▼                ▼
       SQLite          Artifact FS
```

### 5.1 Recommended technology stack

**Backend:** Python 3.12+, FastAPI, Pydantic, asyncio, httpx, SQLite initially.  
**CLI:** Typer using REST API by default; optional direct-core mode later.  
**Frontend:** React + TypeScript + Vite.  
**Live events:** SSE first; WebSocket only when bidirectional live control becomes necessary.  
**Artifacts:** filesystem, indexed by DB.  
**Charts:** frontend chart library selected during UI implementation.  
**System telemetry:** psutil + NVIDIA tooling accessible on GB10; design an interface so telemetry source can be replaced.  
**Sandbox:** container/process abstraction; Docker/Podman compatibility evaluated on ARM64, with process sandbox only for trusted internal fixtures.

---

## 6. Core Domain Model

### 6.1 Model

Represents a logical local model and its files/configurations.

Suggested fields:

- `model_id`
- `display_name`
- `family`
- `parameter_count`
- `architecture`
- `source_repo`
- `license`
- `notes`

### 6.2 Model Variant

A concrete GGUF artifact/configuration.

- `variant_id`
- `model_id`
- `gguf_path`
- `file_size`
- `sha256`
- `quantization`
- `gguf_metadata_json`
- `default_chat_template`

### 6.3 Backend Preset

llama.cpp launch parameters independent from the model identity.

- context size;
- batch size;
- ubatch size;
- GPU layers;
- flash attention;
- KV type;
- threads;
- parallel slots;
- mmap/direct IO options;
- speculative configuration if later supported.

### 6.4 Benchmark Suite

A versioned evaluator definition, e.g.:

- performance-v1;
- server-throughput-v1;
- coding-basic-v1;
- tool-call-v1;
- agent-single-devops-v1;
- agent-multi-devops-v1;
- knowledge-core-v1.

### 6.5 Recipe

A reusable set of parameters binding a model/backend-independent suite configuration.

Example:

```yaml
name: GB10 Standard Performance v1
suite: performance
version: 1
config:
  prompt_tokens: [512, 2048, 8192, 32768]
  gen_tokens: [128, 512]
  repetitions: 5
  flash_attn: true
  n_gpu_layers: 99
```

### 6.6 Run

An immutable experiment instance after completion.

Run state machine:

```text
QUEUED -> PREPARING -> RUNNING -> EVALUATING -> FINALIZING -> COMPLETED
                      |              |              |
                      +--------------+--------------+-> FAILED

QUEUED/RUNNING -> CANCELLING -> CANCELLED
```

The current implementation uses `queued/running/completed/failed/cancelled`. The richer preparing/evaluating/finalizing state machine remains design intent and is not claimed as implemented.

### 6.7 Artifact

A file or directory produced by a run:

- generated repository;
- patch;
- source archive;
- test logs;
- prompt transcript;
- trace JSONL;
- metrics raw JSON;
- report HTML/Markdown;
- screenshots if a future workload requires them.

---

## 7. Storage Design

### 7.1 SQLite role

SQLite stores normalized, queryable metadata and metrics. It does not store large repositories or logs.

Recommended tables after Phase 1:

```text
models
model_variants
backend_presets
benchmark_suites
recipes
runs
run_metrics
run_samples
artifacts
agent_steps
tool_calls
evaluations
tags
```

The active event store is the per-run `events.jsonl` file; `run_events` is intentionally omitted from the current SQLite schema.

### 7.2 Artifact filesystem

```text
runs/
  20260903-220501-a1b2c3/
    manifest.json
    recipe.yaml
    resolved-config.yaml
    environment.json
    result.json
    metrics.jsonl
    events.jsonl
    stdout.log
    stderr.log
    prompts/
    responses/
    traces/
      agent.jsonl
      tools.jsonl
    artifacts/
      repository/
      patch.diff
      tests.xml
      report.md
```

### 7.3 Immutable run policy

Once a run reaches `COMPLETED`, its raw evidence must not be overwritten. Derived annotations may be appended separately. If a scorer changes, create a re-evaluation record pointing to the original run rather than rewriting the run.

---

## 8. Performance Benchmark Design

### 8.1 Microbenchmark — llama-bench

Required default measurements:

- PP 512;
- PP 2K;
- PP 8K;
- PP 32K where context/model allows;
- TG 128;
- TG 512;
- repetitions >= 3 for smoke, >= 5 for published benchmark;
- average and standard deviation;
- exact llama.cpp build metadata.

Optional sweeps:

- batch size;
- ubatch size;
- context depth;
- flash attention on/off;
- quantization comparisons;
- KV-cache type;
- CPU thread count;
- mmap/direct IO.

### 8.2 End-to-end server benchmark

Measure separately:

- request wall latency;
- prompt tokens;
- generated tokens;
- llama.cpp prompt timing;
- llama.cpp predicted timing;
- prompt tokens/s;
- per-request decode tokens/s;
- aggregate generated tokens/s;
- request completion rate;
- error rate;
- P50/P95/P99 latency;
- concurrency;
- slot count;
- queue/wait behavior if derivable;
- total run time.

### 8.3 Concurrency matrix

Default published recipe should use a controlled matrix such as:

```text
Concurrency: 1, 2, 4, 8
Requests per level: max(8, concurrency * 4)
Fixed prompt-size class: short / medium / long
Fixed generation target
```

The benchmark must distinguish:

- **aggregate throughput**: all generated tokens / wall time;
- **per-user throughput**: distribution of per-request decode speed;
- **latency degradation**: P50/P95 versus concurrency;
- **saturation point**: concurrency after which throughput gain is small while latency grows sharply.

### 8.4 Cold vs warm and cache policy

Each performance recipe declares:

```yaml
cache_policy: cold | warm | prefix-reuse
warmup: true | false
```

Published charts must never combine these categories without labels.

### 8.5 Live telemetry

Minimum live telemetry:

- current phase;
- completed samples / total samples;
- current prompt/generated token counts where available;
- current/rolling prompt t/s;
- current/rolling decode t/s;
- current memory use;
- process/system CPU;
- GPU utilization if source available;
- power if source available;
- active llama-server slots;
- elapsed time.

Persist telemetry at a moderate sampling cadence (e.g. 1 second) to avoid creating measurement overhead. The telemetry collector itself should have an overhead test.

---

## 9. Knowledge, Reasoning, Math and Science Evaluation

### 9.1 Adapter model

Do not build a new academic-eval ecosystem. Define a runner adapter interface so established harnesses or local datasets can feed normalized results into this platform.

Candidate suites may include MMLU-style, GSM/math, science QA and Korean custom tests. Exact upstream datasets must be reviewed for licensing and contamination concerns before public redistribution.

### 9.2 Required result representation

For each sample:

- sample ID;
- dataset version;
- prompt rendered to the model;
- raw model output;
- parsed answer;
- correct answer where redistributable;
- score;
- parsing/evaluator reason;
- latency/token metrics;
- evaluator version.

### 9.3 Do not over-aggregate

Keep separate domain scores for:

- general knowledge;
- Korean knowledge;
- math;
- science;
- reasoning;
- instruction following.

A composite score may be provided later as an optional view, never as the canonical data.

---

## 10. Coding Benchmark Design

Coding is split into two fundamentally different modes.

### 10.1 Mode A — isolated programming problems

Input contains a bounded problem and test contract. The model generates a function/program. The evaluator runs hidden/public tests inside a sandbox.

Metrics:

- compile success;
- test pass rate;
- exact pass/fail;
- time;
- generation tokens;
- retries if agentic;
- code size;
- optional lint/static quality.

### 10.2 Mode B — repository task

Input is a repository snapshot plus a task/issue. The model or agent may inspect files, edit files and run allowed commands.

Every run preserves the final workspace.

Required artifacts:

```text
artifacts/repository/
artifacts/patch.diff
artifacts/test-output.log
artifacts/changed-files.json
traces/agent.jsonl
```

### 10.3 Repository fixtures

Create internal, license-clean benchmark fixtures first rather than immediately importing large public suites. Each fixture should have:

- immutable base commit/archive;
- task description;
- allowed operations;
- build command;
- test command;
- hidden evaluator tests if applicable;
- time/step/token limit;
- expected behavioral outcomes;
- version.

Suggested task classes:

- bug fix;
- feature addition;
- refactor with behavior preserved;
- test generation;
- API integration;
- log/debug diagnosis;
- configuration repair.

### 10.4 Coding scoring

Prefer objective gates:

```text
Build/parse       0/1
Required tests    0..1
Regression tests  0..1
Task-specific     0..1
```

Style can be separately scored but must not dominate functional correctness.

### 10.5 Artifact browser

The UI should provide:

- tree view;
- file viewer;
- unified diff;
- test report;
- build log;
- final README/report;
- downloadable run archive;
- side-by-side artifact comparison between two runs.

---

## 11. Tool-Call Benchmark Design

### 11.1 Layers

**Syntax:** Did the model emit parseable structured tool data?  
**Selection:** Did it choose the correct tool?  
**Arguments:** Are parameters correct and complete?  
**Execution:** Did the tool call succeed?  
**Interpretation:** Did the model use the tool result correctly?  
**Recovery:** Can it repair malformed/failed calls?  
**Sequence:** Does it call multiple tools in the correct dependency order?  
**Restraint:** Can it avoid unnecessary or irrelevant tool use?

### 11.2 Native tool simulator

For reproducibility, implement deterministic benchmark tools such as:

- calculator;
- key/value lookup;
- file read/write within a temporary fixture;
- fake weather/data API with known responses;
- structured database query;
- mock issue tracker.

No internet dependency is required for the core tool benchmark.

### 11.3 Metrics

- JSON/schema valid rate;
- correct-tool rate;
- exact-argument rate;
- execution success rate;
- unnecessary-call rate;
- hallucinated-tool rate;
- recovery success rate;
- average calls per task;
- task success rate;
- input/output tokens.

---

## 12. Single-Agent Benchmark

### 12.1 Native harness first

Avoid coupling the platform's identity to one external agent framework. Build a small native agent-loop interface first:

```text
Task -> Model -> Tool call -> Observation -> Model -> ... -> Final
```

External frameworks can be adapters later.

### 12.2 Agent trace format

JSONL per step:

```json
{"step": 3, "type": "tool_call", "tool": "read_file", "args": {"path": "src/a.py"}, "started_at": "..."}
{"step": 3, "type": "tool_result", "ok": true, "duration_ms": 18, "summary": "..."}
```

Do not rely on hidden chain-of-thought. Store observable messages, tool calls, outputs, state transitions and evaluator evidence only.

### 12.3 Metrics

- final success;
- steps;
- LLM calls;
- tool calls;
- failed tool calls;
- repeated actions;
- elapsed time;
- input/output tokens;
- context growth;
- tests passed;
- files changed;
- recovery count.

---

## 13. Multi-Agent Benchmark

### 13.1 Purpose

The core question is not “is multi-agent interesting?” but:

> Does a multi-agent organization improve task success enough to justify added tokens, latency and coordination overhead?

### 13.2 Baseline topology

Start with one fixed topology:

```text
Manager
├── Coder
├── Tester
└── Reviewer
```

Do not introduce arbitrary swarms in v1.

### 13.3 Fair comparison requirements

Single and multi-agent tests use:

- same base model variant;
- same repository/task;
- same total wall-time ceiling;
- separately reported token budget;
- same tool permissions;
- same final evaluator;
- repeated seeds/runs where stochasticity matters.

### 13.4 Coordination metrics

- total model calls;
- messages exchanged;
- duplicated file reads;
- duplicated tool work;
- conflicting edits;
- review changes accepted/rejected;
- total tokens;
- task success;
- time to first valid solution;
- final quality delta versus single-agent baseline.

---

## 14. Real Workload Benchmark

These are the most valuable DevSnack-specific suites because they answer operational questions that public leaderboards do not.

Suggested categories:

### DevOps

- diagnose a supplied service log;
- repair a broken config;
- inspect a small repository and propose a verified fix;
- write/test a deployment script in a sandbox.

### Research

- summarize a fixed evidence package;
- extract claims with citations to supplied documents;
- resolve contradictions;
- produce a structured report.

### Content

- deduplicate a fixed set of article candidates;
- rank by relevance;
- produce an article draft with traceable sources;
- evaluate factual consistency against the package.

### Data

- inspect CSV/JSON;
- calculate specified statistics;
- produce a report;
- validate exact expected outputs.

All workload inputs must be frozen and versioned for comparisons.

---

## 15. Web UI Specification

### 15.1 Global navigation

```text
Dashboard
Launcher
Queue
Runs
Models
Benchmarks
Compare
Artifacts
System
Settings
```

### 15.2 Dashboard

Show:

- active run card;
- queue length;
- server/model state;
- recent runs;
- recent failures;
- key performance leaders by comparable recipe;
- hardware snapshot.

Do not show cross-suite leaderboards without recipe filters.

### 15.3 Launcher

Fields depend on suite.

Common fields:

- model variant;
- benchmark suite;
- recipe;
- repetitions;
- seed;
- tags/notes;
- artifact retention policy.

Performance fields:

- PP lengths;
- TG lengths;
- context;
- batch/ubatch;
- flash attention;
- cold/warm/cache policy;
- concurrency matrix;
- request count.

Coding/agent fields:

- task set;
- max time;
- max steps;
- allowed tools;
- sandbox;
- save full repository.

Launcher buttons:

- Run now;
- Add to queue;
- Dry-run/validate recipe;
- Save recipe.

### 15.4 Live Monitor

Performance view:

- phase and progress;
- active sample;
- PP/TG rates;
- aggregate throughput;
- latency;
- GPU/system telemetry;
- active slots;
- rolling chart.

Agent view:

- current role/agent;
- observable message/event stream;
- tool calls and outcomes;
- files changed;
- tests run;
- token counters;
- elapsed time;
- task status.

Controls:

- Cancel;
- soft stop after current sample;
- open raw log.

### 15.5 Run Detail

Tabs:

```text
Summary | Metrics | Samples | Prompt/Output | Trace | Tools | Files | Diff | Tests | Logs | Environment
```

Tabs appear only when applicable.

### 15.6 Compare

Users select compatible runs. Compatibility rules are displayed.

Comparison views:

- metric table;
- performance curves;
- concurrency curves;
- quality domain bars;
- tokens/time versus success;
- artifact diff;
- agent-step comparison.

### 15.7 Publication/export

A later phase should support export of:

- JSON bundle;
- CSV metrics;
- Markdown report;
- static chart images;
- public-safe artifact package;
- DevSnack Lab data block.

Publication remains a manual action.

---

## 16. REST API Draft

```text
GET    /api/health
GET    /api/system
GET    /api/models
POST   /api/models/scan
GET    /api/recipes
POST   /api/recipes/validate
GET    /api/runs
POST   /api/runs
GET    /api/runs/{id}
POST   /api/runs/{id}/cancel
GET    /api/runs/{id}/events
GET    /api/runs/{id}/metrics
GET    /api/runs/{id}/artifacts
GET    /api/artifacts/{id}
POST   /api/compare
GET    /api/queue
POST   /api/queue/reorder
```

The current implementation exposes health/system/recipes/models/presets/queue/server status, run lifecycle, metrics, environment, artifacts, persisted JSONL event history, compare, and export/methodology endpoints. Recipe and run provenance artifacts are stored under each run directory.

---

## 17. CLI Draft

```bash
llmbench health
llmbench models scan /models
llmbench recipes
llmbench run performance --recipe performance-standard-v1 --model qwen.gguf
llmbench run server-performance --recipe concurrency-v1
llmbench run coding --recipe coding-basic-v1 --model qwen.gguf
llmbench queue list
llmbench run show RUN_ID
llmbench export RUN_ID --format markdown
```

CLI should call REST by default so results are visible in the same UI and DB.

---

## 18. Event Model

SSE is sufficient initially because live traffic is server-to-browser.

Standard event types:

```text
status
phase
progress
metric
telemetry
model_output
tool_call
tool_result
artifact
test_result
warning
error
```

Every persistent event has:

- run ID;
- timestamp;
- sequence number;
- event type;
- payload.

The EventBus persists the authoritative event stream to `runs/<id>/events.jsonl` and replays it for page reloads/SSE subscribers. SQLite does not maintain a second event copy.

---

## 19. Metrics Naming Standard

Avoid ambiguous names such as `speed`.

Recommended examples:

```text
perf.prompt_tokens
perf.prompt_ms
perf.prompt_tps
perf.generated_tokens
perf.decode_ms
perf.decode_tps
perf.aggregate_decode_tps
perf.request_latency_ms
perf.ttft_ms
perf.itl_ms
system.memory_used_bytes
system.gpu_utilization_pct
system.power_w
agent.llm_calls
agent.tool_calls
agent.failed_tool_calls
agent.steps
quality.pass_rate
coding.tests_passed
coding.tests_total
```

Each metric record includes unit, aggregation and provenance.

---

## 20. Environment Capture

Create `environment.json` before every publishable run.

Capture:

- OS/kernel;
- architecture;
- CPU;
- total memory;
- NVIDIA/driver information available on GB10;
- CUDA-visible environment;
- llama.cpp binary path;
- `llama-bench` build metadata;
- `llama-server` build metadata;
- platform git commit;
- model file stat/checksum;
- process environment allowlist;
- thermal/power policy if detectable.

Do not capture secrets or arbitrary environment variables.

---

## 21. Benchmark Integrity Controls

### 21.1 Warmup discipline

Warmup behavior is explicit and recorded.

### 21.2 Repeat discipline

Performance publication: >= 5 repetitions recommended. Quality/agent publication: repeated runs only where stochasticity or agent path variance matters, with raw run distribution visible.

### 21.3 Failure is data

Do not silently retry and keep only the successful run. Store the failed attempt. A retry produces a linked attempt record.

### 21.4 Timeout discipline

Every coding/tool/agent task defines max wall time and max steps. Timeout must produce a distinct evaluator result, not a generic crash.

### 21.5 Benchmark contamination

For public benchmark datasets record dataset release/version and model knowledge-cutoff/known contamination caveats where possible. Real-workload internal fixtures are preferable when the experiment aims to measure practical behavior rather than compare against public leaderboard scores.

---

## 22. Security and Sandbox

Coding and agent suites can execute model-generated commands. Treat model output as untrusted.

Requirements before broad coding tests:

- per-run isolated workspace;
- command allow/deny policy;
- network disabled by default;
- CPU/memory/time limits;
- no access to home SSH keys, tokens or unrelated repositories;
- explicit mount allowlist;
- artifact copy-out after evaluator completes;
- cleanup strategy.

Coding currently provides per-sample workspace isolation, subprocess execution, and a timeout. It does not provide a hardened sandbox, network namespace, container boundary, resource cgroup, or broad untrusted-code protection.

---

## 23. Queue and Scheduling

GB10 is a single primary benchmark host. Most heavyweight model runs should serialize by default.

Queue record fields:

- run ID;
- priority;
- requested model variant;
- server preset;
- resource class;
- submitted time;
- dependency run IDs.

Optimization allowed later: adjacent queued runs with identical model/server preset may reuse the loaded model **only when the recipes permit warm reuse**. The scheduler must never change a cold-run experiment into a warm-run experiment for efficiency.

---

## 24. Model Registry and Auto-Discovery

A model scanner should later crawl configured GGUF directories and create candidate variants.

For each file:

- path;
- size;
- checksum (optionally lazy);
- GGUF metadata;
- quantization;
- inferred family/name;
- tags;
- last benchmark time.

The operator approves display names rather than relying permanently on filename parsing.

---

## 25. Benchmark Profiles Instead of One Rank

The UI should produce a profile such as:

```text
Performance
  Prefill
  Decode
  Concurrency
  Long context
Capability
  Knowledge
  Math
  Science
  Reasoning
Coding
  Isolated
  Repository
Tool Use
Agent
  Single
  Multi
Workload
  DevOps
  Research
  Content
```

Users may create their own weighted view, but canonical storage remains per-dimension.

---

## 26. DevSnack Content Integration

The benchmark platform should make content extraction easy without coupling the runtime to the blog.

A public experiment package can include:

```text
publication/
  summary.json
  tables.csv
  charts/
  methodology.md
  environment.md
  selected-artifacts/
```

This supports articles such as:

- Q6 vs Q8: measurable quality/speed tradeoff;
- dense 27B vs MoE local models;
- how GB10 serving changes from concurrency 1 to 8;
- whether multi-agent pays for its token overhead;
- model A vs B on the same repository repair tasks;
- thinking configuration versus coding success;
- context-size effects on performance.

The article should link to methodology/run IDs so the published claim is traceable to evidence.

---

## 27. Implementation Phases

### Phase 0 — Foundation

Deliverables:

- repository structure;
- FastAPI service;
- SQLite run table;
- runner interface;
- recipe loader;
- CLI;
- React starter UI;
- SSE events;
- artifact directory contract.

Exit gate:

- a dummy or llama-bench smoke run can be launched through API and appears in UI;
- CLI-created run appears in same DB/UI;
- run manifest and result files exist.

### Phase 1 — Performance Lab

Deliverables:

- robust llama-bench parser;
- managed/external llama-server profiles;
- server concurrency runner;
- `/slots` monitor;
- `/metrics` collector;
- GB10 hardware telemetry;
- cold/warm/cache modes;
- charts and compare UI;
- environment capture.

Exit gate:

- same GGUF can be repeatedly measured with stable run metadata;
- PP/TG results and concurrency curves are visible and exportable;
- failed runs leave complete diagnostics.

### Phase 2 — Model Registry and Queue

Deliverables:

- GGUF scan;
- model variants;
- presets;
- persistent queue;
- managed model lifecycle;
- multi-model sequential batch execution.

Exit gate:

- operator can select four model variants in Web UI and enqueue the same recipe;
- platform safely loads/runs/unloads them sequentially.

### Phase 3 — Knowledge/Reasoning

Deliverables:

- external harness adapter contract;
- initial standard suites;
- custom Korean/local suite structure;
- sample-level result browser.

### Phase 4 — Coding

Deliverables:

- sandbox runner;
- internal fixture format;
- isolated code suite;
- repository suite;
- objective tests;
- repository/diff/test artifact browser.

### Phase 5 — Tool Calling

Deliverables:

- deterministic tool simulator;
- llama-server function/tool calling adapter;
- syntax/selection/arguments/execution/recovery scoring;
- trace UI.

### Phase 6 — Single Agent

Deliverables:

- native observable agent loop;
- tool permissions;
- step/token/time limits;
- agent trace;
- coding/DevOps agent tasks.

### Phase 7 — Multi Agent

Deliverables:

- Manager/Coder/Tester/Reviewer topology;
- shared workspace rules;
- coordination metrics;
- single-vs-multi comparison report.

### Phase 8 — Publication/Polish

Deliverables:

- export bundles;
- static/public safe views;
- chart export;
- methodology generator;
- run links for DevSnack Lab.

### Current implementation status

Phases 0–8 are implemented in the current repository. See `docs/IMPLEMENTATION_STATUS.md` for the verified status matrix and explicit limitations. The implementation is a working local benchmark platform, not methodology certification or a secure arbitrary-code execution service.

---

## 28. Initial Development Backlog (historical)

Priority P0:

1. Make repository boot reliably on GB10 ARM64.
2. Add migration/versioning to SQLite schema.
3. Implement persistent JSONL event logging.
4. Harden llama-bench argument generation and parse errors.
5. Add endpoint/runner validation.
6. Add cancellation with subprocess termination.
7. Add environment capture.
8. Add `/slots` polling.
9. Add GPU/memory telemetry adapter.
10. Add run-detail UI.
11. Add recipe selection UI.
12. Add result charts.

Priority P1:

1. Model registry/scanner.
2. Managed llama-server process manager.
3. Queue.
4. concurrency matrix recipes.
5. cold/warm policy.
6. artifact index.
7. compare page.
8. CSV/Markdown export.

The backlog above records the original bottom-up plan. It is historical: the current repository has implemented the listed Phase 0–8 platform layers. Remaining work is hardening, broader validation, and future workload expansion, not a missing core scaffold.

---

## 29. Acceptance Tests

### Core

- Web POST creates run.
- CLI POST creates equivalent run.
- duplicate UI refresh does not duplicate jobs.
- run IDs are unique.
- completed result survives backend restart.

### llama-bench

- binary-not-found gives clear failure.
- nonzero exit captures stderr.
- JSON output retained raw.
- normalized rows retain build commit, model identity, PP/TG parameters and avg/stddev.

### llama-server

- health check detects unavailable server.
- concurrency 1/2/4 produces expected request count.
- failed HTTP requests are counted rather than discarded.
- prompt and predicted timings are retained when provided.

### Artifacts

- every run has manifest.
- completed coding task has final repository and test log.
- artifact path traversal is prevented in API.

### UI

- launch without terminal.
- see live status.
- open completed result.
- compare compatible performance runs.
- distinguish failed/aborted results.

---

## 30. Implementation Notes

The current implementation preserves the original architecture while implementing the Phase 0–8 path:

- `backend/app/runners/llama_bench.py` invokes `llama-bench -o json` and stores raw stdout/stderr.
- `backend/app/runners/server_perf.py` drives concurrent requests against llama-server `/completion` and records request and llama.cpp timing values.
- `backend/app/services/run_manager.py` merges recipes, creates run directories and manages asynchronous execution.
- `backend/app/services/events.py` persists and replays `events.jsonl` for SSE.
- coding/tool/agent/knowledge runners execute their current fixture-backed evaluators through the same RunContext.
- the React UI launches suites, monitors runs, compares results, browses artifacts, and exports reports.

It is a working local benchmark platform, not benchmark methodology certification. Coding remains workspace-isolated process execution rather than a secure sandbox, and recipe-based reproducibility must remain covered by regression and Golden Smoke validation.

---

## 31. Recommended First Implementation Session

1. Build/install current llama.cpp on GB10 and record binary paths.
2. Start backend and frontend.
3. Edit `performance-smoke.yaml` to a known GGUF.
4. Launch the smoke benchmark from Web UI.
5. Verify `manifest.json`, raw llama-bench output and DB run record.
6. Add normalized display of PP/TG rows.
7. Start llama-server with `--metrics --slots` and a controlled `-np` value.
8. Run `server-concurrency-smoke.yaml` through API/CLI.
9. Add `/slots` live card and system memory telemetry.
10. Freeze `performance-standard-v1` only after repeated behavior is understood.

This creates a trustworthy performance base before higher-level evaluator complexity is introduced.

---

## 32. Key Risks

### Metric confusion

Mitigation: label microbenchmark versus end-to-end values and preserve raw timing provenance.

### llama.cpp API evolution

Mitigation: isolate all llama.cpp-specific behavior in adapters; store llama.cpp build commit on every run.

### Benchmark harness becoming an agent framework project

Mitigation: phases; native minimal loop; defer framework abstraction until performance/coding foundations are stable.

### Unsafe generated code

Mitigation: no broad repository coding tests until sandbox controls exist.

### Non-reproducible model state

Mitigation: explicit cache/warmup/server lifecycle policies and immutable manifests.

### Too many metrics without interpretable conclusions

Mitigation: profile views and recipe-specific comparisons rather than a universal score.

---

## 33. Source References Used for llama.cpp Assumptions

These references should be rechecked during implementation because llama.cpp evolves quickly.

- llama.cpp `llama-bench` README: https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md
- llama.cpp server README: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- llama.cpp server benchmark README: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/bench/README.md
- llama.cpp repository README: https://github.com/ggml-org/llama.cpp

Verified design assumptions at document creation time:

- llama-bench supports prompt-processing, text-generation and combined tests plus JSON/JSONL output.
- llama-server supports OpenAI-compatible routes, parallel decoding and continuous batching.
- llama-server provides monitoring endpoints including slots and optional Prometheus-compatible metrics.
- direct completion results can expose llama.cpp timing data useful for prompt/decode throughput measurement.

---

## 34. Handoff Rule for Luna and Local LLM Workers

Treat this document as architecture intent, not permission to implement every phase at once.

Implementation should proceed bottom-up:

1. core run correctness;
2. performance measurement trustworthiness;
3. persistence and comparison;
4. coding/tool infrastructure;
5. single-agent;
6. multi-agent;
7. publication.

Any worker changing the result schema, run lifecycle, benchmark methodology or artifact contract should write an ADR or design note before making an incompatible change. Avoid local optimizations that make Web, CLI and API produce different semantics.

The most important invariant is:

> A run launched from Web, CLI or API must be the same experiment once it reaches the benchmark core, and its evidence must remain inspectable after completion.
