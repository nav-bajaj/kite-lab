"""Derived views of the store. The engines read <MASTER>/panels/<view>/<SYMBOL>_day.csv; those are relative symlinks into
prices/adjusted_<view>/. The view is not shipped in the store archive (the upload endpoint rejects link members) and is
recreated here, idempotently, by the nightly refresh and by every book runner before it loads panels."""
from __future__ import annotations
import os
from pathlib import Path
from data_pipeline.master_store import MASTER

JUNK_PREFIXES = ("._",)
JUNK_NAMES = {".DS_Store"}


def remove_junk_files(master: str | os.PathLike = MASTER) -> int:
    """Delete macOS metadata sidecars (._X, .DS_Store) anywhere under the store. A tar built with BSD tar on a Mac
    carries them as ordinary members; they are not data, and a ._X.csv next to X.csv breaks every glob-based reader
    (first Railway run of mm_v1, 2026-09-12)."""
    n = 0
    for root, _dirs, files in os.walk(master):
        for name in files:
            if name.startswith(JUNK_PREFIXES) or name in JUNK_NAMES:
                Path(root, name).unlink(); n += 1
    return n


def ensure_panel_views(master: str | os.PathLike = MASTER) -> int:
    master = Path(master); n = 0
    for view in ("pr", "tr"):               # stale links to sidecars from an earlier view build
        for link in (master / f"panels/{view}").glob("._*"):
            link.unlink(missing_ok=True)
    for view in ("pr", "tr"):
        src = master / f"prices/adjusted_{view}"; dst = master / f"panels/{view}"
        if not src.is_dir():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*.csv"):
            if f.name.startswith("."):      # macOS AppleDouble sidecars (._X.csv) that a hand-built archive can carry
                continue
            link = dst / f"{f.stem}_day.csv"; target = os.path.relpath(f, dst)
            if link.is_symlink() and os.readlink(link) == target:
                continue
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(target); n += 1
    return n
