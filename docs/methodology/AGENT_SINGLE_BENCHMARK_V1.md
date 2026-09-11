# Agent-single Benchmark v1

Agent-single suite에서 한 agent가 여러 단계로 tool을 선택하고 이전 결과를 활용해 task를 완료하는 경로를 재현 가능하게 평가한다. v1은 leaderboard가 아닌 플랫폼 안정화용 소규모 정식 benchmark다.

총 12문항이며 `arithmetic_chain`, `lookup_transform`, `file_transform`, `mixed_task`가 각각 3문항이다. dataset은 [agent-single-v1.jsonl](../../datasets/agent-single-v1/agent-single-v1.jsonl) version 1이고 recipe는 `../../recipes/agent-single-v1.yaml`이다.

task completion, required tool sequence/dependency, final answer, step 수, tool call 수, failed/invalid call, repeated call을 기록한다. 실패는 `wrong_tool`, `wrong_arguments`, `tool_error`, `missing_required_step`, `incomplete_task`, `repeated_loop`, `final_answer_error`, `max_steps_exceeded`로 분류한다.

각 run에는 recipe/config/manifest/environment/result/events와 dataset snapshot/hash가 보존된다. 문제별로 task prompt, raw model responses, ordered agent trace, parsed tool calls/arguments/results, final answer, scoring metadata를 `artifacts/agent-single/<task-id>/`에 저장한다.

실행은 현재 process-local deterministic tool simulator와 max-step 제한을 사용한다. 동일 recipe와 dataset으로 모델 간 비교를 수행하며 dataset 변경·확장 시 version을 올린다.
