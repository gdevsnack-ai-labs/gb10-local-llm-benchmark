# Agent-multi Benchmark v1

여러 agent가 Researcher와 Calculator 역할을 나누고 이전 결과를 handoff로 전달해 task를 완료하는 경로를 재현 가능하게 평가한다. v1은 대규모 leaderboard가 아닌 플랫폼 실행 경로 안정화용 소규모 정식 benchmark다.

총 10문항이며 `lookup_calculate` 3, `file_calculate` 2, `mixed_handoff` 3, `role_dependency` 2로 구성된다. dataset은 [agent-multi-v1.jsonl](../../datasets/agent-multi-v1/agent-multi-v1.jsonl) version 1이고 recipe는 `../../recipes/agent-multi-v1.yaml`이다.

task completion, required role participation, handoff 및 context transfer, required tool sequence, final answer, total steps/tool calls, failed/invalid calls를 기록한다. 실패는 `missing_role`, `handoff_failure`, `context_transfer_failure`, `wrong_tool`, `wrong_arguments`, `tool_error`, `missing_required_step`, `incomplete_task`, `repeated_loop`, `final_answer_error`, `max_steps_exceeded`로 분류한다.

각 run에는 recipe/config/manifest/environment/result/events와 dataset snapshot/hash가 보존된다. 문제별로 task prompt, raw model responses, ordered multi-agent trace, role transition/handoff payload, parsed tool calls/results, final answer, scoring metadata를 `artifacts/agent-multi/<task-id>/`에 저장한다.

동일 recipe와 dataset으로 모델 간 비교를 수행하며 dataset 변경·확장 시 version을 올린다.
