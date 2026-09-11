from __future__ import annotations
import re
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from app.db.store import Store

QUANT_PAT = re.compile(r"(Q\d+_K_M|Q\d+_K_L|Q\d+_K_S|Q\d+_0|Q\d+_K_XL|IQ\d+_\w+|BF16|F16|Q8_0|Q6_K|Q5_K_M|Q4_K_M|Q4_K_S|Q4_0|NVFP4|UD-|Ridge|DFlash|GSQ|mmproj)", re.I)
FAMILY_PAT = re.compile(r"(qwen|gemma|deepseek|nemotron|step|minimax|ornith)", re.I)

def infer_quant(name: str) -> str | None:
    m = QUANT_PAT.search(name)
    return m.group(1) if m else None

def infer_family(name: str) -> str | None:
    m = FAMILY_PAT.search(name)
    return m.group(1).lower() if m else None

def infer_tags(path: Path) -> list[str]:
    tags = []
    name = path.name.lower()
    # speculative type
    if "mtp" in name:
        tags.append("mtp")
    if "dflash" in name:
        tags.append("dflash")
    if "ngram" in name:
        tags.append("ngram")
    if "mmproj" in name:
        tags.append("mmproj")
    # quant category
    q = infer_quant(path.name)
    if q:
        tags.append(q.lower())
    fam = infer_family(path.name)
    if fam:
        tags.append(fam)
    # directory hint
    for part in path.parts:
        pl = part.lower()
        if pl in ("qwen3.6-35b-a3b","qwen3.8-27b","gemma4","deepseek","nemotron"):
            if pl not in tags:
                tags.append(pl)
    return sorted(set(tags))

def scan_ggufs(root: Path, store: Store, compute_sha: bool = False) -> dict:
    found = []
    # find all .gguf
    for p in root.rglob("*.gguf"):
        try:
            st = p.stat()
            # shard grouping: if file contains -00001-of-
            # treat each shard as separate variant for now, but add group tag
            quant = infer_quant(p.name)
            family = infer_family(p.name)
            tags = infer_tags(p)
            # display name: parent dir + filename
            display = f"{p.parent.name}/{p.name}" if len(p.parts) >=2 else p.name
            sha = None
            if compute_sha and st.st_size < 100*1024*1024:  # only small files
                try:
                    h = hashlib.sha256()
                    with open(p, "rb") as f:
                        for chunk in iter(lambda: f.read(8192*1024), b""):
                            h.update(chunk)
                    sha = h.hexdigest()
                except Exception:
                    pass
            store.upsert_variant(
                path=str(p),
                file_size=st.st_size,
                mtime=datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                quantization=quant,
                family=family,
                tags=tags,
                display_name=display,
                sha256=sha,
            )
            found.append(str(p))
        except Exception:
            continue
    # cleanup missing
    store.delete_missing_variants(found)
    return {"scanned": len(found), "root": str(root)}
