# Benchmark methodology

이 디렉터리는 7개 suite의 측정 정의, scoring, artifact contract, 제한사항을 보관합니다.

Canonical evaluator는 Performance·Server-performance·Coding의 기존 정식 버전과 Knowledge v1.2, Tool-call v1.1, Agent-single v1.1, Agent-multi v1.1의 조합입니다. 모델 비교는 reasoning OFF를 기준으로 하며, Server-performance는 MTP와 non-MTP를 별도 실행 조건으로 기록합니다.

고정 dataset의 hash와 공개 결과 schema는 [`results-public/methodology.json`](../../results-public/methodology.json)을 참조하세요.
