"""Anniversary / calendar content engine — Phase 4.4 + insights_v2 Phase B.

For any date D, surfaces:
  - `get_on_this_day(D)` — anniversaries at 1y / 3y / 5y / 10y back,
    each annotated with the regime + stress reading on that historical
    date and an optional event_tag if D-back lands on a curated event
  - `get_seasonality(D)` — the historical calendar-month (and ISO-week)
    Nifty return profile: median / middle-half range / % positive years /
    n. Descriptive-only historical observation, NOT a forward-return
    claim — with n ~16 per month it can never clear the n>=100 bar in
    `tasks/insight_engine/VALIDITY_PROTOCOL.md`, so copy must stay
    descriptive and disclose n (see `commentary._seasonality_note`).
  - `get_pre_event(D)` — known curated events falling within the next N
    days, each attached to the historical move profile for the same event
    *type* (budget / RBI / election). The curated file holds only *past*
    events, so this returns upcoming hits only once forward-dated events
    are manually added to `data/static/historical_events.csv`; the
    same-event-type history works regardless.
  - `load_events()` — curated Indian-market events at
    `data/static/historical_events.csv`

Built test-first under the policy in `tasks/insight_engine/TDD_POLICY.md`.
The test file `tests/test_insights_calendar.py` was authored before this
implementation.
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
from app.insights._freshness import file_signature
from app.insights._paths import indices_dir as _indices_dir


DEFAULT_HORIZONS_YEARS: tuple[int, ...] = (1, 3, 5, 10)

# Minimum historical observations before a seasonality profile is emitted.
# Below this, the month/week is omitted (None) rather than reported off a
# handful of years — no fabricated precision.
SEASONALITY_MIN_OBS: int = 3


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


def load_events() -> list[dict]:
    """Read the curated events file. Returns a list of {date, tag} dicts."""
    return _load_events_cached(file_signature(_events_file()))


@lru_cache(maxsize=2)
def _load_events_cached(signature) -> list[dict]:
    p = _events_file()
    if not p.exists():
        return []
    df = pd.read_csv(p, comment="#", parse_dates=["date"])
    return [
        {"date": pd.Timestamp(row["date"]), "tag": str(row["tag"])}
        for _, row in df.iterrows()
    ]


load_events.cache_clear = _load_events_cached.cache_clear


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


# ─────────── Nifty panel loader (shared by B1 + B2) ───────────


def _nifty_close() -> pd.Series:
    """Long-history Nifty 50 daily close — the 16y panel used for the
    seasonality profile and event-move history. Same source + shape as
    `stress._nifty_close`; empty Series when the panel is unprovisioned."""
    return _nifty_close_cached(file_signature(_indices_dir() / "NIFTY_50.csv"))


@lru_cache(maxsize=2)
def _nifty_close_cached(signature) -> pd.Series:
    p = _indices_dir() / "NIFTY_50.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    return (pd.read_csv(p, parse_dates=["date"])
              .set_index("date")["close"]
              .sort_index())


_nifty_close.cache_clear = _nifty_close_cached.cache_clear


def clear_cache() -> None:
    """Drop the cached Nifty close + events (hooked into
    reading.clear_all_caches)."""
    _nifty_close_cached.cache_clear()
    _load_events_cached.cache_clear()


# ─────────── B1: seasonality ───────────


@dataclass
class PeriodSeasonality:
    """Historical return profile for one calendar period (a month, or an
    ISO week-of-year) across the panel's years. Descriptive statistics of
    *past* same-period returns — not a forecast."""
    kind: str            # "month" | "week"
    period: int          # 1-12 for month, ISO week 1-53 for week
    label: str           # "December" | "ISO week 51"
    n: int               # number of historical years/observations
    median_return_pct: float | None
    q1_return_pct: float | None   # 25th percentile (lower edge of middle half)
    q3_return_pct: float | None   # 75th percentile (upper edge of middle half)
    pct_positive: float | None    # fraction of observations that finished > 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SeasonalityProfile:
    asof: pd.Timestamp
    month: Optional[PeriodSeasonality]
    week: Optional[PeriodSeasonality]

    def to_dict(self) -> dict:
        return {
            "asof": self.asof.isoformat(),
            "month": self.month.to_dict() if self.month else None,
            "week": self.week.to_dict() if self.week else None,
        }


def _monthly_returns(close: pd.Series) -> pd.Series:
    """Month-over-month returns from a daily close series: resample to the
    last observation each calendar month, then percentage change."""
    if close is None or close.empty:
        return pd.Series(dtype=float)
    monthly_close = close.sort_index().resample("ME").last()
    return monthly_close.pct_change(fill_method=None).dropna()


def _weekly_returns(close: pd.Series) -> pd.Series:
    """Week-over-week returns from a daily close series."""
    if close is None or close.empty:
        return pd.Series(dtype=float)
    weekly_close = close.sort_index().resample("W").last()
    return weekly_close.pct_change(fill_method=None).dropna()


def _period_seasonality(values: pd.Series, kind: str, period: int,
                        label: str,
                        min_obs: int = SEASONALITY_MIN_OBS,
                        ) -> Optional[PeriodSeasonality]:
    """Reduce a set of same-period returns (fractions) to a descriptive
    profile, or None when history is too thin to report honestly."""
    vals = values.dropna()
    n = int(len(vals))
    if n < min_obs:
        return None
    return PeriodSeasonality(
        kind=kind,
        period=int(period),
        label=label,
        n=n,
        median_return_pct=float(vals.median() * 100.0),
        q1_return_pct=float(vals.quantile(0.25) * 100.0),
        q3_return_pct=float(vals.quantile(0.75) * 100.0),
        pct_positive=float((vals > 0).mean()),
    )


def compute_seasonality(close: pd.Series, asof: pd.Timestamp,
                        include_week: bool = True) -> SeasonalityProfile:
    """Pure core: the calendar-month (and optional ISO-week) return profile
    for `asof`'s month/week, computed from `close`. Testable with a
    synthetic panel."""
    asof = pd.Timestamp(asof)

    monthly = _monthly_returns(close)
    month_num = asof.month
    if not monthly.empty:
        month_vals = monthly[monthly.index.month == month_num]
    else:
        month_vals = monthly
    month_profile = _period_seasonality(
        month_vals, "month", month_num, asof.strftime("%B"),
    )

    week_profile = None
    if include_week:
        weekly = _weekly_returns(close)
        week_num = int(asof.isocalendar().week)
        if not weekly.empty:
            weeks = weekly.index.isocalendar().week.to_numpy()
            week_vals = weekly[weeks == week_num]
        else:
            week_vals = weekly
        week_profile = _period_seasonality(
            week_vals, "week", week_num, f"ISO week {week_num}",
        )

    return SeasonalityProfile(asof=asof, month=month_profile, week=week_profile)


def get_seasonality(asof: Optional[pd.Timestamp] = None,
                    include_week: bool = True) -> SeasonalityProfile:
    """Public entry: seasonality profile against the real Nifty panel.
    Defaults `asof` to the panel's last date."""
    close = _nifty_close()
    if asof is None:
        asof = close.index.max() if not close.empty else pd.Timestamp.today()
    return compute_seasonality(close, pd.Timestamp(asof), include_week=include_week)


# ─────────── B2: pre-event helper ───────────

# Curated events are classified into recurring *types* by keyword so we can
# report the historical move around past events of the same kind. Extend the
# keyword table when a new recurring type is curated into the CSV.
EVENT_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "budget": ("budget",),
    "rbi_policy": ("rbi", "repo", "monetary", "rate-hike", "rate hike"),
    "election": ("election",),
}


def classify_event(tag: str) -> Optional[str]:
    """Map a curated event tag to a recurring event type, or None."""
    low = (tag or "").lower()
    for etype, kws in EVENT_TYPE_KEYWORDS.items():
        if any(kw in low for kw in kws):
            return etype
    return None


@dataclass
class EventTypeHistory:
    """Historical Nifty move around past events of one type. Descriptive."""
    event_type: str
    n: int
    median_move_1d_pct: float | None
    median_move_5d_pct: float | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UpcomingEvent:
    date: pd.Timestamp
    tag: str
    event_type: Optional[str]
    days_until: int
    history: Optional[EventTypeHistory]

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "tag": self.tag,
            "event_type": self.event_type,
            "days_until": self.days_until,
            "history": self.history.to_dict() if self.history else None,
        }


def _event_move(close: pd.Series, event_date: pd.Timestamp,
                horizons: tuple[int, ...] = (1, 5)) -> Optional[dict[int, float]]:
    """Nifty move (%) around `event_date`, measured from the prior trading
    close. Horizon h = return over h trading days including the event day
    (h=1 is the event-day reaction). None if the event is outside the panel
    or has no prior day."""
    if close is None or close.empty:
        return None
    idx = close.index
    snapped = _snap_to_trading_day(pd.Timestamp(event_date), idx)
    if snapped is None:
        return None
    pos = int(idx.get_indexer([snapped])[0])
    if pos <= 0:
        return None
    base = float(close.iloc[pos - 1])
    if base == 0:
        return None
    out: dict[int, float] = {}
    for h in horizons:
        tpos = pos + h - 1
        if 0 <= tpos < len(close):
            out[h] = (float(close.iloc[tpos]) / base - 1.0) * 100.0
    return out or None


def get_event_type_history(event_type: str,
                           events: Optional[list[dict]] = None,
                           close: Optional[pd.Series] = None,
                           ) -> Optional[EventTypeHistory]:
    """Median 1d / 5d Nifty move around all past curated events of
    `event_type`. None when no such event resolves against the panel."""
    if events is None:
        events = load_events()
    if close is None:
        close = _nifty_close()
    moves_1d: list[float] = []
    moves_5d: list[float] = []
    for ev in events:
        if classify_event(ev["tag"]) != event_type:
            continue
        mv = _event_move(close, ev["date"])
        if not mv:
            continue
        if mv.get(1) is not None:
            moves_1d.append(mv[1])
        if mv.get(5) is not None:
            moves_5d.append(mv[5])
    if not moves_1d:
        return None
    return EventTypeHistory(
        event_type=event_type,
        n=len(moves_1d),
        median_move_1d_pct=float(pd.Series(moves_1d).median()),
        median_move_5d_pct=(float(pd.Series(moves_5d).median())
                            if moves_5d else None),
    )


def get_pre_event(asof: pd.Timestamp, window_days: int = 7,
                  events: Optional[list[dict]] = None,
                  close: Optional[pd.Series] = None,
                  ) -> list[UpcomingEvent]:
    """Curated events dated within [asof, asof + window_days], each attached
    to its event-type history. Returns [] when nothing is curated ahead —
    forward-dated events must be added to the CSV manually (the file holds
    only past events by design)."""
    asof = pd.Timestamp(asof)
    if events is None:
        events = load_events()
    out: list[UpcomingEvent] = []
    for ev in events:
        days_until = (ev["date"] - asof).days
        if 0 <= days_until <= window_days:
            etype = classify_event(ev["tag"])
            hist = (get_event_type_history(etype, events=events, close=close)
                    if etype else None)
            out.append(UpcomingEvent(
                date=ev["date"], tag=ev["tag"], event_type=etype,
                days_until=days_until, history=hist,
            ))
    out.sort(key=lambda e: e.days_until)
    return out
