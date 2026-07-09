"""Tests for the public /api/insights routes.

Critical: these endpoints must work WITHOUT a Clerk token, since they
power the public acquisition-funnel pages on the dashboard. Tests below
verify both shape and the no-auth requirement.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


# ---------- public-access verification ----------

class TestPublicAccess:
    """The /insights/* routes must be reachable without auth — they're
    the acquisition funnel, public-facing by design."""

    @pytest.mark.parametrize("path", [
        "/api/insights/reading",
        "/api/insights/stress/timeseries?days=20",
        "/api/insights/breadth/timeseries?days=20",
        "/api/insights/sectors",
        "/api/insights/sectors/NIFTY_BANK",
        "/api/insights/analogs?k=5",
        "/api/insights/watchlists?limit=3",
        "/api/insights/watchlists/breakouts",
        "/api/insights/regime/history",
    ])
    def test_route_works_without_auth(self, client, path):
        """No Authorization header sent — must still return 200."""
        r = client.get(path)
        assert r.status_code == 200, (
            f"{path}: expected 200, got {r.status_code} — "
            f"{r.text[:200]}"
        )
        # Should be valid JSON
        body = r.json()
        assert body is not None


# ---------- response shapes ----------

class TestReadingEndpoint:
    def test_returns_full_market_reading_shape(self, client):
        r = client.get("/api/insights/reading")
        b = r.json()
        for key in ("date", "regime", "stress", "breadth", "macro",
                    "sector_breadth", "sector_rs", "sector_leaderboard_60d",
                    "analogs", "analog_distribution", "conditional", "watchlists"):
            assert key in b, f"missing key {key}"

    def test_accepts_historical_date(self, client):
        r = client.get("/api/insights/reading?date=2020-03-23")
        assert r.status_code == 200
        b = r.json()
        # Should snap to the actual data date — at or before requested
        assert b["date"].startswith("2020-03-")
        # COVID crash → STRESS regime
        assert b["regime"]["regime"] == "STRESS"

    def test_rejects_malformed_date(self, client):
        r = client.get("/api/insights/reading?date=not-a-date")
        assert r.status_code == 400


class TestTimeseriesEndpoints:
    def test_stress_timeseries_default_days(self, client):
        r = client.get("/api/insights/stress/timeseries?days=20")
        b = r.json()
        assert "index" in b and "data" in b
        assert len(b["index"]) <= 20
        assert "score" in b["data"]
        assert len(b["data"]["score"]) == len(b["index"])

    def test_stress_timeseries_rejects_bad_days(self, client):
        r = client.get("/api/insights/stress/timeseries?days=2")
        assert r.status_code == 422  # below min 20

    def test_breadth_metrics_filter(self, client):
        r = client.get("/api/insights/breadth/timeseries?days=30&metrics=pct_above_200dma,mcclellan_osc")
        b = r.json()
        assert set(b["data"].keys()) == {"pct_above_200dma", "mcclellan_osc"}

    def test_breadth_unknown_metric_400(self, client):
        r = client.get("/api/insights/breadth/timeseries?days=30&metrics=fake_metric")
        assert r.status_code == 400


class TestSectorsEndpoints:
    def test_all_sectors_present(self, client):
        r = client.get("/api/insights/sectors")
        b = r.json()
        assert len(b["sector_breadth"]) >= 11
        assert len(b["leaderboard_60d"]) >= 10

    def test_leaderboard_sorted_by_rank(self, client):
        b = client.get("/api/insights/sectors").json()
        ranks = [s["rank_60d"] for s in b["leaderboard_60d"]
                 if s["rank_60d"] is not None]
        assert ranks == sorted(ranks)

    def test_single_sector_drill(self, client):
        r = client.get("/api/insights/sectors/NIFTY_BANK")
        b = r.json()
        assert b["sector"] == "NIFTY_BANK"
        assert b["breadth"] is not None
        assert b["rs"] is not None
        assert "timeseries" in b
        # Time series subkeys
        for k in ("breadth", "rs"):
            if k in b["timeseries"]:
                assert "index" in b["timeseries"][k]
                assert "data" in b["timeseries"][k]

    def test_unknown_sector_404(self, client):
        r = client.get("/api/insights/sectors/NIFTY_DOES_NOT_EXIST")
        assert r.status_code == 404


class TestAnalogsEndpoint:
    def test_default_returns_20_matches(self, client):
        r = client.get("/api/insights/analogs")
        b = r.json()
        assert len(b["matches"]) == 20
        assert "distribution" in b

    def test_k_param_respected(self, client):
        r = client.get("/api/insights/analogs?k=7")
        assert len(r.json()["matches"]) == 7

    def test_k_too_high_422(self, client):
        r = client.get("/api/insights/analogs?k=999")
        assert r.status_code == 422


class TestWatchlistsEndpoints:
    def test_all_lists_returned(self, client):
        # Phase 4.2 added 2 validity-tested patterns to the bundled snapshot.
        r = client.get("/api/insights/watchlists?limit=5")
        b = r.json()
        expected = {
            "breakouts", "rs_leaders", "coiled_springs",
            "stretched", "recent_breakdowns",
            "multi_year_breakouts", "sustained_uptrend",
        }
        assert set(b["lists"].keys()) == expected
        for entries in b["lists"].values():
            assert len(entries) <= 5

    def test_single_list_drill(self, client):
        r = client.get("/api/insights/watchlists/rs_leaders?limit=10")
        b = r.json()
        assert b["name"] == "rs_leaders"
        assert len(b["entries"]) <= 10
        if b["entries"]:
            e = b["entries"][0]
            for key in ("symbol", "close", "score", "note", "sectors"):
                assert key in e

    def test_unknown_list_404(self, client):
        r = client.get("/api/insights/watchlists/not_a_list")
        assert r.status_code == 404


class TestRegimeHistoryEndpoint:
    def test_returns_episode_list(self, client):
        b = client.get("/api/insights/regime/history").json()
        assert "episodes" in b
        assert len(b["episodes"]) > 10  # we've seen many regime episodes over 17y
        ep = b["episodes"][0]
        for key in ("regime", "start", "end", "days"):
            assert key in ep
        assert ep["days"] >= 1


# ---------- stock screener + detail (insights_v2 C4) ----------

class TestScreenerEndpoint:
    def test_public_no_auth(self, client):
        r = client.get("/api/insights/screener")
        assert r.status_code == 200

    def test_shape(self, client):
        b = client.get("/api/insights/screener").json()
        assert set(b.keys()) >= {"asof", "data_available", "rows"}
        assert b["data_available"] is True
        assert len(b["rows"]) > 100  # ~NSE 500 minus names lacking a CSV
        row = b["rows"][0]
        # Zipped from metrics + RS + scores + sectors
        for key in ("symbol", "close", "ret_1m", "rank", "percentile",
                    "trend_score", "extension_band", "volume_band",
                    "momentum_consistency", "tags", "sectors"):
            assert key in row, f"screener row missing {key}"
        assert isinstance(row["tags"], list)
        assert isinstance(row["sectors"], list)

    def test_dropped_fields_absent(self, client):
        """Screener row trims raw sub-score inputs (kept on the detail page)."""
        row = client.get("/api/insights/screener").json()["rows"][0]
        for dropped in ("sma_50", "atr_14", "above_50dma", "slope_50dma_20d",
                        "date", "rank_21d_ago"):
            assert dropped not in row, f"{dropped} should be dropped from screener row"

    def test_payload_under_budget(self, client):
        """~500-row payload must stay under the 500 KB contract budget."""
        r = client.get("/api/insights/screener")
        size_kb = len(r.content) / 1024
        assert size_kb < 500, f"screener payload {size_kb:.1f} KB exceeds 500 KB budget"

    def test_accepts_historical_date(self, client):
        b = client.get("/api/insights/screener?date=2020-03-23").json()
        assert b["data_available"] is True
        assert b["asof"].startswith("2020-03-")

    def test_unknown_early_date_degrades_empty(self, client):
        """A date before any data → empty, not a 500."""
        r = client.get("/api/insights/screener?date=1990-01-01")
        assert r.status_code == 200
        b = r.json()
        assert b["data_available"] is False
        assert b["rows"] == []

    def test_rejects_malformed_date(self, client):
        assert client.get("/api/insights/screener?date=nope").status_code == 400

    def test_floats_are_trimmed(self, client):
        """Float precision is trimmed to <=4 decimals for payload size."""
        row = client.get("/api/insights/screener").json()["rows"][0]
        if row.get("ret_1m") is not None:
            s = repr(row["ret_1m"]).split(".")
            if len(s) == 2:
                assert len(s[1]) <= 4


class TestStockDetailEndpoint:
    def _a_symbol(self, client) -> str:
        return client.get("/api/insights/screener").json()["rows"][0]["symbol"]

    def test_public_no_auth(self, client):
        sym = self._a_symbol(client)
        assert client.get(f"/api/insights/stocks/{sym}").status_code == 200

    def test_shape(self, client):
        sym = self._a_symbol(client)
        b = client.get(f"/api/insights/stocks/{sym}").json()
        for key in ("symbol", "data_available", "asof", "row", "series",
                    "rs_rank_history", "peers"):
            assert key in b
        assert b["data_available"] is True
        assert b["row"]["symbol"] == sym
        # Detail row keeps the fields dropped from the screener row
        assert "above_50dma" in b["row"]
        # 1y price/DMA/volume series
        for key in ("dates", "close", "sma_50", "sma_200", "vol_ratio"):
            assert key in b["series"]
        assert len(b["series"]["dates"]) == len(b["series"]["close"])

    def test_rs_history_is_coarse_monthly(self, client):
        sym = self._a_symbol(client)
        hist = client.get(f"/api/insights/stocks/{sym}").json()["rs_rank_history"]
        # ~1y sampled every ~21 trading days → roughly a dozen points, never daily
        assert len(hist) <= 20
        if hist:
            assert {"date", "rank", "percentile"} <= set(hist[0].keys())

    def test_peers_are_ranked_siblings(self, client):
        sym = self._a_symbol(client)
        peers = client.get(f"/api/insights/stocks/{sym}").json()["peers"]
        assert len(peers) <= 5
        for p in peers:
            assert p["symbol"] != sym
            assert {"symbol", "rank", "sector"} <= set(p.keys())
        # Ranked strongest-first
        ranks = [p["rank"] for p in peers]
        assert ranks == sorted(ranks)

    def test_unknown_symbol_404(self, client):
        r = client.get("/api/insights/stocks/NOTAREALTICKER")
        assert r.status_code == 404
        assert "Unknown symbol" in r.json()["detail"]

    def test_accepts_historical_date(self, client):
        sym = self._a_symbol(client)
        b = client.get(f"/api/insights/stocks/{sym}?date=2022-06-17").json()
        assert b["asof"].startswith("2022-06-")


class TestMoversEndpoint:
    def test_public_no_auth(self, client):
        assert client.get("/api/insights/movers").status_code == 200

    def test_shape(self, client):
        b = client.get("/api/insights/movers").json()
        assert b["data_available"] is True
        for key in ("fresh_highs", "fresh_lows", "rs_improvers"):
            assert key in b
        assert "count" in b["fresh_highs"] and "names" in b["fresh_highs"]
        assert len(b["fresh_highs"]["names"]) <= 5
        assert len(b["rs_improvers"]) <= 5
        # RS improvers are observation-only: rank change is a fact
        for e in b["rs_improvers"]:
            assert {"symbol", "rank", "rank_delta_21d"} <= set(e.keys())
            if e["rank_delta_21d"] is not None:
                assert e["rank_delta_21d"] > 0  # improvers moved toward rank 1

    def test_early_date_degrades_empty(self, client):
        b = client.get("/api/insights/movers?date=1990-01-01").json()
        assert b["data_available"] is False
        assert b["fresh_highs"]["count"] == 0


# ---------- caching ----------

class TestCacheHeaders:
    @pytest.mark.parametrize("path", [
        "/api/insights/reading",
        "/api/insights/stress/timeseries?days=20",
        "/api/insights/sectors",
        "/api/insights/analogs?k=3",
        "/api/insights/watchlists?limit=3",
        "/api/insights/screener",
    ])
    def test_cache_control_header_set(self, client, path):
        r = client.get(path)
        cc = r.headers.get("Cache-Control", "")
        assert "max-age=" in cc, f"{path}: no Cache-Control max-age header (got {cc!r})"
        assert "public" in cc
