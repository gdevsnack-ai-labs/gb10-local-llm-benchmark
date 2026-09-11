from app.runners.reasoning import (
    build_chat_payload,
    build_server_reasoning_args,
    extract_chat_message,
    normalize_thinking_config,
)


def test_normalize_thinking_modes_and_default_budgets():
    assert normalize_thinking_config({"thinking_mode": "think"}).mode == "think"
    assert normalize_thinking_config({"thinking_mode": "think"}).budget == -1
    assert normalize_thinking_config({"thinking_mode": "no-think"}).mode == "no-think"
    assert normalize_thinking_config({"thinking_mode": "no-think"}).budget == 0
    assert normalize_thinking_config({"thinking_mode": "auto"}).mode == "auto"
    assert normalize_thinking_config({"thinking_mode": "auto"}).budget == -1


def test_reasoning_mode_aliases_and_validation():
    assert normalize_thinking_config({"reasoning": "on"}).mode == "think"
    assert normalize_thinking_config({"reasoning": "off"}).mode == "no-think"

    try:
        normalize_thinking_config({"thinking_mode": "sometimes"})
    except ValueError as exc:
        assert "thinking_mode" in str(exc)
    else:
        raise AssertionError("invalid thinking mode must fail")


def test_server_args_pin_reasoning_mode_and_budget():
    assert build_server_reasoning_args({"thinking_mode": "think", "thinking_budget": 2048}) == [
        "--reasoning", "on", "--reasoning-format", "deepseek", "--reasoning-budget", "2048"
    ]
    assert build_server_reasoning_args({"thinking_mode": "no-think"}) == [
        "--reasoning", "off", "--reasoning-format", "deepseek", "--reasoning-budget", "0"
    ]
    assert build_server_reasoning_args({"thinking_mode": "auto"}) == []


def test_chat_payload_carries_external_thinking_control():
    payload = build_chat_payload(
        [{"role": "user", "content": "answer"}],
        {"thinking_mode": "no-think", "thinking_budget": 0},
        max_tokens=256,
        temperature=0,
    )
    assert payload["max_tokens"] == 256
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert "thinking_mode" not in payload
    assert "thinking_budget" not in payload


def test_extract_chat_message_handles_unbalanced_think_marker():
    answer, reasoning, _ = extract_chat_message({
        "choices": [{"message": {"content": "internal reasoning</think>\nfinal answer"}}],
    })
    assert reasoning == "internal reasoning"
    assert answer == "final answer"


def test_chat_payload_omits_mode_override_for_auto():
    payload = build_chat_payload(
        [{"role": "user", "content": "answer"}],
        {"thinking_mode": "auto"},
        max_tokens=64,
        temperature=0,
    )
    assert "chat_template_kwargs" not in payload
