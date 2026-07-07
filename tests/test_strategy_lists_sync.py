"""Guard against the multi-file strategy-list drift (audit O6/T-14).

``app.config.EOD_STRATEGIES`` is the canonical list of the 4 client v3
portfolios with an EOD producer. The scheduler imports it directly; the CLI
keeps a local copy (so it stays importable without the API package on the
path). This test asserts they can't silently diverge.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kite-api"))

from app.config import EOD_STRATEGIES, ALL_UNIVERSES, UNIVERSES
from app.scheduler.tasks import EOD_STRATEGIES as TASKS_STRATEGIES
from scripts.run_eod_proposed_orders import _STRATEGIES as CLI_STRATEGIES


def test_scheduler_reuses_the_canonical_list():
    # Imported, not re-declared — identical object.
    assert TASKS_STRATEGIES is EOD_STRATEGIES


def test_cli_choices_match_canonical():
    assert tuple(sorted(CLI_STRATEGIES)) == tuple(sorted(EOD_STRATEGIES))


def test_all_universes_covers_config():
    assert set(ALL_UNIVERSES) == set(UNIVERSES.keys())


def test_eod_strategies_are_real_universes():
    for s in EOD_STRATEGIES:
        assert s in ALL_UNIVERSES, s
