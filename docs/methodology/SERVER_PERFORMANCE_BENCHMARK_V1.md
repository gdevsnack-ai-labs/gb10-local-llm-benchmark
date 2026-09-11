# Server-performance Benchmark v1

## Purpose

This suite repeatedly measures concurrent-request performance through `llama-server` with the same prompts and server settings. Its purpose is to compare aggregate throughput and per-request performance reproducibly when the model, quantization, or server build changes.

## Measurement conditions

[`../../recipes/server-performance-v1.yaml`](../../recipes/server-performance-v1.yaml) uses this matrix:

- Concurrency: 1, 2, 4, and 8
- Total requests per concurrency: concurrency × 4
- Maximum output per request: 512 tokens
- The same fixed prompt for every request
- Prompt cache: off
- Context: 8192
- Batch / ubatch: 2048 / 512
- Flash attention: on
- Parallel slots: 8

## Repetitions

Each concurrency condition runs three times. A formal run contains four conditions × three repetitions × (concurrency × 4) requests. Raw repetition results and per-request samples are retained in the canonical execution evidence.

## Recorded results

Each repetition and concurrency aggregate records:

- aggregate generation throughput: total generated tokens / batch wall time
- per-request generation throughput: per-request generated tokens and mean, standard deviation, minimum, and maximum latency
- total wall time
- request latency p50 / p95 / p99
- successful and failed request counts and failure rate
- prompt-processing throughput when provided by the runner response
- `/slots` and `/metrics` polling evidence

Aggregate throughput is the actual total throughput of the server while handling concurrent requests. Per-request performance describes the individual request experience. They answer different questions and neither should be used alone to judge concurrency performance.

## Recorded environment

The manifest, environment, and resolved-configuration records include:

- model name, path, variant, and quantization
- `llama.cpp` commit and `llama-server` path/build/version
- GPU and driver
- context, batch, ubatch, and flash attention
- actual parallel/slot settings and execution configuration
- execution time, platform commit, and recipe/configuration hash

## Stored evidence

A formal run directory contains:

- `recipe.yaml`
- `resolved-config.yaml`
- `manifest.json`
- `environment.json`
- `result.json`
- `events.jsonl`
- `samples.jsonl` — per-request raw results
- `llama-server.log`

`result.json` stores concurrency 1/2/4/8 under `conditions`; each condition includes summary statistics and `repetitions_raw`. `samples.jsonl` records the repetition, concurrency, and request index.

## Model comparison rule

Model comparisons must use the same recipe, `llama-server` settings, `llama.cpp` build, and GPU conditions. Limit comparison variables to explicitly declared model differences such as model path and variant/quantization, and review provenance and evidence with the result.
