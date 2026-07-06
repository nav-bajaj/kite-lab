"""Guard the Railway persistence symlink script (audit O3).

``scripts/init_persistent_storage.sh`` hand-lists mkdir + link pairs. History
shows this drifts: a new data dir gets created but never linked (or linked to a
path nothing writes to — the indices_data bug), so data silently vanishes on the
next redeploy. These tests parse the script and assert the invariants that
prevent that, driving the strategy-portfolio dirs off the live EOD_STRATEGIES
list so adding a strategy without persisting its runs fails here.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.scheduler.tasks import EOD_STRATEGIES

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "init_persistent_storage.sh"
TEXT = SCRIPT.read_text()

MKDIRS = set(re.findall(r'mkdir -p "\$VOLUME/([^"]+)"', TEXT))
LINKS = {  # src (under $VOLUME) -> dst (under $APP)
    src: dst
    for src, dst in re.findall(r'link "\$VOLUME/([^"]+)"\s+"\$APP/([^"]+)"', TEXT)
}


def test_every_linked_source_is_created_in_volume():
    # A symlink whose volume target was never mkdir'd points at nothing —
    # data written through it is lost. (Files like tokens/access_token.txt are
    # created via touch, so restrict this to directory links.)
    dir_link_srcs = {s for s in LINKS if not s.endswith((".txt", ".csv", ".json"))}
    missing = sorted(dir_link_srcs - MKDIRS)
    assert not missing, f"linked but never created in volume: {missing}"


def test_each_eod_strategy_portfolio_dir_is_persisted():
    # Adding an EOD strategy without persisting its <strategy>_portfolios run
    # dir means its daily runs die on every redeploy and producers can't find a
    # completed run. Force the symlink to exist.
    for strategy in EOD_STRATEGIES:
        src = f"{strategy}_portfolios"
        assert src in LINKS, f"{src} not symlinked in init_persistent_storage.sh"
        assert LINKS[src] == f"data/{strategy}_portfolios", (
            f"{src} links to {LINKS[src]!r}, expected data/{strategy}_portfolios"
        )


def test_critical_data_dirs_are_persisted():
    # The dirs the daily pipeline + EOD producers actually read/write.
    expected = {
        "nse500_data": "nse500_data",
        # Regression: fetch_indices_history.py writes to /app/indices_data, so
        # the link dst MUST be app-root indices_data, not data/indices_data
        # (the old target that caught nothing).
        "indices_data": "indices_data",
        "benchmarks": "data/benchmarks",
        "instruments": "data/instruments",
    }
    for src, dst in expected.items():
        assert src in LINKS, f"{src} not symlinked"
        assert LINKS[src] == dst, f"{src} links to {LINKS[src]!r}, expected {dst}"
