from __future__ import annotations
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import bind
from app.db.store import Store
from app.services.events import EventBus
from app.services.run_manager import RunManager
from app.core.config import settings


@pytest.fixture()
def tmp_root(tmp_path):
    run_root = tmp_path / "runs"
    run_root.mkdir()
    db_path = tmp_path / "test.db"
    return {"tmp_path": tmp_path, "run_root": run_root, "db_path": db_path}


@pytest.fixture()
def app_client(tmp_root):
    # patch settings run_root/db_path for isolation
    with patch.object(settings, "run_root", tmp_root["run_root"]), \
         patch.object(settings, "db_path", tmp_root["db_path"]), \
         patch.object(settings, "recipe_root", Path(__file__).resolve().parents[2] / "recipes"):
        store = Store(tmp_root["db_path"])
        events = EventBus(tmp_root["run_root"])
        manager = RunManager(store, events)
        # ensure presets
        for name, cfg in [("basic", {"spec":"off"}),("ngram", {"spec_type":"ngram"})]:
            store.upsert_preset(name, cfg)
        app = FastAPI()
        app.include_router(bind(store, manager, events), prefix="/api")
        client = TestClient(app)
        yield {"client": client, "store": store, "events": events, "manager": manager, "tmp_root": tmp_root}


@pytest.fixture()
def mock_httpx(monkeypatch):
    """Provide a helper to patch httpx.AsyncClient with MockTransport."""
    import httpx
    def _make(handler):
        transport = httpx.MockTransport(handler)
        original = httpx.AsyncClient
        def fake_client(*args, **kwargs):
            # force our transport, allow base_url/timeout passthrough
            kwargs["transport"] = transport
            return original(*args, **kwargs)
        monkeypatch.setattr(httpx, "AsyncClient", fake_client)
        return transport
    return _make
