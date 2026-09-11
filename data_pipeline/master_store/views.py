"""Derived views of the store. The engines read <MASTER>/panels/<view>/<SYMBOL>_day.csv; those are relative symlinks into
prices/adjusted_<view>/. The view is not shipped in the store archive (the upload endpoint rejects link members) and is
recreated here, idempotently, by the nightly refresh and by every book runner before it loads panels."""
from __future__ import annotations
import os
from pathlib import Path
from data_pipeline.master_store import MASTER


def ensure_panel_views(master: str | os.PathLike = MASTER) -> int:
    master = Path(master); n = 0
    for view in ("pr", "tr"):
        src = master / f"prices/adjusted_{view}"; dst = master / f"panels/{view}"
        if not src.is_dir():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*.csv"):
            link = dst / f"{f.stem}_day.csv"; target = os.path.relpath(f, dst)
            if link.is_symlink() and os.readlink(link) == target:
                continue
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(target); n += 1
    return n
