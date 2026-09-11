# Public results interpretation

모델별 결과는 summary와 provenance를 분리합니다. `source_runs`는 원본 run ID만 가리키며, raw trace·환경 파일·개인 경로를 결과 저장소에 복사하지 않습니다.

- Performance: PP/TG microbenchmark
- Server-performance: concurrency별 aggregate/per-request throughput, latency, failure rate
- Knowledge: total/correct/accuracy와 category summary
- Coding: passed/pass rate와 failure type
- Tool-call: selection/argument/execution 지표
- Agent-single: pass rate, steps, tool calls
- Agent-multi: pass rate, handoff, role participation, steps, tool calls

서로 다른 MTP 여부, llama.cpp commit, hardware, evaluator version이 다르면 숫자를 직접 합산하거나 순위를 단정하지 않습니다.
