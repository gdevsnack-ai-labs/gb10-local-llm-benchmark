# Coding Benchmark v1

## 목적

Coding suite를 고정 dataset과 실제 Python 코드 생성 및 pytest 평가로 재현 가능하게 실행한다. v1은 대규모 leaderboard가 아니라 플랫폼 실행 경로와 artifact 보존을 검증하는 소규모 정식 benchmark다.

총 12문항으로 `basic`, `string`, `collection`, `edge_case` 4개 category가 각각 3문항씩 구성된다. dataset은 [coding-v1.jsonl](../../datasets/coding-v1/coding-v1.jsonl) version 1이며 recipe는 `../../recipes/coding-v1.yaml`이다.

각 문제에서 생성 코드를 workspace에 저장하고 pytest를 실행한다. 전체/category별 total, passed, pass rate와 문제별 pass/fail을 기록하며 실패는 `extraction_error`, `syntax_error`, `test_failure`, `runtime_error`, `timeout`으로 분류한다.

run에는 recipe/config/manifest/environment/result/events와 dataset snapshot/hash가 남고, 문제별 prompt/task spec, generated source, pytest test file, stdout/stderr, 결과 metadata가 `artifacts/coding/<task-id>/`에 저장된다.

현재 평가는 process workspace isolation과 timeout 수준의 제한된 실행 환경이다. 동일 recipe와 dataset으로 모델 간 비교를 수행하며, dataset을 확장하거나 의미 있게 변경할 때는 version을 올린다.
