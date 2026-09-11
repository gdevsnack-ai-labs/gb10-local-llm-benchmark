# Server-performance Benchmark v1

## 목적

`llama-server` 기반 동시 요청 성능을 동일한 prompt와 server 설정으로 반복 측정합니다. 모델·quant·server build를 바꿔도 같은 recipe로 aggregate 처리량과 요청 단위 성능을 재현 가능하게 비교하는 것이 목적입니다.

## 측정 조건

`../../recipes/server-performance-v1.yaml`은 다음 matrix를 사용합니다.

- concurrency: 1, 2, 4, 8
- 각 concurrency의 총 요청 수: concurrency × 4
- 요청당 최대 출력: 512 tokens
- 모든 요청에 동일한 고정 prompt 사용
- prompt cache: off
- context: 8192
- batch / ubatch: 2048 / 512
- flash attention: on
- parallel slots: 8

## 반복 횟수

각 concurrency 조건을 3회 반복합니다. 한 정식 run에는 4개 조건 × 3회 × (concurrency × 4) 요청이 포함됩니다. 각 repetition의 raw 결과와 요청별 sample을 보존합니다.

## 기록되는 결과

각 repetition과 concurrency 집계에는 다음을 기록합니다.

- aggregate generation throughput: 전체 생성 token / 해당 batch wall time
- per-request generation throughput: 요청별 생성 token / 요청 latency의 평균·표준편차·최소·최대
- total wall time
- request latency p50 / p95 / p99
- 성공·실패 요청 수와 failure rate
- runner가 응답에서 제공할 때 prompt processing throughput
- `/slots` 및 `/metrics` polling evidence

Aggregate throughput은 동시 요청을 모두 처리한 서버의 실제 총 처리량이고, per-request 성능은 개별 요청의 체감 처리 성능입니다. 둘은 목적이 다르므로 어느 한 숫자만으로 동시성 성능을 판단하지 않습니다.

## 기록되는 환경

기존 manifest / environment / resolved-config 구조를 사용해 다음을 남깁니다.

- model name, path, variant, quant
- llama.cpp commit 및 llama-server path/build/version
- GPU / driver
- context, batch, ubatch, flash attention
- 실제 parallel/slot 설정과 실행 config
- 실행 시각, platform commit, recipe/config hash

## 저장되는 evidence

정식 run 디렉터리에는 다음을 저장합니다.

- `recipe.yaml`
- `resolved-config.yaml`
- `manifest.json`
- `environment.json`
- `result.json`
- `events.jsonl`
- `samples.jsonl` — 요청별 raw result
- `llama-server.log`

`result.json`의 `conditions` 아래에 concurrency 1/2/4/8이 각각 들어가며, 각 조건에는 평균·표준편차 통계와 `repetitions_raw`가 포함됩니다. `samples.jsonl`에는 repetition, concurrency, request index가 함께 기록됩니다.

## 모델 비교 원칙

모델 간 비교에서는 반드시 동일한 recipe와 동일한 llama-server 설정·llama.cpp build·GPU 조건을 사용합니다. 비교 변수는 model path와 variant/quant 등 명시한 모델 차이로 제한하고, 각 run의 provenance와 raw evidence를 함께 검토합니다.
