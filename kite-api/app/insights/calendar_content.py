"""Anniversary / calendar content engine — Phase 4.4.

For any date D, surfaces:
  - `get_on_this_day(D)` — anniversaries at 1y / 3y / 5y / 10y back,
    each annotated with the regime + stress reading on that historical
    date and an optional event_tag if D-back lands on a curated event
  - `load_events()` — curated Indian-market events at
    `data/static/historical_events.csv`

Built test-first under the policy in `tasks/insight_engine/TDD_POLICY.md`.
The test file `tests/test_insights_calendar.py` was authored before this
implementation.

Two other helpers are scaffolded for later phases (seasonality + pre-event
look-ahead) but not yet exposed.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

from app.config import get_settings
from app.insights import regime as regime_mod
from app.insights import stress as stress_mod


DEFAULT_HORIZONS_YEARS: tuple[int, ...] = (1, 3, 5, 10)


@dataclass
class AnniversarySnapshot:
    """Reading on a historical anniversary date."""
    horizon_years: int
    date: pd.Timestamp
    regime: str
    stress_score: float | None
    event_tag: Optional[str]
    # Days actually offset (may differ from years*365 if we snapped to
    # the nearest available trading day)
    actual_offset_days: int

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat()
        return d


def _events_file() -> Path:
    return get_settings().data_dir / "data" / "static" / "historical_events.csv"


@lru_cache(maxsize=1)
def load_events() -> list[dict]:
    """Read the curated events file. Returns a list of {date, tag} dicts."""
    p = _events_file()
    if not p.exists():
        return []
    df = pd.read_csv(p, comment="#", parse_dates=["date"])
    return [
        {"date": pd.Timestamp(row["date"]), "tag": str(row["tag"])}
        for _, row in df.iterrows()
    ]


def _event_tag_for_date(target: pd.Timestamp,
                        events: list[dict],
                        slack_days: int = 2) -> Optional[str]:
    """Find a curated event within `slack_days` of `target`. Returns the
    tag of the closest match, or None."""
    if not events:
        return None
    best_tag = None
    best_dist = slack_days + 1
    for ev in events:
        dist = abs((ev["date"] - target).days)
        if dist <= slack_days and dist < best_dist:
            best_tag = ev["tag"]
            best_dist = dist
    return best_tag


def _snap_to_trading_day(target: pd.Timestamp,
                         panel_index: pd.DatetimeIndex) -> Optional[pd.Timestamp]:
    """Find the trading day in `panel_index` closest to `target`. Returns
    None if `target` is outside the panel by more than a week."""
    if panel_index.empty:
        return None
    # Allow up to a week's slack so the function works around weekends
    # / holidays / non-business days
    pos = panel_index.searchsorted(target)
    candidates = []
    if 0 <= pos < len(panel_index):
        candidates.append(panel_index[pos])
    if pos - 1 >= 0:
        candidates.append(panel_index[pos - 1])
    if not candidates:
        return None
    closest = min(candidates, key=lambda d: abs((d - target).days))
    if abs((closest - target).days) > 7:
        return None
    return closest


def get_on_this_day(
    asof: pd.Timestamp,
    horizons_years: tuple[int, ...] = DEFAULT_HORIZONS_YEARS,
) -> dict[int, AnniversarySnapshot]:
    """For each horizon in `horizons_years`, look back that many years
    from `asof` and return the regime + stress + event_tag (if any) on
    that historical date.

    Missing horizons (anniversary date before our panel begins, or no
    regime/stress data available) are simply omitted from the returned
    dict rather than set to None — keeps the consumer code simple.
    """
    asof = pd.Timestamp(asof)
    panel = stress_mod.compute_stress_panel()
    events = load_events()

    out: dict[int, AnniversarySnapshot] = {}
    for years in horizons_years:
        try:
            target = asof - pd.DateOffset(years=years)
        except Exception:
            continue
        snapped = _snap_to_trading_day(target, panel.index)
        if snapped is None:
            continue

        regime_snap = regime_mod.get_regime_snapshot(snapped)
        stress_snap = stress_mod.get_stress_snapshot(snapped)
        if regime_snap is None or stress_snap is None:
            continue

        out[years] = AnniversarySnapshot(
            horizon_years=years,
            date=snapped,
            regime=regime_snap.regime,
            stress_score=float(stress_snap.score) if stress_snap.score is not None else None,
            event_tag=_event_tag_for_date(snapped, events),
            actual_offset_days=(asof - snapped).days,
        )
    return out
