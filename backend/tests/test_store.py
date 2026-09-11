from pathlib import Path
from tempfile import TemporaryDirectory
from app.db.store import Store
from app.models.schemas import RunCreate


def test_store_roundtrip():
    with TemporaryDirectory() as td:
        s = Store(Path(td) / "x.db")
        s.create_run("r1", RunCreate(suite="performance", config={"x": 1}))
        got = s.get("r1")
        assert got is not None
        assert got.config["x"] == 1
