"""production_port_2026 P2: the rebuilt books (mm_v1, om25_v4) are registered consistently everywhere the legacy books are,
and their locked configs match tasks/mm_rebuild/MECHANICS.md."""
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "kite-api"))

BOOKS = ("mm_v1", "om25_v4")


def test_registered_everywhere():
    from app.config import UNIVERSES, ALL_UNIVERSES
    from app.services.sync_service import UNIVERSE_DIRS
    from scripts.sync_validation import RUN_DIR_GLOBS
    from app.services.freshness_service import _PORTFOLIO_UNIVERSES
    from app.services.metrics_service import _BENCHMARK
    sh = (ROOT / "scripts/init_persistent_storage.sh").read_text()
    ts = (ROOT / "kite-dashboard/src/lib/universes.ts").read_text()
    types = (ROOT / "kite-dashboard/src/lib/types.ts").read_text()
    upd = (ROOT / "scripts/update_all_portfolios.py").read_text()
    for b in BOOKS:
        assert b in UNIVERSES and b in ALL_UNIVERSES
        assert UNIVERSES[b]["portfolio_dir"] == f"data/{b}_portfolios"
        assert UNIVERSES[b]["rebalance_cadence"] == "monthly_first"
        assert UNIVERSE_DIRS[b] == (f"data/{b}_portfolios", f"{b}_portfolio_202*")
        assert RUN_DIR_GLOBS[b] == (f"data/{b}_portfolios", f"{b}_portfolio_")
        assert b in dict(_PORTFOLIO_UNIVERSES) and _BENCHMARK[b][1] == "Nifty 250"
        assert f'link "$VOLUME/{b}_portfolios"' in sh and f'mkdir -p "$VOLUME/{b}_portfolios"' in sh
        assert f'"{b}"' in types and f"  {b}: {{" in ts
        assert re.search(rf'{b}:\s*\{{[^}}]*clientVisible:\s*false', ts), f"{b} must be admin-only until P5 sign-off"
        assert f'"--book", "{b}"' in upd


def test_admin_only_by_default():
    from app.auth import CLIENT_VISIBLE_UNIVERSES
    for b in BOOKS:
        assert b not in CLIENT_VISIBLE_UNIVERSES


def test_locked_configs_match_mechanics():
    from scripts.rebuilt_books import LOCKED, BOOKS as RB
    assert RB == BOOKS
    for b in BOOKS:
        c = LOCKED[b]
        assert (c["universe"], c["lookback"], c["top_n"], c["exit_buffer"], c["skip"]) == ("nifty250", 252, 25, 20, 21)
        assert (c["sizing"], c["iv_window"], c["max_weight"], c["sector_cap"]) == ("invvol", 63, 0.10, 5)
        assert (c["regime_index"], c["roc_n"], c["confirm"], c["bear_n"], c["bear_buffer"]) == ("NIFTY_100", 31, 3, 15, 20)
        assert (c["trailing_stop"], c["stop_check"], c["cadence"], c["rebalance_day"], c["fill_from_buffer"]) == (0.20, "monthly", "monthly", 1, True)
        assert c["lock_date"] == "2026-09-11"
    assert LOCKED["mm_v1"]["score"] == "voladj" and LOCKED["mm_v1"]["min_obs"] == 219
    assert LOCKED["om25_v4"]["score"] == "mix" and LOCKED["om25_v4"]["mix_w"] == 0.5 and LOCKED["om25_v4"]["min_obs"] == 220


def test_monthly_cadence_projection():
    from datetime import date
    from app.services.rebalance_service import project_next_signal, expected_cadence_history
    nxt = project_next_signal(date(2026, 9, 1), "monthly_first", date(2026, 9, 12))
    assert nxt == date(2026, 10, 1)   # 1 Oct 2026 is a Thursday and a trading day
    hist = expected_cadence_history(today=date(2026, 9, 12), anchor_exec=date(2026, 9, 2), cadence_key="monthly_first", lookback_count=3)
    assert [s for s, _ in hist] == [date(2026, 9, 1), date(2026, 8, 3), date(2026, 7, 1)]
    assert all(e > s for s, e in hist)


def test_store_backed_price_dir(monkeypatch, tmp_path):
    from app.config import price_dir, STORE_BACKED_UNIVERSES, settings
    assert set(STORE_BACKED_UNIVERSES) == set(BOOKS)
    monkeypatch.setenv("MASTER_STORE_DIR", str(tmp_path / "master"))
    for b in BOOKS:
        assert price_dir(b) == tmp_path / "master" / "panels" / "pr"
    assert price_dir("l6_v2") == settings.data_dir / "nse500_data"
    monkeypatch.delenv("MASTER_STORE_DIR")
    assert price_dir("mm_v1") == settings.data_dir / "data" / "master" / "panels" / "pr"
