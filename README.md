# GB10 Local LLM Benchmark

A reproducible local LLM benchmark for NVIDIA DGX Spark GB10 systems using `llama.cpp` and GGUF model variants.

This repository contains the benchmark source code, canonical fixed datasets, public methodology, and sanitized result projections. It does not include raw runs, model weights, prompts or responses, agent traces, environment snapshots, or machine-specific evidence.

## What is measured

The benchmark defines eight suites:

1. **Performance** — prompt processing and token generation
2. **Server-performance** — concurrency, throughput, and latency
3. **Knowledge** — fixed question-answer accuracy
4. **Coding** — generated code and test outcomes
5. **Tool-call** — tool selection, arguments, execution, and recovery
6. **External tool-eval-bench** — 69 deterministic external tool-use scenarios, trace, and safety
7. **Agent-single** — single-agent completion and tool behavior
8. **Agent-multi** — role participation, handoff, and completion

The canonical comparison condition uses `llama.cpp` with reasoning **OFF** unless a recipe explicitly defines another experiment. Server-performance MTP and non-MTP conditions remain separate variants.

## Current benchmark projection

The current projection is the latest sanitized benchmark view used by DevSnack. Historical immutable releases remain versioned separately and are not silently overwritten.

- Release ID: `gb10-local-llm-benchmark`
- Model variants: **23**
- Suites: **8**
- Revalidated evaluator runs: **76**
- Reused source runs: **57**
- Fresh full-cycle runs: **28**
- Source run references: **169**
- External tool-eval evaluator runs: **8**
- Raw runs included: **false**
- Projection updated: **2026-09-16**
- Projection SHA-256: `79a87494564558b620b125a08d53b0ae4b7f9bb9f736e419f9e0b46bb4f707c1`

Machine-readable files:

- [`results-public/releases/gb10-local-llm-benchmark.json`](results-public/releases/gb10-local-llm-benchmark.json)
- [`results-public/releases/gb10-local-llm-benchmark.manifest.json`](results-public/releases/gb10-local-llm-benchmark.manifest.json)
- [`results-public/methodology.json`](results-public/methodology.json)
- [`results-public/schema.json`](results-public/schema.json)
- [Historical immutable release](results-public/releases/gb10-llm-benchmark-v1-20260906.json)

## Where to view the benchmark

GitHub is the source and evidence boundary for the project: source code, methodology, fixed datasets, schemas, manifests, and sanitized public result data are maintained here.

DevSnack provides the presentation layer:

- [Benchmark Hub](https://devsnack-blog.vercel.app/benchmarks) — human-readable model and suite comparison
- [Benchmark Story](https://devsnack-blog.vercel.app/devsnack/dgx-spark-gb10-local-llm-benchmark) — editorial explanation and context
- [Machine-readable JSON](https://devsnack-blog.vercel.app/data/benchmarks/gb10-local-llm-benchmark.json) — the current sanitized projection

DevSnack presents the projection and manifest as static public data. It does not read raw runs or machine-specific evidence at runtime.

## Repository layout

```text
backend/             FastAPI benchmark control plane and runners
frontend/            React/Vite local control UI
data/                Small synthetic compatibility fixtures
recipes/             Versioned suite and execution recipes
datasets/            Canonical fixed datasets and hashes
docs/methodology/    Suite definitions and platform design
docs/public/         Public result analyses and interpretation guides
results-public/      Sanitized JSON projections, manifests, and schema
scripts/             Public release validation and historical exporter
```

The reviewed file boundary is documented in [`PUBLIC_RELEASE_ALLOWLIST.md`](PUBLIC_RELEASE_ALLOWLIST.md). Dataset and result immutability rules are in [`BENCHMARK_INTEGRITY.md`](BENCHMARK_INTEGRITY.md). External tool-eval-bench is a separate protocol from the internal Tool-call v1.1 suite; its numbers are shown as a separate lane and are not merged.

## Local reproduction

The platform can be run on a compatible local machine with Python, Node.js, `llama.cpp`, and model files supplied separately by the user.

### Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e backend

# Configure model paths, server settings, and local API settings in your environment.
# Keep generated runs outside Git-tracked files.
uvicorn app.main:app
```

### Frontend

```bash
cd frontend
npm ci
# Set VITE_API_BASE_URL to the API base for your local deployment when needed.
npm run dev
```

Run recipes through the backend control plane or the local CLI after configuring model paths, server settings, and dataset locations for your machine. Model weights are not distributed in this repository.

## Methodology and datasets

- Suite definitions: [`docs/methodology/`](docs/methodology/)
- Public analyses: [`docs/public/`](docs/public/)
- Canonical datasets: [`datasets/`](datasets/)
- Dataset provenance and SHA-256 records: [`datasets/README.md`](datasets/README.md)
- Integrity and immutable-release rules: [`BENCHMARK_INTEGRITY.md`](BENCHMARK_INTEGRITY.md)

Scores are fixed-harness observations under stated conditions. They are not universal model quality, safety, or product-suitability scores.

## Evidence boundary

Raw run directories, raw prompts and responses, agent traces, screenshots, generated workspaces, local environment snapshots, model files, logs, and machine-specific execution records are not distributed here. A new benchmark result or dataset revision must receive a new version or release identity rather than silently overwriting an immutable public release.

## License

- Source code and ordinary documentation: Apache License 2.0; see [`LICENSE`](LICENSE).
- Canonical benchmark datasets and sanitized public result data: Creative Commons Attribution 4.0 International; see [`DATASET_LICENSE.md`](DATASET_LICENSE.md) and the notices in `datasets/` and `results-public/`.
- Third-party model files, upstream tools, names, and external materials are not included and remain subject to their own terms.
