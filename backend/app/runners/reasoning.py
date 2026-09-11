from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast


ThinkingMode = Literal["auto", "think", "no-think"]


@dataclass(frozen=True)
class ThinkingConfig:
    mode: ThinkingMode
    budget: int
    request_timeout_s: float


def normalize_thinking_config(config: dict[str, Any] | None) -> ThinkingConfig:
    """Normalize benchmark reasoning controls without changing endpoint payloads."""
    c = config or {}
    raw = c.get("thinking_mode")
    if raw is None:
        raw = c.get("reasoning", "auto")
    value = str(raw).strip().lower().replace("_", "-")
    aliases = {
        "on": "think",
        "true": "think",
        "yes": "think",
        "enabled": "think",
        "off": "no-think",
        "false": "no-think",
        "no": "no-think",
        "disabled": "no-think",
        "nothink": "no-think",
        "no-think": "no-think",
        "think": "think",
        "auto": "auto",
    }
    mode = aliases.get(value)
    if mode is None:
        raise ValueError("thinking_mode must be one of: auto, think, no-think")

    budget_raw = c.get("thinking_budget", c.get("reasoning_budget"))
    if budget_raw is None:
        budget = -1 if mode in ("think", "auto") else 0
    else:
        try:
            budget = int(budget_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("thinking_budget must be an integer >= -1") from exc
    if budget < -1:
        raise ValueError("thinking_budget must be >= -1")

    timeout_raw = c.get("request_timeout_s", c.get("timeout_s", 300))
    try:
        request_timeout_s = float(timeout_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("request_timeout_s must be a positive number") from exc
    if request_timeout_s <= 0:
        raise ValueError("request_timeout_s must be a positive number")

    return ThinkingConfig(mode=cast(ThinkingMode, mode), budget=budget, request_timeout_s=request_timeout_s)


def build_server_reasoning_args(config: dict[str, Any] | None) -> list[str]:
    """Build llama-server flags for managed think/no-think runs."""
    thinking = normalize_thinking_config(config)
    if thinking.mode == "auto":
        return []
    return [
        "--reasoning",
        "on" if thinking.mode == "think" else "off",
        "--reasoning-format",
        "deepseek",
        "--reasoning-budget",
        str(thinking.budget),
    ]


def build_chat_payload(
    messages: list[dict[str, Any]],
    config: dict[str, Any] | None,
    *,
    max_tokens: int,
    temperature: float,
    tools: list[dict[str, Any]] | None = None,
    tool_choice: Any | None = None,
) -> dict[str, Any]:
    """Build an OpenAI-compatible request with external template control."""
    thinking = normalize_thinking_config(config)
    payload: dict[str, Any] = {
        "model": "test",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": int(max_tokens),
    }
    if tools is not None:
        payload["tools"] = tools
    if tool_choice is not None:
        payload["tool_choice"] = tool_choice
    if thinking.mode != "auto":
        payload["chat_template_kwargs"] = {"enable_thinking": thinking.mode == "think"}
    return payload


def extract_chat_message(body: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Return answer text, reasoning text, and the raw assistant message."""
    choices = body.get("choices") or []
    if not choices:
        return "", "", {}
    message = choices[0].get("message") or {}
    answer = str(message.get("content") or "")
    reasoning = str(message.get("reasoning_content") or "")

    if not reasoning:
        if "<think>" in answer:
            before, marker, after = answer.partition("<think>")
            if marker and "</think>" in after:
                reasoning, _, answer_after = after.partition("</think>")
                answer = (before + answer_after).strip()
        elif "</think>" in answer:
            reasoning, _, answer = answer.partition("</think>")
            answer = answer.strip()
        elif answer.lstrip().startswith("<think>"):
            _, _, reasoning = answer.partition("<think>")
            answer = ""
    return answer.strip(), reasoning.strip(), message


def extract_reasoning_tokens(body: dict[str, Any]) -> int | None:
    """Read provider-native reasoning token usage when the endpoint exposes it."""
    candidates = [
        body.get("reasoning_tokens"),
        (body.get("usage") or {}).get("reasoning_tokens"),
        ((body.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens"),
        (body.get("timings") or {}).get("reasoning_n"),
    ]
    for value in candidates:
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    return None


def thinking_metadata(config: dict[str, Any] | None) -> dict[str, Any]:
    thinking = normalize_thinking_config(config)
    return {
        "thinking_mode": thinking.mode,
        "thinking_budget": thinking.budget,
        "request_timeout_s": thinking.request_timeout_s,
    }
