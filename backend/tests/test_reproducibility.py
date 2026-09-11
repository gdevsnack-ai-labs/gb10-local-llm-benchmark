from __future__ import annotations

import json
from datetime import datetime, timezone
import io
from pathlib import Path
from unittest.mock import patch
import zipfile

import httpx
import pytest
import yaml

from app.core.config import settings
from app.db.store import Store
from app.models.schemas import RunCreate, RunRecord
from app.runners.coding import run_tests
from app.runners.base import RunContext
from app.runners.server_perf import ServerPerformanceRunner
from app.services.events import EventBus
from app.services.export import build_methodology, build_zip
from app.services.run_manager import RunManager


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RECIPE_ROOT = PROJECT_ROOT / "recipes"


def coding_handler(request: httpx.Request):
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok"})
    if request.url.path == "/v1/chat/completions":
        prompt = json.loads(request.content).get("messages", [{}])[-1].get("content", "")
        if "factorial" in prompt:
            code = "def factorial(n):\n    result = 1\n    for i in range(2, n + 1):\n        result *= i\n    return result\n"
        elif "is_prime" in prompt:
            code = "def is_prime(n):\n    if n <= 1:\n        return False\n    if n <= 3:\n        return True\n    if n % 2 == 0 or n % 3 == 0:\n        return False\n    i = 5\n    while i * i <= n:\n        if n % i == 0 or n % (i + 2) == 0:\n            return False\n        i += 6\n    return True\n"
        else:
            code = "def add(a, b):\n    return a + b\n"
        return httpx.Response(200, json={"choices": [{"message": {"content": f"```python\n{code}```"}}]})
    return httpx.Response(404, json={})


@pytest.mark.asyncio
async def test_coding_recipe_end_to_end_preserves_provenance(tmp_root, mock_httpx):
    mock_httpx(coding_handler)
    with patch.object(settings, "run_root", tmp_root["run_root"]), \
         patch.object(settings, "db_path", tmp_root["db_path"]), \
         patch.object(settings, "recipe_root", RECIPE_ROOT):
        store = Store(tmp_root["db_path"])
        events = EventBus(tmp_root["run_root"])
        manager = RunManager(store, events)
        rec = await manager.create(RunCreate(
            suite="coding",
            recipe="coding-basic-v1.yaml",
            config={"server_url": "http://test"},
        ))
        task = manager.tasks[rec.id]
        await task
        final = store.get(rec.id)
        run_dir = tmp_root["run_root"] / rec.id

    assert final is not None
    assert final.status == "completed"
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["recipe"] == "coding-basic-v1.yaml"
    assert manifest["resolved_config"]["dataset"] == "data/coding/sample-v1.jsonl"
    assert (run_dir / "recipe.yaml").read_text(encoding="utf-8") == (RECIPE_ROOT / "coding-basic-v1.yaml").read_text(encoding="utf-8")
    resolved = yaml.safe_load((run_dir / "resolved-config.yaml").read_text(encoding="utf-8"))
    assert resolved["dataset"] == "data/coding/sample-v1.jsonl"
    assert resolved["server_url"] == "http://test"
    assert (run_dir / "environment.json").exists()
    assert (run_dir / "result.json").exists()
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "samples.jsonl").exists()
    assert (run_dir / "artifacts" / "coding" / "c1" / "solution.py").exists()
    events_read = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines() if line.strip()]
    assert [event["seq"] for event in events_read] == list(range(1, len(events_read) + 1))
    with patch.object(settings, "run_root", tmp_root["run_root"]):
        archive = build_zip(rec.id, final)
    assert archive.startswith(b"PK")
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        names = set(bundle.namelist())
    assert f"{rec.id}/recipe.yaml" in names
    assert f"{rec.id}/resolved-config.yaml" in names


def test_methodology_uses_nested_environment_schema(tmp_path):
    run_root = tmp_path / "runs"
    run_id = "methodology-test"
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(json.dumps({
        "suite": "performance",
        "config": {"n_gpu_layers": 99, "flash_attn": True, "ctx_size": 8192, "batch_size": 2048},
    }), encoding="utf-8")
    (run_dir / "environment.json").write_text(json.dumps({
        "os": {"system": "Linux", "release": "6.17.0", "machine": "aarch64"},
        "arch": "aarch64",
        "cpu": {"physical": 20, "logical": 20},
        "nvidia": "NVIDIA GB10, 590.00, 128000 MiB",
        "llama_bench": {"path": "/opt/llama-bench", "resolved": "/opt/llama-bench", "commit": "abc123", "help_head": "build 10788"},
        "llama_server": {"path": "/opt/llama-server", "resolved": "/opt/llama-server", "version": "build 10788"},
        "platform_commit": "platform123",
        "config": {"n_gpu_layers": 99},
    }), encoding="utf-8")
    (run_dir / "result.json").write_text("{}", encoding="utf-8")
    record = RunRecord(
        id=run_id,
        suite="performance",
        status="completed",
        recipe="performance-smoke.yaml",
        config={"n_gpu_layers": 99, "flash_attn": True, "ctx_size": 8192, "batch_size": 2048},
        created_at=datetime.now(timezone.utc),
    )
    with patch.object(settings, "run_root", run_root):
        methodology = build_methodology(run_id, record)
    assert "/opt/llama-bench" in methodology
    assert "/opt/llama-server" in methodology
    assert "NVIDIA GB10" in methodology
    assert "20 physical / 20 logical" in methodology
    assert "abc123" in methodology
    assert "n_gpu_layers=99" in methodology
    assert "ctx_size=8192" in methodology


def test_new_store_does_not_create_unused_run_events_table(tmp_root):
    store = Store(tmp_root["db_path"])
    store.conn.commit()
    names = {row[0] for row in store.conn.execute("select name from sqlite_master where type='table'")}
    assert "run_events" not in names


def test_all_coding_recipes_reference_existing_fixture():
    for recipe_name in ("coding-basic-v1.yaml", "coding-spec-ngram-v1.yaml", "coding-spec-off-v1.yaml"):
        recipe = yaml.safe_load((RECIPE_ROOT / recipe_name).read_text(encoding="utf-8"))
        dataset = recipe["config"]["dataset"]
        assert dataset == "data/coding/sample-v1.jsonl"
        assert (PROJECT_ROOT / dataset).is_file()


def test_coding_evaluator_uses_backend_interpreter(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.setenv("PATH", str(tmp_path))
    result = run_tests(
        workspace,
        "def test_answer():\n    assert 2 + 2 == 4\n",
        timeout=10,
    )
    assert result["success"] is True, result["output"]


@pytest.mark.asyncio
async def test_server_performance_persists_samples(tmp_path, mock_httpx):
    def handler(request: httpx.Request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/completion":
            return httpx.Response(200, json={
                "timings": {
                    "prompt_n": 4,
                    "prompt_ms": 10,
                    "prompt_per_second": 400,
                    "predicted_n": 4,
                    "predicted_ms": 20,
                    "predicted_per_second": 200,
                }
            })
        return httpx.Response(404, json={})

    mock_httpx(handler)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ctx = RunContext(
        run_id="server-sample-test",
        run_dir=run_dir,
        config={"server_url": "http://test", "concurrency": 1, "requests": 1, "gen_tokens": 4, "prompt": "test"},
        emit=lambda _event_type, _data: __import__("asyncio").sleep(0),
    )
    result = await ServerPerformanceRunner().run(ctx)
    assert result["requests"] == 1
    samples = run_dir / "samples.jsonl"
    assert samples.exists()
    assert len([line for line in samples.read_text().splitlines() if line.strip()]) == 1


def test_server_performance_v1_recipe_defines_formal_matrix():
    recipe = yaml.safe_load((RECIPE_ROOT / "server-performance-v1.yaml").read_text(encoding="utf-8"))
    assert recipe["suite"] == "server-performance"
    config = recipe["config"]
    assert config["concurrencies"] == [1, 2, 4, 8]
    assert config["requests_per_concurrency"] == 4
    assert config["repetitions"] == 3
    assert config["gen_tokens"] == 512
    assert config["parallel"] == 8


@pytest.mark.asyncio
async def test_server_performance_v1_matrix_preserves_repetitions_and_raw_samples(tmp_path, mock_httpx):
    def handler(request: httpx.Request):
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/completion":
            return httpx.Response(200, json={"timings": {"predicted_n": 4, "predicted_per_second": 200, "prompt_n": 2, "prompt_per_second": 100}})
        return httpx.Response(404, json={})

    mock_httpx(handler)
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    ctx = RunContext(
        run_id="server-formal-test", run_dir=run_dir,
        config={"server_url": "http://test", "concurrencies": [1, 2, 4, 8], "requests_per_concurrency": 4, "repetitions": 3, "gen_tokens": 4, "prompt": "test"},
        emit=lambda _event_type, _data: __import__("asyncio").sleep(0),
    )
    result = await ServerPerformanceRunner().run(ctx)
    assert [x["concurrency"] for x in result["conditions"]] == [1, 2, 4, 8]
    assert all(x["repetitions"] == 3 and x["requests_per_repetition"] == c * 4 for c, x in zip([1, 2, 4, 8], result["conditions"]))
    assert all(len(x["repetitions_raw"]) == 3 for x in result["conditions"])
    assert all(len(rep["samples"]) == c * 4 for c in [1, 2, 4, 8] for rep in next(x["repetitions_raw"] for x in result["conditions"] if x["concurrency"] == c))
    assert result["samples_count"] == 180
    assert len(run_dir.joinpath("samples.jsonl").read_text().splitlines()) == 180
