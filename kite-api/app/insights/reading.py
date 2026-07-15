"""Unified MarketReading — the top-level data object the Daily Quant Note
generator consumes.

Pulls outputs from every Phase 0 module into one structured snapshot for
the requested date. Designed so Phase 1 templates can render any section
of the Note by reading attributes off a single object rather than calling
8 different modules.

For API responses, `to_dict()` returns a fully JSON-serializable nested
dict — every component already implements `to_dict()`.

The reading is computed lazily and cached at the module level via the
underlying modules' own LRU caches. First call after a data refresh
takes ~3-5 seconds (rebuilds all panels); subsequent calls are <100ms.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import pandas as pd

from app.insights import (
    analog_finder,
    breadth,
    calendar_content,
    concentration,
    conditional_dist,
    cross_asset,
    macro,
    regime as regime_mod,
    rs_rank,
    scores as scores_mod,
    sector_breadth,
    sector_rs,
    stock_metrics,
    stress,
    subgroups,
    watchlists,
    zerodha_sectors,
)


@dataclass
class MarketReading:
    """The unified market reading for one date.

    Every component is already a dataclass or dict from its source
    module; this is purely a container that simplifies downstream
    consumption.
    """
    date: pd.Timestamp

    # Headline (lead the Daily Quant Note with these)
    regime: regime_mod.RegimeSnapshot
    stress: stress.StressSnapshot

    # Breadth — full row of the breadth panel for the date (dict of metrics)
    breadth: dict[str, float | None]
    macro: dict[str, float | None]

    # Sector views (constituent-level breadth + index-level RS)
    sector_breadth: dict[str, sector_breadth.SectorBreadthSnapshot]
    sector_rs: dict[str, sector_rs.SectorRSSnapshot]
    sector_leaderboard_60d: list[sector_rs.SectorRSSnapshot]

    # Historical context — the killer differentiation
    analogs: list[analog_finder.AnalogMatch]
    analog_distribution: dict[int, analog_finder.AnalogDistribution]
    conditional: dict  # from conditional_dist.get_today_conditional()

    # Action content for the "WATCH" section
    watchlists: dict[str, list[watchlists.WatchlistEntry]]

    # Structural — concentration / attribution of today's Nifty 50 move
    concentration: concentration.ConcentrationReading

    # Sector subgroup tracker — within-sector splits
    subgroups: dict[str, subgroups.SubgroupSnapshot]
    sibling_spreads: list[subgroups.SubgroupSpread]

    # Cross-asset features (India 10y today; USDINR / gold / US10y / crude
    # are registered but data_available=False pending sourcing)
    cross_asset: dict[str, cross_asset.CrossAssetEntry]

    def to_dict(self) -> dict[str, Any]:
        """Fully JSON-serializable nested dict. Used by the API layer."""
        return {
            "date": self.date.isoformat(),
            "regime": self.regime.to_dict(),
            "stress": self.stress.to_dict(),
            "breadth": self.breadth,
            "macro": self.macro,
            "sector_breadth": {
                k: v.to_dict() for k, v in self.sector_breadth.items()
            },
            "sector_rs": {
                k: v.to_dict() for k, v in self.sector_rs.items()
            },
            "sector_leaderboard_60d": [s.to_dict() for s in self.sector_leaderboard_60d],
            "analogs": [m.to_dict() for m in self.analogs],
            "analog_distribution": {
                h: d.to_dict() for h, d in self.analog_distribution.items()
            },
            "conditional": self.conditional,
            "watchlists": {
                k: [e.to_dict() for e in entries]
                for k, entries in self.watchlists.items()
            },
            "concentration": self.concentration.to_dict(),
            "subgroups": {k: v.to_dict() for k, v in self.subgroups.items()},
            "sibling_spreads": [s.to_dict() for s in self.sibling_spreads],
            "cross_asset": {k: v.to_dict() for k, v in self.cross_asset.items()},
        }


def _serialise_panel_row(panel: pd.DataFrame, asof: pd.Timestamp) -> dict[str, float | None]:
    """Convert one row of a panel into a plain dict of native floats / None."""
    if panel.empty:
        return {}
    valid = panel.index[panel.index <= asof]
    if valid.empty:
        return {}
    row = panel.loc[valid.max()]
    out: dict[str, float | None] = {}
    for col, val in row.items():
        if pd.isna(val):
            out[str(col)] = None
        else:
            try:
                out[str(col)] = float(val)
            except (TypeError, ValueError):
                out[str(col)] = None
    return out


def get_market_reading(asof: pd.Timestamp | None = None) -> MarketReading:
    """Compose the unified MarketReading for `asof` (default: latest).

    Internally calls every Phase 0 module; this is the single function
    the Daily Quant Note generator should depend on. If you find yourself
    importing more than this from insights/, the orchestrator should
    probably be extended instead.
    """
    # Use the regime panel's index as the canonical calendar (breadth ⊇ macro)
    regime_panel = regime_mod.compute_regime_panel()
    if regime_panel.empty:
        raise RuntimeError("MarketReading requires non-empty regime panel — check data pipeline")

    if asof is None:
        asof = regime_panel.index.max()
    asof = pd.Timestamp(asof)
    valid = regime_panel.index[regime_panel.index <= asof]
    if valid.empty:
        raise ValueError(f"No data available on or before {asof}")
    asof = valid.max()

    regime_snap = regime_mod.get_regime_snapshot(asof)
    stress_snap = stress.get_stress_snapshot(asof)
    if regime_snap is None or stress_snap is None:
        raise RuntimeError(f"Could not compute regime/stress at {asof}")

    sb_snaps = sector_breadth.get_sector_breadth_snapshot(asof)
    srs_snaps = sector_rs.get_sector_rs_snapshot(asof)
    leaderboard = sector_rs.get_leaderboard("60d", asof)

    analogs = analog_finder.find_analogs(asof, k=5)
    analog_dist = analog_finder.get_analog_distribution(asof, k=20)
    conditional = conditional_dist.get_today_conditional(asof)

    wl = watchlists.get_all_watchlists(asof)

    breadth_panel = breadth.get_breadth_panel()
    macro_panel = macro.get_macro_panel()

    conc = concentration.compute_concentration(asof)
    subgroup_snaps = subgroups.get_subgroup_snapshot(asof)
    spreads = subgroups.get_sibling_spreads(asof)
    cross = cross_asset.get_cross_asset_snapshot()

    return MarketReading(
        date=asof,
        regime=regime_snap,
        stress=stress_snap,
        breadth=_serialise_panel_row(breadth_panel, asof),
        macro=_serialise_panel_row(macro_panel, asof),
        sector_breadth=sb_snaps,
        sector_rs=srs_snaps,
        sector_leaderboard_60d=leaderboard,
        analogs=analogs,
        analog_distribution=analog_dist,
        conditional=conditional,
        watchlists=wl,
        concentration=conc,
        subgroups=subgroup_snaps,
        sibling_spreads=spreads,
        cross_asset=cross,
    )


def clear_all_caches() -> None:
    """Force every downstream module to rebuild on next call.

    Use this after the daily pipeline drops new EOD data and we want to
    refresh the API's in-memory cache before the next request.
    """
    breadth.clear_cache()
    macro.clear_cache()
    sector_breadth.clear_cache()
    sector_rs.clear_cache()
    regime_mod.clear_cache()
    stress.clear_cache()
    analog_finder.clear_cache()
    conditional_dist.clear_cache()
    watchlists.clear_cache()
    concentration.clear_cache()
    subgroups.clear_cache()
    cross_asset.clear_cache()
    stock_metrics.clear_cache()
    rs_rank.clear_cache()
    scores_mod.clear_cache()
    calendar_content.clear_cache()
    zerodha_sectors.clear_cache()
