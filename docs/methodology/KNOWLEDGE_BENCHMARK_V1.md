# Knowledge Benchmark v1

## 목적

Knowledge suite를 동일한 실행 경로와 자동 채점 규칙으로 재현 가능하게 실행하고, 모델 간 결과를 비교할 수 있도록 고정한다. v1은 모델 능력의 종합 순위표가 아니라 플랫폼 실행 경로 validation을 위한 소규모 정식 benchmark다.

## Dataset

총 25문항이며 `general`, `korea`, `math`, `science`, `logic` 5개 category가 각각 5문항씩 포함된다. dataset은 [knowledge-v1.jsonl](../../datasets/knowledge-v1/knowledge-v1.jsonl) version 1이며, recipe는 `../../recipes/knowledge-v1.yaml`에 정의되어 있다.

## Scoring

- `multiple_choice`: 응답에서 실제 choice id를 추출해 expected choice id와 비교한다.
- `numeric`: 응답의 숫자를 normalization한 뒤 expected 숫자와 비교한다.
- `exact_match`: trim, casefold, whitespace normalization 후 비교한다.

LLM-as-a-judge는 사용하지 않는다. 전체 및 category별 total, correct, accuracy를 기록한다.

## Evidence and comparison rule

각 run에는 `recipe.yaml`, `resolved-config.yaml`, `manifest.json`, `environment.json`, `result.json`, `events.jsonl`, `samples.jsonl`, dataset snapshot이 저장된다. `result.json`과 문제별 evidence에는 dataset path/version/SHA-256, raw response, normalized answer, expected answer, scoring type, pass/fail이 포함된다.

모델 간 비교는 반드시 동일한 recipe와 동일한 dataset을 사용하고, 각 run의 환경·설정·raw evidence를 함께 검토한다. v1 dataset은 플랫폼 안정화용 소규모 정식 dataset이며, 향후 문항을 확장하거나 의미 있는 변경을 할 때는 dataset version을 올린다.
