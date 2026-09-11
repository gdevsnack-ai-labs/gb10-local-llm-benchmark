from __future__ import annotations
import json
import time

def test_health(app_client):
    c = app_client["client"]
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_system(app_client):
    r = app_client["client"].get("/api/system")
    assert r.status_code == 200
    j = r.json()
    assert "platform" in j
    assert "memory_total" in j

def test_recipes(app_client):
    r = app_client["client"].get("/api/recipes")
    assert r.status_code == 200
    lst = r.json()
    assert isinstance(lst, list)
    assert any(x["name"] == "knowledge-sample-v1.yaml" for x in lst)

def test_models_and_presets(app_client):
    c = app_client["client"]
    assert c.get("/api/models").status_code == 200
    assert c.get("/api/presets").status_code == 200
    # create preset
    r = c.post("/api/presets", json={"name":"test-preset","config":{"foo":1}})
    assert r.status_code == 200
    lst = c.get("/api/presets").json()
    assert any(p["name"]=="test-preset" for p in lst)

def test_queue_empty(app_client):
    r = app_client["client"].get("/api/queue")
    assert r.status_code == 200
    assert "queued" in r.json()

def test_create_run_validation(app_client):
    c = app_client["client"]
    # missing suite
    r = c.post("/api/runs", json={"suite":"","config":{}})
    assert r.status_code in (400,422)
    # unknown suite
    r = c.post("/api/runs", json={"suite":"unknown-suite","config":{}})
    # will be 202 then fail async; but we test sync validation for recipe not found
    r = c.post("/api/runs", json={"suite":"knowledge","recipe":"not-exist.yaml","config":{}})
    assert r.status_code == 400

def test_create_run_queued(app_client):
    c = app_client["client"]
    r = c.post("/api/runs", json={"suite":"knowledge","config":{"dataset":"data/knowledge/sample-v1.jsonl"}})
    # knowledge without server will fail later, but creation should be 202
    assert r.status_code == 202
    rid = r.json()["id"]
    # list
    lst = c.get("/api/runs").json()
    assert any(x["id"]==rid for x in lst)
    # get single
    assert c.get(f"/api/runs/{rid}").status_code == 200
    # artifacts list exists
    time.sleep(0.3)
    assert c.get(f"/api/runs/{rid}/artifacts").status_code == 200

def test_compare_validation(app_client):
    c = app_client["client"]
    r = c.post("/api/compare", json={"run_ids":[]})
    assert r.status_code == 400
    # need at least 2
    r = c.post("/api/compare", json={"run_ids":["a","b"]})
    assert r.status_code == 404  # not found

def test_artifact_traversal_guard(app_client):
    c = app_client["client"]
    r = c.post("/api/runs", json={"suite":"knowledge","config":{}})
    rid = r.json()["id"]
    # traversal
    assert c.get(f"/api/runs/{rid}/artifacts/../../etc/passwd").status_code in (400,404)

def test_server_status(app_client):
    r = app_client["client"].get("/api/server/status")
    assert r.status_code == 200
    assert "managed" in r.json()
