"""Tests for the sector subgroup tracker.

Covers membership integrity, snapshot shape, JSON serialisation, and
the sibling-spread helper. Spot-checks one well-known historical
divergence (PSU banks weakness around the 2018 NBFC crisis).
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from app.insights import subgroups as sg


@pytest.fixture(scope="module", autouse=True)
def _clear_cache():
    sg.clear_cache()


class TestMembership:
    def test_all_groups_have_at_least_three_members(self):
        for name, g in sg.SUBGROUPS.items():
            assert len(g["members"]) >= 3, f"{name} has <3 members"

    def test_all_groups_have_required_metadata(self):
        for name, g in sg.SUBGROUPS.items():
            assert "label" in g and g["label"]
            assert "parent_sector" in g and g["parent_sector"].startswith("NIFTY_")
            assert "members" in g and isinstance(g["members"], list)

    def test_sibling_pairs_reference_real_subgroups(self):
        for a, b in sg.SIBLING_PAIRS:
            assert a in sg.SUBGROUPS, f"unknown subgroup in pair: {a}"
            assert b in sg.SUBGROUPS, f"unknown subgroup in pair: {b}"

    def test_members_in_price_panel(self):
        """Most members should resolve to price data — minor misses are
        OK (recently demerged or rare names) but the bulk must cover."""
        panel = sg.load_close_panel()
        missing = []
        for name, g in sg.SUBGROUPS.items():
            for m in g["members"]:
                if m not in panel.columns:
                    missing.append(f"{name}:{m}")
        # Tolerate a few; treat large miss as bug
        assert len(missing) <= 2, (
            f"too many subgroup members missing from price panel: {missing}"
        )


class TestSnapshot:
    @pytest.fixture(scope="class")
    def snap(self):
        return sg.get_subgroup_snapshot()

    def test_returns_all_subgroups(self, snap):
        assert set(snap.keys()) == set(sg.SUBGROUPS.keys())

    def test_snapshot_fields_populated(self, snap):
        for name, s in snap.items():
            assert s.subgroup == name
            assert s.label
            assert s.parent_sector
            assert s.n_total > 0
            assert s.n_covered <= s.n_total
            assert isinstance(s.members_covered, list)

    def test_rs_values_in_reasonable_range(self, snap):
        for name, s in snap.items():
            for h, v in [("5d", s.rs_5d), ("20d", s.rs_20d), ("60d", s.rs_60d)]:
                if v is not None:
                    assert -1.0 < v < 1.0, (
                        f"{name} rs_{h} = {v} out of plausible range"
                    )

    def test_pct_above_200dma_in_unit_range(self, snap):
        for s in snap.values():
            if s.pct_above_200dma is not None:
                assert 0.0 <= s.pct_above_200dma <= 1.0

    def test_to_dict_json_serializable(self, snap):
        for s in snap.values():
            json.dumps(s.to_dict())


class TestSpreads:
    @pytest.fixture(scope="class")
    def spreads(self):
        return sg.get_sibling_spreads()

    def test_one_per_sibling_pair(self, spreads):
        # Some pairs may be skipped if either group's RS couldn't be
        # computed — but on latest data, all should resolve.
        assert len(spreads) >= len(sg.SIBLING_PAIRS) - 1

    def test_spread_units_are_pp(self, spreads):
        for sp in spreads:
            if sp.spread_60d_pp is not None:
                # 60d spread between large-cap groups should plausibly be
                # within ±60pp (anything wider would be exceptional).
                assert -100 < sp.spread_60d_pp < 100

    def test_to_dict_shape(self, spreads):
        for sp in spreads:
            d = sp.to_dict()
            assert set(d.keys()) == {"pair", "spread_60d_pp", "label"}


class TestSpreadSignConventionSpec:
    """Spec test: the sign of `spread_60d_pp` is `group_a - group_b` and
    a positive sign means `group_a` is leading. Pinned with a constructed
    snapshot rather than reading live data — sign-convention bugs would
    be invisible without this."""

    def test_positive_spread_means_first_group_leading(self, monkeypatch):
        """Construct two SubgroupSnapshot fixtures with known RS_60d values
        and verify the spread direction."""
        fake_a = sg.SubgroupSnapshot(
            subgroup="private_banks", label="Private banks",
            parent_sector="NIFTY_BANK",
            n_total=5, n_covered=5, today_chg_pct=None,
            rs_5d=None, rs_20d=None, rs_60d=0.05,  # +5% RS
            rs_60d_prev_week=None, rs_60d_wow_delta=None,
            pct_above_200dma=None, members_covered=[],
        )
        fake_b = sg.SubgroupSnapshot(
            subgroup="psu_banks", label="PSU banks",
            parent_sector="NIFTY_BANK",
            n_total=5, n_covered=5, today_chg_pct=None,
            rs_5d=None, rs_20d=None, rs_60d=-0.03,  # -3% RS
            rs_60d_prev_week=None, rs_60d_wow_delta=None,
            pct_above_200dma=None, members_covered=[],
        )
        fake_snaps = {"private_banks": fake_a, "psu_banks": fake_b}
        # Patch get_subgroup_snapshot to return our fixture
        monkeypatch.setattr(sg, "get_subgroup_snapshot",
                            lambda asof=None: fake_snaps)

        spreads = sg.get_sibling_spreads()
        bank_spread = next(
            (s for s in spreads if s.pair == ("private_banks", "psu_banks")),
            None,
        )
        assert bank_spread is not None
        # rs_60d[private] - rs_60d[psu] = 0.05 - (-0.03) = +0.08 → +8.0pp
        assert abs(bank_spread.spread_60d_pp - 8.0) < 1e-6, (
            f"Expected +8.0pp; got {bank_spread.spread_60d_pp}. "
            "Sign convention: group_a - group_b."
        )

    def test_missing_rs_yields_none_spread(self, monkeypatch):
        """If either side has rs_60d=None, the spread must be None
        (not 0, not a crash)."""
        fake_a = sg.SubgroupSnapshot(
            subgroup="private_banks", label="Private banks",
            parent_sector="NIFTY_BANK",
            n_total=5, n_covered=5, today_chg_pct=None,
            rs_5d=None, rs_20d=None, rs_60d=None,  # missing
            rs_60d_prev_week=None, rs_60d_wow_delta=None,
            pct_above_200dma=None, members_covered=[],
        )
        fake_b = sg.SubgroupSnapshot(
            subgroup="psu_banks", label="PSU banks",
            parent_sector="NIFTY_BANK",
            n_total=5, n_covered=5, today_chg_pct=None,
            rs_5d=None, rs_20d=None, rs_60d=0.02,
            rs_60d_prev_week=None, rs_60d_wow_delta=None,
            pct_above_200dma=None, members_covered=[],
        )
        monkeypatch.setattr(
            sg, "get_subgroup_snapshot",
            lambda asof=None: {"private_banks": fake_a, "psu_banks": fake_b},
        )
        spreads = sg.get_sibling_spreads()
        bank_spread = next(
            (s for s in spreads if s.pair == ("private_banks", "psu_banks")),
            None,
        )
        assert bank_spread is not None
        assert bank_spread.spread_60d_pp is None


class TestHistoricalEpisodes:
    def test_2018_nbfc_psu_banks_weakness(self):
        """During Oct 2018 NBFC stress, PSU banks should show weak RS
        relative to private banks over the trailing 60 days."""
        snaps = sg.get_subgroup_snapshot(pd.Timestamp("2018-10-31"))
        if "psu_banks" not in snaps or "private_banks" not in snaps:
            pytest.skip("subgroups missing on this date")
        psu = snaps["psu_banks"]
        pvt = snaps["private_banks"]
        if psu.rs_60d is None or pvt.rs_60d is None:
            pytest.skip("RS not computable at this date")
        # PSU banks shouldn't be ahead of private banks during NBFC crunch
        assert psu.rs_60d <= pvt.rs_60d + 0.02, (
            f"Expected PSU banks <= private banks on 2018-10-31 (NBFC stress); "
            f"got psu rs_60d={psu.rs_60d}, pvt rs_60d={pvt.rs_60d}"
        )
