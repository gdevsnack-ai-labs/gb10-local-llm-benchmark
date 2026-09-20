# Public benchmark data

이 디렉터리는 향후 별도 `gb10-llm-benchmark-data` repository로 분리할 수 있는 공개 결과 영역입니다. summary, cycle manifest, evaluator/version/provenance metadata만 저장하며 `runs/`의 raw artifact 전체를 복사하지 않습니다.

- `index.json`: 공개 파일과 schema 버전
- `models/`: 모델별 또는 cycle별 요약 결과
- `cycles/`: 공개 cycle manifest
- `methodology.json`: canonical evaluator와 dataset hash
- `schema.json`: 모델별 summary의 공개 필드 계약
- `releases/gb10-local-llm-benchmark.json`: 최신 32개 모델 변형 통합 projection
- `releases/gb10-local-llm-benchmark.manifest.json`: 최신 projection hash와 source/count manifest
- `releases/gb10-llm-benchmark-v1-20260906.json`: 18개 모델 × 7개 suite의 sanitized immutable public release
- `releases/gb10-llm-benchmark-v1-20260906.manifest.json`: release hash와 source/count manifest

경로는 상대 경로 또는 run ID만 사용하며 개인의 모델 저장소·llama.cpp 경로를 기록하지 않습니다.

2026-09-06 immutable release의 `72 revalidated evaluator runs`는 Knowledge·Tool-call·Agent-single·Agent-multi 4개 evaluator를 18개 모델에 다시 실행한 수입니다. Performance·Server-performance·Coding은 기존 정식 source run 54개를 재사용했으며, 해당 historical matrix의 source run reference는 126개입니다. 현재 projection에는 2026-09-10 N2.5 Mini 4개 variant의 28개 fresh full-cycle run, 2026-09-16~2026-09-17 Laguna S 2.1과 Laguna XS 2.1의 35개 fresh full-cycle run, 2026-09-18 Occamy 1.0 네 variant의 28개 Standard full-cycle run, 그리고 N2/N2.5 Mini 8개·Occamy 1.0 4개·Laguna S 2.1 1개·Laguna XS 2.1 네 variant의 외부 `tool-eval-bench` 실행 17개가 추가되어 총 32개 모델 변형·8개 suite·91개 fresh full-cycle run·241개 source run reference가 있습니다.

현재 공개 projection은 날짜별 benchmark detail 페이지를 추가하지 않고 `gb10-local-llm-benchmark.json`을 최신 상태로 갱신합니다. 모델군 제품군 페이지는 이 projection에서 파생되며, 같은 모델의 새 양자화·MTP/non-MTP 결과는 기존 제품군 URL의 variant matrix를 갱신합니다. 2026-09-10에는 N2.5 Mini 4개 variant의 non-MTP full-cycle 결과를 추가했고, 2026-09-16에는 N2/N2.5 Mini 8개 variant의 외부 `tool-eval-bench` 결과를 별도 suite로 추가했습니다. raw run·manifest·log·source evidence는 기존 run directory에 immutable하게 보존합니다.
