from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app.runners.base import RunContext
from app.runners.server_perf import ServerPerformanceRunner


@pytest.mark.asyncio
async def test_server_performance_thinking_mode_uses_chat_and_records_reasoning(tmp_root, mock_httpx):
    seen: list[dict] = []

    def handler(request: httpx.Request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/slots":
            return httpx.Response(200, json=[])
        if request.url.path == "/metrics":
            return httpx.Response(200, text="metrics")
        if request.url.path == "/v1/chat/completions":
            body = json.loads(request.content)
            seen.append(body)
            return httpx.Response(200, json={
                "choices": [{"message": {
                    "content": "answer",
                    "reasoning_content": "long thought",
                }}],
                "timings": {
                    "prompt_n": 3,
                    "prompt_ms": 10,
                    "prompt_per_second": 300,
                    "predicted_n": 6,
                    "predicted_ms": 20,
                    "predicted_per_second": 300,
                    "reasoning_n": 4,
                },
            })
        return httpx.Response(404)

    mock_httpx(handler)
    run_dir = tmp_root["run_root"] / "thinking-server"
    run_dir.mkdir(parents=True)
    events = []

    async def emit(kind, data):
        events.append((kind, data))

    ctx = RunContext(
        run_id="thinking-server",
        run_dir=run_dir,
        config={
            "server_url": "http://test",
            "thinking_mode": "think",
            "thinking_budget": 2048,
            "request_timeout_s": 17,
            "requests": 1,
            "concurrency": 1,
            "gen_tokens": 64,
        },
        emit=emit,
        cancel_event=asyncio.Event(),
    )
    result = await ServerPerformanceRunner().run(ctx)

    assert seen[0]["chat_template_kwargs"] == {"enable_thinking": True}
    assert result["thinking_mode"] == "think"
    assert result["thinking_budget"] == 2048
    assert result["request_timeout_s"] == 17
    assert result["reasoning_tokens_total"] == 4
    sample = json.loads((run_dir / "samples.jsonl").read_text().splitlines()[0])
    assert sample["reasoning_chars"] == len("long thought")
    assert sample["output"] == "answer"
