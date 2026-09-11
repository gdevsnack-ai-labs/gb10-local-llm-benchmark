from __future__ import annotations
import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.runners.base import RunContext
from app.runners.knowledge import KnowledgeRunner
from app.runners.coding import CodingRunner
from app.runners.tool_call import ToolCallRunner
from app.runners.agent_single import AgentSingleRunner
from app.runners.agent_multi import AgentMultiRunner


def make_ctx(tmp_root, config, run_id="test-run"):
    run_dir = tmp_root["run_root"] / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    events = []
    async def emit(t,d):
        events.append((t,d))
    return RunContext(run_id=run_id, run_dir=run_dir, config=config, emit=emit, cancel_event=asyncio.Event()), events


# helpers for mock server
def mock_knowledge_handler(request: httpx.Request):
    # health
    if request.url.path == "/health":
        return httpx.Response(200, json={"status":"ok"})
    if request.url.path == "/completion":
        body = json.loads(request.content) if request.content else {}
        prompt = body.get("prompt","")
        if "대한민국의 수도" in prompt or "서울" in prompt:
            return httpx.Response(200, json={"content":"서울"})
        if "2 + 3 * 4" in prompt:
            return httpx.Response(200, json={"content":"14"})
        if "capital of france" in prompt.lower() or "france" in prompt.lower():
            return httpx.Response(200, json={"content":"Paris"})
        if "물은 몇 도" in prompt or "끓는" in prompt:
            return httpx.Response(200, json={"content":"100"})
        if "60km/h" in prompt or "train" in prompt.lower():
            return httpx.Response(200, json={"content":"120"})
        return httpx.Response(200, json={"content":"unknown"})
    if request.url.path == "/v1/chat/completions":
        body = json.loads(request.content) if request.content else {}
        messages = body.get("messages", [])
        prompt = messages[-1].get("content", "") if messages else ""
        if "대한민국의 수도" in prompt or "서울" in prompt:
            content = "서울"
        elif "2 + 3 * 4" in prompt:
            content = "14"
        elif "capital of france" in prompt.lower() or "france" in prompt.lower():
            content = "Paris"
        elif "물은 몇 도" in prompt or "끓는" in prompt:
            content = "100"
        elif "60km/h" in prompt or "train" in prompt.lower():
            content = "120"
        else:
            content = "unknown"
        return httpx.Response(200, json={"choices":[{"message":{"content":content}}]})
    return httpx.Response(404, json={})

def mock_tool_handler(request: httpx.Request):
    if request.url.path == "/health":
        return httpx.Response(200, json={"status":"ok"})
    if request.url.path == "/v1/chat/completions":
        body = json.loads(request.content) if request.content else {}
        msgs = body.get("messages",[])
        last = msgs[-1].get("content","") if msgs else ""
        tools = body.get("tools",[])
        # decide based on prompt
        if "15 * 23" in last or "calculator" in last and "15" in last:
            # return tool_call for calculator
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"calculator","arguments": json.dumps({"a":15,"b":23,"op":"*"})},"id":"1"}]}}]})
        if "japan_capital" in last:
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"kv_lookup","arguments": json.dumps({"key":"japan_capital"})},"id":"2"}]}}]})
        if "/tmp/data.txt" in last:
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"read_file","arguments": json.dumps({"path":"/tmp/data.txt"})},"id":"3"}]}}]})
        # fallback: try to infer via generic
        if "calculator" in last:
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"calculator","arguments": json.dumps({"a":15,"b":23,"op":"*"})},"id":"1"}]}}]})
        return httpx.Response(200, json={"choices":[{"message":{"content":"{\"name\":\"calculator\",\"arguments\":{\"a\":15,\"b\":23,\"op\":\"*\"}}"}}]})
    if request.url.path == "/completion":
        return httpx.Response(200, json={"content":"{\"name\":\"calculator\",\"arguments\":{\"a\":15,\"b\":23,\"op\":\"*\"}}"})
    return httpx.Response(404, json={})

def mock_agent_single_handler(request: httpx.Request):
    if request.url.path == "/health":
        return httpx.Response(200, json={"status":"ok"})
    if request.url.path == "/v1/chat/completions":
        body = json.loads(request.content) if request.content else {}
        msgs = body.get("messages",[])
        # count tool messages to decide step
        tool_msgs = [m for m in msgs if m.get("role")=="tool"]
        if len(tool_msgs) == 0:
            # first call: infer intent
            last_user = msgs[-1].get("content","") if msgs else ""
            if "15*23" in last_user or "15 * 23" in last_user:
                return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"calculator","arguments": json.dumps({"a":15,"b":23,"op":"*"})},"id":"a1"}]}}]})
            if "japan_capital" in last_user:
                return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"kv_lookup","arguments": json.dumps({"key":"japan_capital"})},"id":"a1"}]}}]})
            if "/tmp/data.txt" in last_user:
                return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"read_file","arguments": json.dumps({"path":"/tmp/data.txt"})},"id":"a1"}]}}]})
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"calculator","arguments": json.dumps({"a":15,"b":23,"op":"*"})},"id":"a1"}]}}]})
        elif len(tool_msgs) == 1:
            # second step -> calculator second op or final
            # check first tool was calculator 345
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"calculator","arguments": json.dumps({"a":345,"b":7,"op":"+"})},"id":"a2"}]}}]})
        else:
            return httpx.Response(200, json={"choices":[{"message":{"content":"FINAL: 352"}}]})
    return httpx.Response(404, json={})

def mock_agent_multi_handler(request: httpx.Request):
    if request.url.path == "/health":
        return httpx.Response(200, json={"status":"ok"})
    if request.url.path == "/v1/chat/completions":
        body = json.loads(request.content) if request.content else {}
        msgs = body.get("messages",[])
        tool_msgs = [m for m in msgs if m.get("role")=="tool"]
        if len(tool_msgs) == 0:
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"kv_lookup","arguments": json.dumps({"key":"japan_capital"})},"id":"m1"}]}}]})
        elif len(tool_msgs) == 1:
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"kv_lookup","arguments": json.dumps({"key":"france_capital"})},"id":"m2"}]}}]})
        elif len(tool_msgs) == 2:
            return httpx.Response(200, json={"choices":[{"message":{"tool_calls":[{"type":"function","function":{"name":"calculator","arguments": json.dumps({"a":5,"b":5,"op":"+"})},"id":"m3"}]}}]})
        else:
            return httpx.Response(200, json={"choices":[{"message":{"content":"FINAL: 10"}}]})
    return httpx.Response(404, json={})


@pytest.mark.asyncio
async def test_knowledge_runner(tmp_root, mock_httpx):
    mock_httpx(mock_knowledge_handler)
    ctx, _ = make_ctx(tmp_root, {"dataset":"data/knowledge/sample-v1.jsonl","server_url":"http://test"})
    runner = KnowledgeRunner()
    result = await runner.run(ctx)
    assert result["total"] == 5
    assert "pass_rate" in result
    assert result["correct"] >= 1

@pytest.mark.asyncio
async def test_coding_runner(tmp_root, mock_httpx):
    # coding calls chat completions returning python code that passes tests
    def handler(req: httpx.Request):
        if req.url.path == "/health":
            return httpx.Response(200, json={"status":"ok"})
        if req.url.path == "/v1/chat/completions":
            # return code for add(a,b)
            code = "def add(a,b):\n    return a+b\n"
            return httpx.Response(200, json={"choices":[{"message":{"content": f"```python\n{code}\n```"}}]})
        if req.url.path == "/completion":
            return httpx.Response(200, json={"content":"def add(a,b): return a+b"})
        return httpx.Response(404, json={})
    mock_httpx(handler)
    ctx, _ = make_ctx(tmp_root, {"dataset":"data/coding/sample-v1.jsonl","server_url":"http://test"}, run_id="codetest")
    runner = CodingRunner()
    result = await runner.run(ctx)
    assert result["total"] == 3
    assert "pass_rate" in result

@pytest.mark.asyncio
async def test_tool_call_runner(tmp_root, mock_httpx):
    mock_httpx(mock_tool_handler)
    ctx, _ = make_ctx(tmp_root, {"dataset":"data/tool/sample-v1.jsonl","server_url":"http://test"}, run_id="tooltest")
    runner = ToolCallRunner()
    result = await runner.run(ctx)
    assert result["total"] == 3
    assert result["tool_rate"] == 1.0

@pytest.mark.asyncio
async def test_agent_single_runner(tmp_root, mock_httpx):
    mock_httpx(mock_agent_single_handler)
    ctx, _ = make_ctx(tmp_root, {"dataset":"data/agent/single-v1.jsonl","server_url":"http://test","max_steps":4}, run_id="agent-single-test")
    runner = AgentSingleRunner()
    result = await runner.run(ctx)
    assert result["total"] == 3
    assert result["pass_rate"] >= 0.33

@pytest.mark.asyncio
async def test_agent_multi_runner(tmp_root, mock_httpx):
    mock_httpx(mock_agent_multi_handler)
    ctx, _ = make_ctx(tmp_root, {"dataset":"data/agent/multi-v1.jsonl","server_url":"http://test","max_steps":6}, run_id="agent-multi-test")
    runner = AgentMultiRunner()
    result = await runner.run(ctx)
    assert result["total"] == 3
    assert "handoffs" in result

@pytest.mark.asyncio
async def test_runner_health_failure(tmp_root, mock_httpx):
    def handler(req: httpx.Request):
        return httpx.Response(500, json={})
    mock_httpx(handler)
    ctx, _ = make_ctx(tmp_root, {"dataset":"data/knowledge/sample-v1.jsonl","server_url":"http://test"})
    runner = KnowledgeRunner()
    with pytest.raises(RuntimeError, match="server health failed"):
        await runner.run(ctx)
