"""The panel view and the panel loader ignore macOS AppleDouble sidecars (._X.csv), and the nightly removes them."""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline.master_store.views import ensure_panel_views, remove_junk_files
from data_pipeline.loaders import load_price_panels


def _store(tmp_path: Path) -> Path:
    src = tmp_path / "prices/adjusted_pr"; src.mkdir(parents=True)
    pd.DataFrame({"date": ["2026-01-01", "2026-01-02"], "open": [1, 2], "high": [1, 2], "low": [1, 2], "close": [1.0, 2.0]}).to_csv(src / "ABC.csv", index=False)
    (src / "._ABC.csv").write_bytes(b"\x00\x05\x16\x07" + b"\xa3" * 60)
    (tmp_path / ".DS_Store").write_bytes(b"junk")
    return tmp_path


def test_view_skips_sidecars_and_loader_reads(tmp_path):
    master = _store(tmp_path)
    assert ensure_panel_views(master) == 1
    names = sorted(p.name for p in (master / "panels/pr").iterdir())
    assert names == ["ABC_day.csv"]
    close, _ = load_price_panels(master / "panels/pr")
    assert list(close.columns) == ["ABC"] and len(close) == 2


def test_loader_ignores_a_stale_sidecar_link(tmp_path):
    master = _store(tmp_path); ensure_panel_views(master)
    (master / "panels/pr/._ABC_day.csv").write_bytes(b"\xa3" * 50)
    close, _ = load_price_panels(master / "panels/pr")
    assert list(close.columns) == ["ABC"]
    ensure_panel_views(master)
    assert not (master / "panels/pr/._ABC_day.csv").exists()


def test_remove_junk_files(tmp_path):
    master = _store(tmp_path)
    assert remove_junk_files(master) == 2
    assert (master / "prices/adjusted_pr/ABC.csv").exists()
    assert remove_junk_files(master) == 0
