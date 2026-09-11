# Public Release Contents

This document defines the reviewed file boundary for this repository. It is not a mirror of the canonical local benchmark workspace.

## Included

- `backend/` — benchmark control plane, runners, schemas, and tests
- `frontend/` — local control UI source and package metadata
- `data/` — small synthetic compatibility fixtures used by tests and sample recipes; no raw evidence
- `recipes/` — versioned benchmark recipes with environment-specific server URLs left blank
- `datasets/` — canonical fixed datasets only
- `docs/public/` — public analyses and interpretation documents, excluding the unresolved license decision memo
- `docs/methodology/` — public suite definitions and platform design
- `results-public/` — sanitized projections, manifests, schemas, methodology, and public result indexes
- `scripts/export_public_release.py` — historical release exporter retained as source documentation; it never publishes externally
- `scripts/test_current_projection.py` — current projection, hash, and safety validation
- `scripts/test_public_release.py` — public artifact validation that does not require raw runs
- `.env.example` — placeholders only
- `README.md`, `BENCHMARK_INTEGRITY.md`, `DATASET_LICENSE.md`, `LICENSE_SCOPE.md`
- `LICENSE` — Apache-2.0 source license

## Explicitly excluded

- `runs/`, `runs-agent/`, `workspaces-agent/`
- `archive/`, `artifacts/`, `private/`
- `backend/llmbench.db`, SQLite, and any other database files
- logs, raw events, raw prompts, raw responses, agent traces, and environment snapshots
- screenshots, generated HTML workspaces, and validation artifacts
- GGUF, MMPROJ, model weights, and downloaded model assets
- `.venv/`, `node_modules/`, `dist/`, `build/`, caches, and bytecode
- `docs/public/LICENSE_OPTIONS.md`
- methodology ADRs and local execution runbooks
- untracked files from the canonical local workspace

The canonical local repository and its raw evidence remain separate from this public source, methodology, dataset, and result boundary.
