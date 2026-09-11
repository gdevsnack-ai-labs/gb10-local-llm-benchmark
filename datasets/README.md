# Canonical Benchmark Datasets

This directory contains the fixed datasets used by the seven-suite GB10 Local LLM Benchmark. They are project-authored benchmark fixtures for controlled comparison, not a claim to represent all model knowledge or capability.

## Purpose and provenance

The datasets were created and curated for this benchmark's scoring contracts. They use deterministic prompts, expected answers, tool specifications, or task definitions so that the same model/runtime conditions can be compared repeatedly. They are not copied from an external leaderboard dataset in this release.

The benchmark platform records dataset version, scoring type, and SHA-256 in `results-public/methodology.json`. The public projection exposes those identifiers rather than raw run evidence.

## Canonical datasets

| Dataset | Version | Scoring | SHA-256 |
|---|---:|---|---|
| `knowledge-v1` | 1.0 | deterministic answer matching | `44883816f2b11f8560c69a6c28933c2496ea137a5b98860dd102d397349f650c` |
| `knowledge-v1.2` | 1.2 | deterministic normalized answer matching | `66e691da99a416fdf59887930d40c0dd7d12538b9f81b818e15e5bd0f6584079` |
| `coding-v1` | 1.0 | generated code + pytest | `53a283316be1ab63ee04c051d5194decbc3c7e27b76e5c177293bcab87dccbbd` |
| `tool-call-v1` | 1.1 | deterministic tool, argument, and execution scoring | `8c0c1abefa2825c97341afaee620adbbf60cf43add20e0535c599872733065d5` |
| `agent-single-v1` | 1.1 | deterministic completion, step, and tool scoring | `188a63368a0631cc6cc6a80a8eed165f559f8131b5196ba28a951c428479b5d5` |
| `agent-multi-v1` | 1.1 | deterministic role, handoff, and completion scoring | `ee9bc5035f9ca17be36a3749e62322d767232570960ae80d3041b2b1741a010a` |

## Version and derivative rules

Do not edit a canonical dataset in place while keeping its version/name and hash identity. A modified, extended, translated, or otherwise derived dataset must be published under a new dataset version/name, with a new SHA-256 and an explicit derivative note.

The tool-call fixtures may contain synthetic paths such as `/tmp/data.txt` because those paths are part of an intentional benchmark task contract. They are not references to a private machine or to a file shipped with this repository.

## License

The canonical original dataset content is offered under CC BY 4.0. See [`../DATASET_LICENSE.md`](../DATASET_LICENSE.md) and [`LICENSE`](LICENSE). Third-party material, if introduced in a future release, must be separately attributed and rights-checked before inclusion.

## Interpretation limit

Dataset scores are fixed-harness observations under the stated suite and recipe. They are not an absolute score for general intelligence, safety, or every real-world workload.
