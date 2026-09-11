# GB10 Local LLM Benchmark

A local-first benchmark platform for comparing local LLM models on an NVIDIA DGX Spark GB10 using `llama.cpp` and GGUF model variants.

This repository is the **public-ready source and result staging** for the benchmark. It contains benchmark code, canonical fixed datasets, methodology, and sanitized public result projections. Raw runs, model files, prompts/responses, agent traces, environment snapshots, and private machine evidence are intentionally not included.

## What is measured

The current benchmark contract contains seven suites:

1. **Performance** — prompt processing and token generation
2. **Server-performance** — concurrency, throughput, and latency
3. **Knowledge** — fixed question-answer accuracy
4. **Coding** — generated code and test outcomes
5. **Tool-call** — tool selection, arguments, execution, and recovery
6. **Agent-single** — single-agent completion and tool behavior
7. **Agent-multi** — role participation, handoff, and completion

The canonical comparison condition uses `llama.cpp` with reasoning **OFF** unless a recipe explicitly defines another experiment. Server-performance MTP and non-MTP conditions remain separate variants.

## Current public release

- Release ID: `gb10-local-llm-benchmark`
- Model variants: **23**
- Suites: **7**
- Revalidated evaluator runs: **76**
- Reused source runs: **57**
- Fresh full-cycle runs: **28**
- Source run references: **161**
- Raw runs public: **false**
- Projection SHA-256: `7065e2b970ae63a1c024e659f38f69d876215978539f6653df3fe6483a199738`

Machine-readable release files:

- [`results-public/releases/gb10-local-llm-benchmark.json`](results-public/releases/gb10-local-llm-benchmark.json)
- [`results-public/releases/gb10-local-llm-benchmark.manifest.json`](results-public/releases/gb10-local-llm-benchmark.manifest.json)
- [`results-public/methodology.json`](results-public/methodology.json)
- [`results-public/schema.json`](results-public/schema.json)

## DevSnack links

- [DevSnack Standard Benchmark](https://devsnack-blog.vercel.app/benchmarks)
- [DevSnack benchmark Story](https://devsnack-blog.vercel.app/devsnack/dgx-spark-gb10-local-llm-benchmark)
- [Current machine-readable JSON](https://devsnack-blog.vercel.app/data/benchmarks/gb10-local-llm-benchmark.json)

DevSnack serves the sanitized projection and manifest as static public data. It does not read raw runs or private benchmark evidence at runtime.

## Repository layout

```text
backend/             FastAPI benchmark control plane and runners
frontend/            React/Vite local control UI
data/                Small synthetic compatibility fixtures only
recipes/             Versioned suite and execution recipes
datasets/            Canonical fixed datasets and hashes
docs/methodology/    Public suite definitions and platform design
docs/public/         Public result analyses and interpretation guides
results-public/      Sanitized JSON projections, manifests, and schema
scripts/             Public release validation and historical exporter
```

The public allowlist and exclusion contract are documented in [`PUBLIC_RELEASE_ALLOWLIST.md`](PUBLIC_RELEASE_ALLOWLIST.md). Dataset and result immutability rules are in [`BENCHMARK_INTEGRITY.md`](BENCHMARK_INTEGRITY.md).

## Local reproduction

The platform is intended to run on a compatible local machine with Python, Node.js, `llama.cpp`, and the required model files supplied by the operator.

### Backend

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e backend

# Configure model/tool locations and any local API settings in your environment.
# Keep generated runs outside Git-tracked public files.
uvicorn app.main:app
```

### Frontend

```bash
cd frontend
npm ci
# Set VITE_API_BASE_URL to the API base for your local deployment when needed.
npm run dev
```

Run recipes through the backend control plane or the local CLI after configuring model paths, server settings, and dataset locations for your own machine. No model weights are distributed in this repository.

## Methodology and datasets

- Suite definitions: [`docs/methodology/`](docs/methodology/)
- Public analyses: [`docs/public/`](docs/public/)
- Canonical datasets: [`datasets/`](datasets/)
- Dataset provenance and SHA-256 records: [`datasets/README.md`](datasets/README.md)
- Integrity and immutable-release rules: [`BENCHMARK_INTEGRITY.md`](BENCHMARK_INTEGRITY.md)

Scores are fixed-harness observations under stated conditions. They are not universal model quality, safety, or product-suitability scores.

## Evidence boundary

Raw run directories, raw prompts and responses, agent traces, screenshots, generated workspaces, local environment snapshots, model files, logs, and private execution records stay outside this public-ready repository. A new benchmark result or dataset revision must receive a new version or release identity rather than silently overwriting an immutable public release.

## License

- Source code and ordinary documentation: Apache License 2.0; see [`LICENSE`](LICENSE).
- Canonical benchmark datasets and sanitized public result data: Creative Commons Attribution 4.0 International; see [`DATASET_LICENSE.md`](DATASET_LICENSE.md) and the notices in `datasets/` and `results-public/`.
- Third-party model files, upstream tools, names, and external materials are not included and remain subject to their own terms.
