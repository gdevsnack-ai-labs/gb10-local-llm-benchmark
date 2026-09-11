from __future__ import annotations
import json
import time

def test_export_json(app_client):
    c = app_client["client"]
    # create a simple run that will complete fast (use knowledge but mock not needed: create manual run dir)
    # Instead create run via API then check export after polling
    r = c.post("/api/runs", json={"suite":"knowledge","config":{"dataset":"data/knowledge/sample-v1.jsonl"}})
    rid = r.json()["id"]
    # wait briefly for fail (no server) -> should still export json
    time.sleep(0.6)
    # export json should work even for failed
    er = c.get(f"/api/runs/{rid}/export?format=json")
    assert er.status_code == 200
    j = er.json()
    assert "manifest" in j
    assert "environment" in j

def test_export_csv_markdown_methodology(app_client):
    c = app_client["client"]
    r = c.post("/api/runs", json={"suite":"knowledge","config":{}})
    rid = r.json()["id"]
    time.sleep(0.2)
    for fmt in ["csv","markdown","methodology"]:
        er = c.get(f"/api/runs/{rid}/export?format={fmt}")
        assert er.status_code == 200, f"{fmt} failed {er.text[:200]}"
        assert len(er.text) > 10

def test_export_zip(app_client):
    c = app_client["client"]
    r = c.post("/api/runs", json={"suite":"knowledge","config":{}})
    rid = r.json()["id"]
    time.sleep(0.2)
    er = c.get(f"/api/runs/{rid}/export?format=zip")
    assert er.status_code == 200
    assert er.headers["content-type"] == "application/zip"
    assert len(er.content) > 500

def test_methodology_endpoint(app_client):
    c = app_client["client"]
    r = c.post("/api/runs", json={"suite":"knowledge","config":{}})
    rid = r.json()["id"]
    time.sleep(0.2)
    er = c.get(f"/api/runs/{rid}/methodology")
    assert er.status_code == 200
    assert "Methodology" in er.text

def test_export_not_found(app_client):
    c = app_client["client"]
    assert c.get("/api/runs/not-exist/export?format=json").status_code == 404

def test_export_invalid_format(app_client):
    c = app_client["client"]
    r = c.post("/api/runs", json={"suite":"knowledge","config":{}})
    rid = r.json()["id"]
    assert c.get(f"/api/runs/{rid}/export?format=bad").status_code == 400
