from __future__ import annotations
import json
import time

def test_persisted_events(app_client):
    c = app_client["client"]
    r = c.post("/api/runs", json={"suite":"knowledge","config":{}})
    rid = r.json()["id"]
    time.sleep(0.6)
    # history
    hr = c.get(f"/api/runs/{rid}/events/history?limit=100")
    assert hr.status_code == 200
    lst = hr.json()
    assert isinstance(lst, list)
    assert len(lst) >= 1
    assert any(e["type"]=="status" for e in lst)

def test_queue_after_create(app_client):
    c = app_client["client"]
    # create long running via performance (no model -> will fail quickly but still queue)
    r1 = c.post("/api/runs", json={"suite":"performance","config":{"model_path":"/tmp/fake.gguf"}})
    r2 = c.post("/api/runs", json={"suite":"performance","config":{"model_path":"/tmp/fake2.gguf"}})
    q = c.get("/api/queue").json()
    assert "queued" in q
    assert "total" in q

def test_cancel(app_client):
    c = app_client["client"]
    r = c.post("/api/runs", json={"suite":"performance","config":{"model_path":"/tmp/fake.gguf"}})
    rid = r.json()["id"]
    cr = c.post(f"/api/runs/{rid}/cancel")
    # may be queued or running -> 200 or 400
    assert cr.status_code in (200,400)

def test_compare_flow(app_client):
    c = app_client["client"]
    r1 = c.post("/api/runs", json={"suite":"knowledge","config":{}}).json()
    r2 = c.post("/api/runs", json={"suite":"knowledge","config":{}}).json()
    time.sleep(0.3)
    cr = c.post("/api/compare", json={"run_ids":[r1["id"], r2["id"]]})
    assert cr.status_code == 200
    j = cr.json()
    assert "table" in j
    assert len(j["table"]) == 2
