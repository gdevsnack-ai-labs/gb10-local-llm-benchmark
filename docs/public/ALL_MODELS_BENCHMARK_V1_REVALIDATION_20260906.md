# GB10 LLM Benchmark v1 통합 재검증 결과

## 범위

2026-09-06 기준으로 6개 모델군, 18개 모델 변형을 통합 정리한 문서다.

- Performance / Server-performance / Coding: 기존 유효 run 재사용
- Knowledge: `knowledge-v1.2.yaml`, 100문제, reasoning OFF, budget 0
- Tool-call / Agent-single / Agent-multi: v1.1 evaluator recipe, reasoning OFF, budget 0
- 기존 historical run은 수정하지 않았으며, 이번 단계의 evaluator run만 새로 추가했다.
- 모든 새 run의 raw response, event, resolved config, environment, result는 `runs/<run-id>/`에 보존됐다.

기존 성능 계측 및 원본 full-cycle 결과는 다음 문서에 있다.

- [Ornith 1.5 original cycle](ORNITH15_FULL_BENCHMARK_V1.md)
- [North Mini original cycle](NORTH_MINI_FULL_BENCHMARK_V1.md)
- [N2 Mini original cycle](N2MINI_FULL_BENCHMARK_V1.md)
- [Gemma4 QAT cycle](GEMMA4_QAT_MTP_COMPARISON_V1.md)
- [Qwen3.6 35B original cycle](QWEN36_35B_FULL_BENCHMARK_V1.md)
- [Qwen3.8 Flash original cycle](QWEN38_FLASH_NEXT_IQ4XS_FULL_BENCHMARK_V1.md)

## 통합 evaluator 결과

표의 순서는 `Knowledge / Tool-call / Agent-single / Agent-multi`이며 분모는 각각 `100 / 15 / 12 / 10`이다.

| 모델 | Knowledge v1.2 | Tool-call v1.1 | Agent-single v1.1 | Agent-multi v1.1 |
|---|---:|---:|---:|---:|
| Ornith 1.5 Q5_K_M | 92/100 | 11/15 | 8/12 | 8/10 |
| Ornith 1.5 Q6_K | 94/100 | 11/15 | 10/12 | 8/10 |
| Ornith 1.5 Q8_0 | 93/100 | 11/15 | 9/12 | 9/10 |
| North Mini MXFP4_MOE | 88/100 | 12/15 | 10/12 | 7/10 |
| North Mini UD-Q4_K_M | 90/100 | 9/15 | 11/12 | 7/10 |
| North Mini UD-Q5_K_M | 93/100 | 12/15 | 11/12 | 7/10 |
| North Mini UD-Q6_K_XL | 92/100 | 11/15 | 11/12 | 8/10 |
| N2 Mini UD-Q4_K_M | 91/100 | 9/15 | 7/12 | 5/10 |
| N2 Mini UD-Q5_K_XL | 93/100 | 9/15 | 9/12 | 7/10 |
| N2 Mini Q5_K_M | 92/100 | 8/15 | 6/12 | 6/10 |
| N2 Mini Q6_K | 93/100 | 8/15 | 8/12 | 9/10 |
| Gemma4 QAT NVFP4 | 98/100 | 11/15 | 12/12 | 7/10 |
| Gemma4 QAT Q4_0 | 98/100 | 12/15 | 12/12 | 7/10 |
| Qwen3.6 MTP-HQ | 94/100 | 11/15 | 11/12 | 8/10 |
| Qwen3.6 MTP-TURBO | 94/100 | 11/15 | 7/12 | 8/10 |
| Qwen3.6 Q8_0 | 95/100 | 10/15 | 9/12 | 9/10 |
| Qwen3.6 APEX-I Balanced | 95/100 | 11/15 | 9/12 | 9/10 |
| Qwen3.8 Flash Next UD-IQ4_XS | 98/100 | 10/15 | 4/12 | 4/10 |

## 새 evaluator Run index

### Ornith 1.5

| 모델 | Knowledge | Tool-call | Agent-single | Agent-multi |
|---|---|---|---|---|
| Q5_K_M | `20260906-012545-d5c2ab` | `20260906-005207-3d30c2` | `20260906-005233-6b715b` | `20260906-005319-5297e7` |
| Q6_K | `20260906-012641-3397c7` | `20260906-005517-5ceb4f` | `20260906-005548-c7c4b3` | `20260906-005634-c44293` |
| Q8_0 | `20260906-012743-4222c1` | `20260906-005852-8e3526` | `20260906-005928-9c1a52` | `20260906-010019-112caa` |

### North Mini

| 모델 | Knowledge | Tool-call | Agent-single | Agent-multi |
|---|---|---|---|---|
| MXFP4_MOE | `20260906-012854-b6a868` | `20260906-010242-4406ed` | `20260906-010308-34728b` | `20260906-010349-d84a1c` |
| UD-Q4_K_M | `20260906-012950-ab0899` | `20260906-010527-039740` | `20260906-010558-04371f` | `20260906-010639-645e21` |
| UD-Q5_K_M | `20260906-013046-0c6ff8` | `20260906-010817-3fddf8` | `20260906-010848-ae5c5a` | `20260906-010934-955895` |
| UD-Q6_K_XL | `20260906-013143-e503c0` | `20260906-011127-af54cb` | `20260906-011203-9766e8` | `20260906-011249-c4feed` |

### N2 Mini

| 모델 | Knowledge | Tool-call | Agent-single | Agent-multi |
|---|---|---|---|---|
| UD-Q4_K_M | `20260906-013249-879db0` | `20260906-011407-a27ccc` | `20260906-011438-5c19a8` | `20260906-011519-289ee9` |
| UD-Q5_K_XL | `20260906-013315-178550` | `20260906-011652-d8b541` | `20260906-011723-ef8d8d` | `20260906-011804-db9de7` |
| Q5_K_M | `20260906-013406-4ef35a` | `20260906-011932-b32a24` | `20260906-011958-55657b` | `20260906-012040-fa2694` |
| Q6_K | `20260906-013458-772406` | `20260906-012217-7896f9` | `20260906-012248-967a21` | `20260906-012334-65f1f4` |

### Gemma4, Qwen3.6, Qwen3.8

| 모델 | Knowledge | Tool-call | Agent-single | Agent-multi |
|---|---|---|---|---|
| Gemma4 QAT NVFP4 | `20260906-015332-2d0b6b` | `20260906-015418-4a3ac8` | `20260906-015454-69cbe0` | `20260906-015541-b2872f` |
| Gemma4 QAT Q4_0 | `20260906-015637-2b954c` | `20260906-015713-f535c9` | `20260906-015739-e15da7` | `20260906-015820-d0681f` |
| Qwen3.6 MTP-HQ | `20260906-015907-f823d8` | `20260906-015958-979df7` | `20260906-020019-5e397a` | `20260906-020055-80d568` |
| Qwen3.6 MTP-TURBO | `20260906-020127-747b4b` | `20260906-020213-f0a325` | `20260906-020234-a0eaf2` | `20260906-020305-4be7f9` |
| Qwen3.6 Q8_0 | `20260906-020336-b838f8` | `20260906-020448-943315` | `20260906-020519-378732` | `20260906-020615-282e39` |
| Qwen3.6 APEX-I Balanced | `20260906-020707-041e50` | `20260906-020758-65179b` | `20260906-020824-1d79ba` | `20260906-020910-33d8b1` |
| Qwen3.8 Flash Next UD-IQ4_XS | `20260906-020952-a4ffcc` | `20260906-021203-505271` | `20260906-021420-bc6cfc` | `20260906-021716-919ebc` |

## 실행 및 해석 메모

- 통합 표에 반영한 유효 evaluator run은 총 72개(18 models × 4 suites)이며 모두 `completed`다. Knowledge 설정 보정 전의 11개 superseded run도 historical artifact로 보존돼 실제 추가 디렉터리 수는 83개다.
- Knowledge는 최종 18개 모두 v1.2 recipe의 `max_tokens:128`을 사용했다. 초기 보정 전 Knowledge run은 보존했지만 통합 표에는 포함하지 않았다.
- Qwen3.6 MTP 파일은 managed server가 native MTP를 자동 적용했고, Qwen3.8 multipart는 세 shard를 하나의 모델로 로드했다.
- Gemma4 MTP draft는 기존 Server-performance 전용 비교 결과를 재사용했다. evaluator suite에는 draft model을 적용하지 않았다.
- 성능 수치의 MTP/non-MTP 차이는 Server-performance 원본 문서와 각 run의 `resolved-config.yaml`에서 확인한다.
- 모든 evidence는 `runs/<run-id>/manifest.json`, `recipe.yaml`, `resolved-config.yaml`, `environment.json`, `events.jsonl`, `result.json`, raw artifact에 있다.

## 보존 상태

기존 full-cycle run과 historical raw result는 덮어쓰지 않았다. 이 문서는 기존 성능 측정과 새 evaluator 결과를 연결하는 통합 인덱스이며, 다음 모델군 진행 시 같은 형식으로 확장할 수 있다.
