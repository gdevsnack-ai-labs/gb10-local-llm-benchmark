# Benchmark Integrity and Provenance

## Canonical identity

The current public projection is identified by:

- Release ID: `gb10-local-llm-benchmark`
- Schema: `gb10-benchmark-public-v1`
- Model variants: 23
- Suites: 7
- Revalidated evaluator runs: 76
- Reused source runs: 57
- Fresh full-cycle runs: 28
- Source run references: 161
- Raw runs public: `false`
- Projection SHA-256: `7065e2b970ae63a1c024e659f38f69d876215978539f6653df3fe6483a199738`

The release manifest records the projection hash and reconciled counts. The JSON projection and manifest are the public numeric source of truth.

## Dataset identity

Every canonical dataset is identified by its dataset name, version, and SHA-256. The canonical hashes are recorded in [`datasets/README.md`](datasets/README.md) and [`results-public/methodology.json`](results-public/methodology.json).

A dataset modification must not continue to use the same benchmark version/name. A modified or extended dataset must be labeled as a derivative or a new version and receive a new hash.

## Result immutability

A public result release is immutable by identity. Do not alter result values while keeping the same release identity and manifest hash. A corrected measurement, changed scorer, changed dataset, changed evaluator, or changed condition requires a new release identity or an explicitly versioned current projection update with a new manifest hash.

Historical releases remain historical. The current projection may add a new model variant or a new measurement only through the exporter and reconciliation checks; it must not silently rewrite historical release files.

## Evidence boundary

Raw runs, manifests, logs, environment snapshots, prompts, responses, agent traces, generated workspaces, screenshots, and model files are canonical local evidence but are not public release inputs. The public projection contains only the metrics and provenance fields required to interpret the comparison safely.

The exporter is separate from external publication. It does not call GitHub, Vercel, Supabase, or Blogger.

## Interpretation limits

Scores are fixed-harness observations under the stated hardware, runtime, recipe, dataset, and reasoning conditions. They are not universal intelligence, safety, or product-quality scores. Unlike suites and unlike execution conditions must not be collapsed into one unexplained total score.

## Public verification

The public artifact checks must pass before a release is staged:

```bash
python3 scripts/test_current_projection.py
python3 -m pytest scripts/test_public_release.py -q
```
