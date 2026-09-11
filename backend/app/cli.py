from __future__ import annotations
import asyncio
import os
import json
from pathlib import Path
import httpx
import typer
import yaml

app = typer.Typer(help="GB10 LLM benchmark launcher")
BASE = os.environ.get("LLMBENCH_API_BASE", "")


@app.command()
def health(base: str = BASE):
    print(httpx.get(f"{base}/health").json())


@app.command()
def recipes(path: Path = Path("../recipes")):
    for p in sorted(path.glob("*.yaml")):
        doc = yaml.safe_load(p.read_text()) or {}
        print(f"{p.name:32} {doc.get('suite', '-')}")


@app.command("run")
def run_cmd(
    suite: str,
    recipe: str | None = typer.Option(None),
    model_path: str | None = typer.Option(None),
    base: str = typer.Option(BASE),
):
    cfg = {}
    if model_path:
        cfg["model_path"] = model_path
    r = httpx.post(f"{base}/runs", json={"suite": suite, "recipe": recipe, "config": cfg}, timeout=30)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
