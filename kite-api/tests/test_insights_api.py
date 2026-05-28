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
    def test_all_five_lists_returned(self, client):
        r = client.get("/api/insights/watchlists?limit=5")
        b = r.json()
        expected = {"breakouts", "rs_leaders", "coiled_springs",
                    "stretched", "recent_breakdowns"}
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


# ---------- caching ----------

class TestCacheHeaders:
    @pytest.mark.parametrize("path", [
        "/api/insights/reading",
        "/api/insights/stress/timeseries?days=20",
        "/api/insights/sectors",
        "/api/insights/analogs?k=3",
        "/api/insights/watchlists?limit=3",
    ])
    def test_cache_control_header_set(self, client, path):
        r = client.get(path)
        cc = r.headers.get("Cache-Control", "")
        assert "max-age=" in cc, f"{path}: no Cache-Control max-age header (got {cc!r})"
        assert "public" in cc
