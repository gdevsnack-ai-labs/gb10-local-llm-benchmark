# Public Release Allowlist

This repository is assembled from an explicit public-ready allowlist. It is not a mirror of the local benchmark workspace.

## Included

- `backend/` — tracked benchmark control plane, runners, schemas, and tests
- `frontend/` — tracked local control UI source and package metadata
- `data/` — synthetic compatibility fixtures used by the runner tests and sample recipes
- `recipes/` — tracked versioned benchmark recipes; environment-specific server URLs are blank
- `datasets/` — canonical fixed datasets only
- `docs/public/` — public analysis and interpretation documents, excluding the unresolved license decision memo
- `docs/methodology/README.md`
- `docs/methodology/FULL_DESIGN.md`
- `docs/methodology/PERFORMANCE_BENCHMARK_V1.md`
- `docs/methodology/SERVER_PERFORMANCE_BENCHMARK_V1.md`
- `docs/methodology/KNOWLEDGE_BENCHMARK_V1.md`
- `docs/methodology/CODING_BENCHMARK_V1.md`
- `docs/methodology/TOOL_CALL_BENCHMARK_V1.md`
- `docs/methodology/AGENT_SINGLE_BENCHMARK_V1.md`
- `docs/methodology/AGENT_MULTI_BENCHMARK_V1.md`
- `results-public/` — sanitized projection, manifest, schema, methodology, and public result indexes
- `scripts/export_public_release.py` — historical release exporter retained as source documentation; it never publishes externally
- `scripts/test_current_projection.py` — current projection/hash/safety validation
- `scripts/test_public_release.py` — public artifact validation that does not require raw runs
- `.env.example` — placeholders only
- `README.md`, `BENCHMARK_INTEGRITY.md`, `DATASET_LICENSE.md`, `LICENSE_SCOPE.md`
- `LICENSE` — Apache-2.0 source license

## Explicitly excluded

- `data/` compatibility samples are included only when they are small synthetic fixtures; raw evidence is never included
- `runs/`, `runs-agent/`, `workspaces-agent/`
- `archive/`, `artifacts/`, `private/`
- `backend/llmbench.db`, SQLite, and any other database files
- logs, raw events, raw prompts, raw responses, agent traces, environment snapshots
- screenshots, generated HTML workspaces, and validation artifacts
- GGUF, MMPROJ, model weights, and downloaded model assets
- `.venv/`, `node_modules/`, `dist/`, `build/`, caches, and bytecode
- `docs/public/LICENSE_OPTIONS.md`
- methodology ADRs and local execution runbooks
- `docs/methodology/AGENT_BENCH_RUNBOOK.md`
- `docs/methodology/OPENCODE_AGENT_TEST_DS_APP_01.md`
- untracked files from the local workspace

The canonical local repository and its raw evidence remain separate. Do not recreate this staging by running `git add -A` in the local workspace.
