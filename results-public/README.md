# Public benchmark data

This directory contains sanitized benchmark summaries, cycle manifests, evaluator/version metadata, provenance records, schemas, and release projections. Raw run artifacts are not copied here.

- `index.json`: public files and schema version
- `models/`: model and cycle summary indexes
- `cycles/`: public cycle manifests
- `methodology.json`: canonical evaluator and dataset hashes
- `schema.json`: public field contract for model summaries
- `releases/gb10-local-llm-benchmark.json`: current 23-variant benchmark projection
- `releases/gb10-local-llm-benchmark.manifest.json`: current projection hash and source/count manifest
- `releases/gb10-llm-benchmark-v1-20260906.json`: immutable historical release for 18 models across seven suites
- `releases/gb10-llm-benchmark-v1-20260906.manifest.json`: historical release hash and source/count manifest

Paths use repository-relative references or run IDs. Personal model-storage paths and machine-specific `llama.cpp` paths are not part of the public data.

The 2026-09-06 immutable release contains `72 revalidated evaluator runs`: four evaluator suites—Knowledge, Tool-call, Agent-single, and Agent-multi—were run across 18 models. Performance, Server-performance, and Coding reuse 54 established source runs, with 126 source-run references in that historical matrix. The current projection adds 28 fresh full-cycle runs for four N2.5 Mini variants from 2026-09-10, resulting in 23 model variants and 161 source-run references.

The current projection updates `gb10-local-llm-benchmark.json` rather than creating date-specific detail pages. Model-family pages can derive their variant matrix from this projection. Historical release files remain immutable; new measurements require an explicitly versioned projection or release identity.
