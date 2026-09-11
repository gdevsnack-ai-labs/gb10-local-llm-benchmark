# Tool-call Benchmark v1

Tool-call suite를 고정 dataset과 deterministic tool simulator로 재현 가능하게 실행한다. v1은 대규모 function-calling leaderboard가 아니라 실행 경로 안정화용 소규모 정식 benchmark다.

총 15문항이며 `single_tool` 5, `tool_selection` 3, `multi_step` 3, `recovery` 2, `no_tool` 2로 구성된다. dataset은 [tool-call-v1.jsonl](../../datasets/tool-call-v1/tool-call-v1.jsonl) version 1이며 recipe는 `../../recipes/tool-call-v1.yaml`이다.

tool 선택, arguments, execution 성공, final task 성공을 각각 채점한다. multi-step은 expected sequence와 dependency, recovery는 오류 후 재시도 경로, no-tool은 불필요한 호출이 없는지를 확인한다. 실패는 `wrong_tool`, `wrong_arguments`, `execution_error`, `missing_tool_call`, `unnecessary_tool_call`, `incomplete_sequence`, `final_answer_error`로 분류한다.

run에는 recipe/config/manifest/environment/result/events와 dataset snapshot/hash가 보존된다. 문제별로 prompt/task, raw model response, parsed tool calls와 arguments, tool execution result, final answer, scoring metadata를 `artifacts/tool-call/<task-id>/`에 저장한다.

동일 recipe와 dataset으로 모델 간 비교를 수행하며 dataset을 변경하거나 확장할 때는 version을 올린다.
