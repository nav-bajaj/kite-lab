"""Spec for `analyse_stock_rs` — the production-sourced per-stock RS handler.

The handler feeds content dossiers, and a wrong number or a wrong date in a
dossier becomes a wrong number in a published reel. Two behaviours are
load-bearing enough to pin down:

1. Facts carry PRODUCTION's as-of date, not the requested one, and a mismatch
   is surfaced rather than swallowed.
2. `sector_rank` / `sector_size` never reach the dossier — rs_rank reports a
   stock's best rank across all its sectors without naming which sector won,
   so two stocks in one sector can carry different denominators.

The API is stubbed; these tests make no network call.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import analyse_topic  # noqa: E402


STOCK_PAYLOADS = {
    "SBIN": {
        "data_available": True,
        "row": {"symbol": "SBIN", "date": "2026-08-14", "rank": 173,
                "percentile": 64.46, "rs_score": 0.6027,
                "ret_3m": 0.1071, "ret_12m": 0.3245,
                "above_200dma": True, "dist_200dma_pct": 0.0328,
                "sector_rank": 4, "sector_size": 20},
    },
    "HDFCBANK": {
        "data_available": True,
        "row": {"symbol": "HDFCBANK", "date": "2026-08-14", "rank": 458,
                "percentile": 5.6, "rs_score": 0.1236,
                "ret_3m": -0.0528, "ret_12m": -0.2676,
                "above_200dma": False, "dist_200dma_pct": -0.1570,
                "sector_rank": 14, "sector_size": 14},
    },
}

SECTORS_PAYLOAD = {
    "sector_rs": {
        "NIFTY_BANK": {"date": "2026-08-14", "rs_60d": 0.043469, "rank_60d": 5},
    }
}


@pytest.fixture
def stub_api(monkeypatch):
    """Route the handler's fetches to fixtures; fail loudly on a real call."""
    def _fetch(path: str, timeout: int = 90):
        if path == "/api/insights/sectors":
            return SECTORS_PAYLOAD
        for symbol, payload in STOCK_PAYLOADS.items():
            if path.endswith(f"/stocks/{symbol}"):
                return payload
        raise AssertionError(f"unexpected API path: {path}")
    monkeypatch.setattr(analyse_topic, "_fetch_json", _fetch)


def test_resolves_spoken_names_and_bare_symbols():
    got = analyse_topic.symbols_in("relative strength of SBI vs HDFC Bank and KOTAKBANK")
    assert got == ["HDFCBANK", "SBIN", "KOTAKBANK"] or set(got) == {
        "HDFCBANK", "SBIN", "KOTAKBANK"}


def test_no_symbols_named_yields_no_facts(stub_api):
    out = analyse_topic.analyse_stock_rs("relative strength generally", "2026-08-16")
    assert out["verified_facts"] == []
    assert out["confidence"] == "low"


def test_facts_carry_production_asof_not_requested(stub_api):
    out = analyse_topic.analyse_stock_rs("relative strength of SBI", "2026-08-16")
    rank_facts = [f for f in out["verified_facts"] if f["source"].endswith(".rank")]
    assert rank_facts, "expected a rank fact"
    assert "2026-08-14" in rank_facts[0]["fact"]
    assert "2026-08-16" not in rank_facts[0]["fact"]


def test_asof_mismatch_is_surfaced(stub_api):
    out = analyse_topic.analyse_stock_rs("relative strength of SBI", "2026-08-16")
    joined = " ".join(out["related_signals"])
    assert "2026-08-14" in joined and "2026-08-16" in joined


def test_matching_asof_raises_no_mismatch_warning(stub_api):
    out = analyse_topic.analyse_stock_rs("relative strength of SBI", "2026-08-14")
    assert not any("not the requested" in s for s in out["related_signals"])


def test_sector_rank_never_reaches_the_dossier(stub_api):
    out = analyse_topic.analyse_stock_rs(
        "relative strength of SBI and HDFC Bank", "2026-08-14")
    blob = repr(out["verified_facts"]) + repr(out["data_points"])
    assert "sector_rank" not in blob
    # 14/14 and 4/20 are the incomparable denominators; neither may appear.
    assert "14/14" not in blob and "4/20" not in blob


def test_rank_and_returns_are_reported_verbatim(stub_api):
    out = analyse_topic.analyse_stock_rs("relative strength of SBI", "2026-08-14")
    by_source = {f["source"].rsplit(".", 1)[-1]: f for f in out["verified_facts"]}
    assert by_source["rank"]["value"] == 173
    assert by_source["ret_12m"]["value"] == pytest.approx(0.3245)
    assert "+32.5%" in by_source["ret_12m"]["fact"]


def test_sector_context_is_relative_to_the_nifty(stub_api):
    out = analyse_topic.analyse_stock_rs(
        "relative strength of SBI in the bank sector", "2026-08-14")
    sector_facts = [f for f in out["verified_facts"] if "sectors." in f["source"]]
    assert sector_facts, "expected sector context when a sector is named"
    assert "+4.3%" in sector_facts[0]["fact"]
    assert "Nifty" in sector_facts[0]["fact"]


def test_a_dead_symbol_does_not_kill_the_batch(stub_api, monkeypatch, capsys):
    def _fetch(path: str, timeout: int = 90):
        if path.endswith("/stocks/HDFCBANK"):
            raise RuntimeError("503")
        if path == "/api/insights/sectors":
            return SECTORS_PAYLOAD
        return STOCK_PAYLOADS["SBIN"]
    monkeypatch.setattr(analyse_topic, "_fetch_json", _fetch)
    out = analyse_topic.analyse_stock_rs(
        "relative strength of SBI and HDFC Bank", "2026-08-14")
    assert any(f["value"] == 173 for f in out["verified_facts"])
    assert "HDFCBANK" in capsys.readouterr().err


def test_own_trend_state_is_reported_for_the_momentum_contrast(stub_api):
    out = analyse_topic.analyse_stock_rs("relative strength of SBI", "2026-08-14")
    trend = [f for f in out["verified_facts"] if f["source"].endswith(".above_200dma")]
    assert trend, "expected the 200-DMA own-trend fact"
    assert "above its 200-day average" in trend[0]["fact"]
    assert "3.3%" in trend[0]["fact"]


def test_production_supersedes_local_sector_rs(stub_api):
    """The dossier must never carry two numbers for one metric."""
    out = analyse_topic.analyse_stock_rs(
        "relative strength of SBI in the bank sector", "2026-08-14")
    assert "sector_rs" in out["supersedes"]


def test_nothing_is_superseded_when_the_handler_found_nothing(stub_api):
    out = analyse_topic.analyse_stock_rs("relative strength generally", "2026-08-14")
    assert out["supersedes"] == []


def test_handler_is_registered_and_routed():
    assert analyse_topic.HANDLERS["analyse_stock_rs"] is analyse_topic.analyse_stock_rs
    categories = [r.category for r in analyse_topic.route("relative strength of SBI")]
    assert "stock_rs" in categories
