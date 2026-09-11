# Performance Benchmark v1

## 목적

`llama-bench`를 이용해 모델의 prompt processing(PP)과 token generation(TG) 성능을 동일 조건에서 반복 측정하고, 나중에 같은 모델·설정·recipe로 재현할 수 있도록 실행 증거를 보존합니다.

## 측정 조건

`../../recipes/performance-v1.yaml`은 다음 matrix를 사용합니다.

- PP: 512, 2,048, 8,192, 32,768 tokens
- TG: 512 tokens
- 각 조건 5회 반복
- GPU layers: 999
- batch: 2,048
- ubatch: 512
- flash attention: on
- threads: 20
- KV cache types: K/V `f16`

PP와 TG는 `llama-bench`의 엔진 마이크로벤치마크입니다. PP는 prompt 처리, TG는 decode를 의미하며, HTTP 요청 latency나 사용자 체감 전체 응답 시간과 혼동하지 않습니다. `llama-bench`의 prompt length가 주요 context 조건이며, 32K 조건까지의 matrix를 recipe에 고정합니다.

## 반복 횟수와 결과

각 PP/TG 조건은 5회 실행합니다. `result.json`의 `formal_summary.representative`에는 대표 키(`pp_512`, `pp_2048`, `pp_8192`, `pp_32768`, `tg_512`)별로 다음을 남깁니다.

- `mean`: 평균 tokens/s
- `stddev`: 표준편차 tokens/s
- `repetitions`: 각 반복의 raw tokens/s 값

원본 `llama-bench` JSON은 `rows`와 `llama-bench.stdout.json`에 그대로 보존하고, stderr는 `llama-bench.stderr.log`에 저장합니다. 각 row에도 llama-bench가 반환한 `avg_ts`, `stddev_ts`, `samples_ts`, raw timing 값을 유지합니다.

## 기록되는 실행 환경

기존 provenance 구조를 사용해 다음을 기록합니다.

- 모델 파일명과 경로, 크기, 수정 시각
- 모델 family/variant 추정값, quantization, tags
- 기존 model registry가 제공하는 ID 또는 hash가 있으면 해당 식별자
- llama.cpp commit/build 정보
- llama-bench 경로
- GPU와 driver 정보
- `n_gpu_layers`, batch, ubatch, flash attention, threads, KV cache 설정
- PP/TG matrix, repetition count와 실행 시각
- platform commit과 resolved runtime configuration

대형 GGUF는 전체 SHA-256 계산 비용 때문에 기존 registry 정책상 자동 hash가 없을 수 있습니다. 이 경우 파일 path·size·mtime과 llama-bench의 model metadata를 함께 사용합니다.

## 저장되는 evidence

정식 run은 다음을 보존합니다.

- `recipe.yaml`
- `resolved-config.yaml`
- `manifest.json`
- `environment.json`
- `result.json`
- `metrics.jsonl`
- `events.jsonl`
- `llama-bench.stdout.json`
- `llama-bench.stderr.log`

## 모델 간 비교 원칙

모델을 비교할 때는 반드시 동일한 `performance-v1.yaml`, 동일한 llama.cpp build, 동일한 GPU/offload·batch·ubatch·flash attention·KV cache·threads 조건, 동일한 PP/TG matrix와 반복 횟수를 사용합니다. 모델 path와 variant/quant만 비교 변수로 바꾸고, 각 run의 provenance와 raw evidence를 함께 확인합니다.
