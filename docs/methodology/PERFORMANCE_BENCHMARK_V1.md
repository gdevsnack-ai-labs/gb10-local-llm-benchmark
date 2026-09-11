# Performance Benchmark v1

## Purpose

`llama-bench` repeatedly measures prompt processing (PP) and token generation (TG) performance under identical conditions. The recorded execution evidence makes it possible to reproduce a result with the same model, configuration, and recipe.

## Measurement conditions

[`../../recipes/performance-v1.yaml`](../../recipes/performance-v1.yaml) uses this matrix:

- PP: 512, 2,048, 8,192, and 32,768 tokens
- TG: 512 tokens
- Five repetitions per condition
- GPU layers: 999
- Batch: 2,048
- Ubatch: 512
- Flash attention: on
- Threads: 20
- KV cache types: K/V `f16`

PP and TG are engine microbenchmarks from `llama-bench`. PP is prompt processing and TG is decoding; neither should be confused with HTTP request latency or total user-perceived response time. Prompt length is the primary context variable, with the 32K condition fixed in the recipe.

## Repetitions and results

Each PP/TG condition runs five times. `result.json` stores representative values under `formal_summary.representative` using keys such as `pp_512`, `pp_2048`, `pp_8192`, `pp_32768`, and `tg_512`.

- `mean`: mean tokens per second
- `stddev`: standard deviation in tokens per second
- `repetitions`: raw tokens-per-second values for each repetition

The original `llama-bench` JSON is preserved in `rows` and `llama-bench.stdout.json`; stderr is stored in `llama-bench.stderr.log`. Each row retains the returned `avg_ts`, `stddev_ts`, `samples_ts`, and raw timing values.

## Recorded execution environment

The provenance structure records:

- model filename and path, size, and modification time
- inferred model family/variant, quantization, and tags
- an existing model-registry ID or hash when available
- `llama.cpp` commit and build information
- `llama-bench` path
- GPU and driver information
- `n_gpu_layers`, batch, ubatch, flash attention, threads, and KV-cache settings
- PP/TG matrix, repetition count, and execution time
- platform commit and resolved runtime configuration

Large GGUF files may not receive an automatic full SHA-256 under the registry policy because of the computation cost. In that case, the file path, size, modification time, and `llama-bench` model metadata are used together.

## Stored evidence

A formal run preserves:

- `recipe.yaml`
- `resolved-config.yaml`
- `manifest.json`
- `environment.json`
- `result.json`
- `metrics.jsonl`
- `events.jsonl`
- `llama-bench.stdout.json`
- `llama-bench.stderr.log`

## Model comparison rule

Model comparisons must use the same `performance-v1.yaml`, `llama.cpp` build, GPU/offload, batch, ubatch, flash-attention, KV-cache, and thread settings, as well as the same PP/TG matrix and repetition count. Only the explicitly declared model variables, such as model path and variant/quantization, should change. Review provenance and evidence for each run together with the result.
