# Ornith 1.5 Full Benchmark v1

## 목적과 실행 범위

Ornith 1.5 35B-A3B MTP의 세 quantization variant를 동일한 GB10/llama.cpp 조건에서 비교했다. 각 모델에 대해 `performance-v1.yaml` → `server-performance-v1.yaml` → `knowledge-v1.yaml` → `coding-v1.yaml` → `tool-call-v1.yaml` → `agent-single-v1.yaml` → `agent-multi-v1.yaml` 순서로 새 Run을 만들었다.

- Cycle ID: `ornith15-v1-full-20260905-131958-052758`
- Started: `2026-09-05T04:19:58Z`
- Finished: `2026-09-05T05:27:58Z`
- Platform commit: `5380bfa7cf0defa924fdb62a0116e667a372b887`
- llama.cpp: `e107984bc`, build 10788
- Host: NVIDIA GB10, CUDA, aarch64, 20 physical/logical CPUs
- 모델 경로만 Run config로 지정했으며 recipe와 scoring 조건은 변경하지 않았다.
- 21/21 Run `completed`; retry 0; platform failure 0

각 Run directory에는 `manifest.json`, `recipe.yaml`, `resolved-config.yaml`, `environment.json`, `events.jsonl`, `result.json`, raw log/sample artifact가 있다. Dataset suite는 dataset snapshot과 SHA-256도 보존한다.

## 1. Performance

단위는 tokens/s이며 5회 반복의 mean ± stddev다.

| Model | Run ID | PP512 | PP2K | PP8K | PP32K | TG512 |
|---|---|---:|---:|---:|---:|---:|
| Q5_K_M | `20260905-131958-3cfdfd` | 1827.801 ± 46.660 | 1816.784 ± 12.569 | 1773.626 ± 20.591 | 1634.950 ± 28.213 | 64.546 ± 1.149 |
| Q6_K | `20260905-134111-76e244` | 1405.261 ± 141.396 | 1552.256 ± 15.231 | 1512.315 ± 42.379 | 1432.075 ± 17.220 | 57.901 ± 0.894 |
| Q8_0 | `20260905-140444-106393` | 1758.027 ± 56.957 | 1907.193 ± 10.432 | 1836.953 ± 27.294 | 1726.666 ± 7.451 | 57.795 ± 0.277 |

Q5_K_M과 Q8_0은 Q6_K보다 이 microbenchmark에서 높은 PP/TG 결과를 보였다. Performance raw evidence: `runs/<run-id>/llama-bench.stdout.json`, `llama-bench.stderr.log`, `result.json`.

## 2. Server-performance

각 조건은 3회 반복, 반복당 4개 요청, 요청당 512 generation tokens다. Aggregate/per-request는 tokens/s, latency는 초다. 모든 조건의 failure rate는 0%였다.

### Q5_K_M — Run `20260905-132350-d86bcf`

| Concurrency | Aggregate | Per-request | P50 | P95 | P99 | Failure |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 68.338 | 68.345 | 7.487 | 7.575 | 7.582 | 0% |
| 2 | 92.764 | 46.761 | 11.032 | 11.251 | 11.271 | 0% |
| 4 | 129.088 | 32.624 | 15.910 | 16.955 | 17.230 | 0% |
| 8 | 164.058 | 21.110 | 24.920 | 27.054 | 27.311 | 0% |

### Q6_K — Run `20260905-134533-c5b64a`

| Concurrency | Aggregate | Per-request | P50 | P95 | P99 | Failure |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 62.402 | 62.409 | 8.194 | 8.285 | 8.297 | 0% |
| 2 | 85.522 | 42.944 | 11.925 | 12.457 | 12.551 | 0% |
| 4 | 116.235 | 29.540 | 17.527 | 18.798 | 19.016 | 0% |
| 8 | 154.510 | 19.719 | 26.489 | 29.108 | 30.147 | 0% |

### Q8_0 — Run `20260905-140846-2c88a0`

| Concurrency | Aggregate | Per-request | P50 | P95 | P99 | Failure |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 60.349 | 60.354 | 8.490 | 8.546 | 8.548 | 0% |
| 2 | 84.163 | 42.130 | 12.075 | 12.489 | 12.553 | 0% |
| 4 | 117.318 | 29.823 | 17.324 | 18.536 | 18.865 | 0% |
| 8 | 158.085 | 20.261 | 26.224 | 28.476 | 29.649 | 0% |

Raw server evidence는 각 Run의 `llama-server.log`, `samples.jsonl`, `result.json`, `events.jsonl`에 있다.

## 3. Knowledge

Dataset SHA-256은 세 Run에서 동일한 정식 v1 dataset snapshot으로 보존됐다: `44883816f2b11f8560c69a6c28933c2496ea137a5b98860dd102d397349f650c`.

| Model | Run ID | Correct / Total | Accuracy | Category (general / korea / math / science / logic) |
|---|---|---:|---:|---|
| Q5_K_M | `20260905-133554-951ece` | 4 / 25 | 16% | 3/5, 1/5, 0/5, 0/5, 0/5 |
| Q6_K | `20260905-135837-dd55e7` | 4 / 25 | 16% | 3/5, 1/5, 0/5, 0/5, 0/5 |
| Q8_0 | `20260905-142150-af87ad` | 4 / 25 | 16% | 3/5, 1/5, 0/5, 0/5, 0/5 |

Evidence: `runs/20260905-133554-951ece/`, `runs/20260905-135837-dd55e7/`, `runs/20260905-142150-af87ad/`.

## 4. Coding

Dataset SHA-256: `53a283316be1ab63ee04c051d5194decbc3c7e27b76e5c177293bcab87dccbbd`.

| Model | Run ID | Passed / Total | Pass rate | Category basic / string / collection / edge_case | Failure types |
|---|---|---:|---:|---|---|
| Q5_K_M | `20260905-133625-26bbb8` | 9 / 12 | 75.00% | 3/3, 3/3, 1/3, 2/3 | runtime_error 1, syntax_error 2 |
| Q6_K | `20260905-135918-37492a` | 9 / 12 | 75.00% | 3/3, 3/3, 1/3, 2/3 | syntax_error 2, test_failure 1 |
| Q8_0 | `20260905-142222-7d90b3` | 10 / 12 | 83.33% | 3/3, 3/3, 2/3, 2/3 | syntax_error 2 |

Evidence: each coding Run directory의 `result.json`, `samples.jsonl`, `artifacts/`와 dataset snapshot.

## 5. Tool-call

Dataset SHA-256: `8c0c1abefa2825c97341afaee620adbbf60cf43add20e0535c599872733065d5`.

| Model | Run ID | Pass rate | Tool selection | Argument | Execution success | Failure types |
|---|---|---:|---:|---:|---:|---|
| Q5_K_M | `20260905-133757-c5d8cb` | 10/15 (66.67%) | 66.67% | 66.67% | 73.33% | wrong_tool 4, incomplete_sequence 1 |
| Q6_K | `20260905-140110-4b8720` | 10/15 (66.67%) | 66.67% | 66.67% | 73.33% | wrong_tool 4, incomplete_sequence 1 |
| Q8_0 | `20260905-142423-f1bd49` | 10/15 (66.67%) | 80.00% | 73.33% | 73.33% | wrong_arguments 1, wrong_tool 3, execution_error 1 |

Evidence: 각 Run의 `result.json`, `samples.jsonl`, `artifacts/tool-call/`, events, dataset snapshot.

## 6. Agent-single

Dataset SHA-256: `188a63368a0631cc6cc6a80a8eed165f559f8131b5196ba28a951c428479b5d5`.

| Model | Run ID | Pass rate | Avg steps | Avg tool calls | Category arithmetic / lookup / file / mixed | Failure types |
|---|---|---:|---:|---:|---|---|
| Q5_K_M | `20260905-133848-686f03` | 5/12 (41.67%) | 3.17 | 2.17 | 1/3, 1/3, 0/3, 3/3 | tool_error 4, missing_required_step 3 |
| Q6_K | `20260905-140201-6cf2ff` | 6/12 (50.00%) | 3.33 | 2.33 | 1/3, 2/3, 0/3, 3/3 | tool_error 4, missing_required_step 2 |
| Q8_0 | `20260905-142515-24734c` | 8/12 (66.67%) | 3.17 | 2.17 | 3/3, 2/3, 0/3, 3/3 | tool_error 2, missing_required_step 2 |

Evidence: 각 Run의 per-case trace `artifacts/agent-single/`와 raw responses.

## 7. Agent-multi

Dataset SHA-256: `ee9bc5035f9ca17be36a3749e62322d767232570960ae80d3041b2b1741a010a`.

| Model | Run ID | Pass rate | Handoff | Role participation | Avg steps | Avg tool calls | Failure types |
|---|---|---:|---:|---:|---:|---:|---|
| Q5_K_M | `20260905-133949-1338f2` | 7/10 (70.00%) | 100% (10/10) | 100% | 3.70 | 2.70 | tool_error 3 |
| Q6_K | `20260905-140313-a7f044` | 5/10 (50.00%) | 100% | 90% | 4.10 | 3.20 | tool_error 4, missing_role 1 |
| Q8_0 | `20260905-142626-1d94bf` | 7/10 (70.00%) | 100% (10/10) | 100% | 3.80 | 2.80 | tool_error 3 |

수정 후 handoff success rate는 task-level 성공 handoff 수 / expected handoff task 수로 계산한다. 따라서 Q5_K_M은 10/10 = 100%, Q6_K는 9/10 = 90%, Q8_0은 10/10 = 100%다. 기존 세 raw `result.json`에는 역사적 계산 오류인 Q5_K_M/Q8_0 `1.10`이 그대로 남아 있으며, Q6_K의 기존 `1.0`은 동일하다. corrected 재계산 결과는 `runs/full-cycles/ornith15-v1-full-20260905-131958-052758/agent-multi-corrected-summary.json`에 별도 보존했다.

Evidence: 각 Run의 per-case trace `artifacts/agent-multi/`, raw responses, role transitions, events, dataset snapshot.

## 회귀 및 보존 상태

- Backend targeted regression: **33 passed**, 1 기존 Starlette/httpx deprecation warning
- `python3 -m compileall -q app`: passed
- Frontend `npm run build`: passed
- Full `python3 -m pytest tests -q`: 기존 `tests/test_api.py::test_health` 환경 hang 재현, 20초 timeout (`EXIT 124`). 6개 테스트가 시작된 뒤 중단됐다. 이는 21개 benchmark Run 실패와 무관하다.
- 모델별 managed server는 각 Run 종료 후 정리됐다.
- Machine-readable manifest: `runs/full-cycles/ornith15-v1-full-20260905-131958-052758/manifest.json`
