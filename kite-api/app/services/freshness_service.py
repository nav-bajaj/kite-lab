"""Data-freshness / staleness monitor.

Motivation (real incident): the insight engine's INDIA_VIX.csv silently
froze at 2026-05-08 while every other index panel advanced to 2026-07-10.
The /api/insights/reading date looked current, but the VIX input feeding the
stress + regime scores was ~2 months stale and nobody noticed. This module
inspects every data source the platform depends on and reports a per-source
freshness verdict so a frozen input can no longer hide.

Design — reference-based trading-day lag (the key idea)
-------------------------------------------------------
We do NOT maintain an exchange holiday calendar. Instead we take the latest
date present in the core equity indices (max of NIFTY_50 / NIFTY_100) as the
"expected latest trading day" reference. For every daily-cadence source we
count how many *actual* index trading dates sit between that source's last
date and the reference (using NIFTY_50's own date list, which naturally skips
weekends and holidays). VIX at 2026-05-08 against a 2026-07-10 reference lands
~40 trading days behind, which trips the critical tier — exactly what should
have paged the founder.

Thresholds are transparent operational choices, not researched constants. They
are module-level named values below so they can be read and tuned in one place.

Every source builder degrades gracefully: an unreadable file / absent dir /
down database yields status="missing" with an explanatory detail string and
never raises out of the aggregator, so the whole report builds even before a
fresh Railway volume is provisioned.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Optional


# ---------------------------------------------------------------------------
# Thresholds — operational choices, documented and tunable here (not derived
# from any study). Daily tiers are in *trading days* of lag versus the index
# reference; monthly tiers are in wall-clock days; token tiers in hours.
# ---------------------------------------------------------------------------

DAILY_FRESH_MAX_LAG = 1        # lag 0-1 trading days -> fresh
DAILY_STALE_MAX_LAG = 5        # lag 2-5 -> stale; > 5 -> critical
WALL_CLOCK_CRITICAL_DAYS = 10  # any daily source older than this (wall clock)
#                                is critical regardless of lag — guards against
#                                the reference index itself being frozen.

MONTHLY_FRESH_MAX_DAYS = 40    # snapshot < 40d old -> fresh
MONTHLY_STALE_MAX_DAYS = 70    # 40-70d -> stale; > 70d -> critical

TOKEN_STALE_HOURS = 2.0        # < 2h to expiry -> stale

# Trades are episodic (weekly / biweekly rebalances), so they are judged on a
# looser wall-clock rule rather than trading-day lag.
TRADES_STALE_AGE_DAYS = 15
TRADES_CRITICAL_AGE_DAYS = 35


# Severity ordering for rolling up the overall status. `critical` outranks
# `missing` in labelling: a present-but-frozen source is the more actionable
# "something stopped updating" signal, while missing is often an unprovisioned
# optional source.
_SEVERITY = {"fresh": 0, "stale": 1, "missing": 2, "critical": 3}


# Indices we surface. VIX is deliberately its own row — it is the input that
# froze in the motivating incident.
CORE_INDICES = [
    ("NIFTY_50", "Nifty 50"),
    ("NIFTY_100", "Nifty 100"),
    ("NIFTY_500", "Nifty 500"),
]
VIX_INDEX = ("INDIA_VIX", "India VIX")
SECTOR_INDICES = [
    ("NIFTY_BANK", "Nifty Bank"),
    ("NIFTY_IT", "Nifty IT"),
]

# Production portfolios whose DB snapshot date should advance each trading day
# via the daily pipeline sync. Kept local to avoid importing the settings
# module in the pure-logic path; validated against app.config.UNIVERSES.
_PORTFOLIO_UNIVERSES = [
    ("om25_v3", "Quality Momentum (OM25 v3)"),
    ("tl25_v3", "Trend Leaders (TL25 v3)"),
    ("l6_v2", "Core Momentum (L6 v2)"),
    ("combo_defensive", "Defensive Blend (COMBO)"),
    ("nse500", "NSE 500 (legacy)"),
    ("nifty250", "Nifty 250 (legacy)"),
    ("nifty100", "Nifty 100 (legacy)"),
]


# ---------------------------------------------------------------------------
# Data shape
# ---------------------------------------------------------------------------

@dataclass
class SourceFreshness:
    """One source's freshness verdict. All fields are JSON-safe via to_dict()."""
    name: str
    kind: str  # stock_panel|index|cross_asset|sector_constituents|index_weights|token|trades|portfolio
    last_date: Optional[str]         # ISO date/datetime string, or None
    age_days: Optional[int]          # wall-clock days since last_date, None if unknown
    lag_trading_days: Optional[int]  # index trading dates behind the reference, None if n/a
    status: str                      # fresh|stale|critical|missing
    detail: str
    expected_cadence: str            # daily|monthly|session

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pure helpers — classification + calendar math
# ---------------------------------------------------------------------------

def trading_day_lag(trading_dates: List[date], last_date: date,
                    reference_date: date) -> int:
    """Number of index trading dates strictly after `last_date` and up to and
    including `reference_date`.

    last_date == reference_date -> 0; one trading day earlier -> 1; source at
    or ahead of the reference -> 0 (clamped). `trading_dates` must be sorted
    ascending.
    """
    if last_date >= reference_date:
        return 0
    # count dates d with last_date < d <= reference_date
    left = bisect_right(trading_dates, last_date)
    right = bisect_right(trading_dates, reference_date)
    return max(0, right - left)


def classify_daily(lag_trading_days: Optional[int],
                   age_days: Optional[int]) -> str:
    """Tier a daily-cadence source from its trading-day lag and wall-clock age.

    critical if lag > DAILY_STALE_MAX_LAG OR wall-clock age exceeds
    WALL_CLOCK_CRITICAL_DAYS (the latter catches a frozen reference index that
    would otherwise make every lag read 0).
    """
    if age_days is not None and age_days > WALL_CLOCK_CRITICAL_DAYS:
        return "critical"
    if lag_trading_days is None:
        # No reference available — fall back to a coarse wall-clock read.
        if age_days is None:
            return "missing"
        if age_days <= DAILY_FRESH_MAX_LAG:
            return "fresh"
        if age_days <= DAILY_STALE_MAX_LAG:
            return "stale"
        return "critical"
    if lag_trading_days > DAILY_STALE_MAX_LAG:
        return "critical"
    if lag_trading_days > DAILY_FRESH_MAX_LAG:
        return "stale"
    return "fresh"


def classify_monthly(age_days: Optional[int]) -> str:
    """Tier a monthly-cadence snapshot from its wall-clock age."""
    if age_days is None:
        return "missing"
    if age_days > MONTHLY_STALE_MAX_DAYS:
        return "critical"
    if age_days >= MONTHLY_FRESH_MAX_DAYS:
        return "stale"
    return "fresh"


def classify_token(valid: bool, hours_to_expiry: Optional[float],
                   file_missing: bool) -> str:
    """Tier the Kite access token from its validity + hours-to-expiry."""
    if file_missing:
        return "missing"
    if not valid:
        return "critical"
    if hours_to_expiry is not None and hours_to_expiry < TOKEN_STALE_HOURS:
        return "stale"
    return "fresh"


def classify_trades(age_days: Optional[int]) -> str:
    """Tier the last-trade date on a looser wall-clock rule (trades are
    episodic, not daily)."""
    if age_days is None:
        return "missing"
    if age_days > TRADES_CRITICAL_AGE_DAYS:
        return "critical"
    if age_days > TRADES_STALE_AGE_DAYS:
        return "stale"
    return "fresh"


def last_csv_date(path: Path) -> Optional[date]:
    """Cheap last-row date read: seek the tail of the file and parse the first
    comma-separated field of the final non-empty, non-header line.

    Returns None for a missing/empty/header-only file or an unparseable tail.
    """
    try:
        if not path.exists() or path.stat().st_size == 0:
            return None
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            chunk = min(size, 8192)
            fh.seek(size - chunk, 0)
            tail = fh.read().decode("utf-8", errors="ignore")
        lines = [ln.strip() for ln in tail.splitlines() if ln.strip()]
        for ln in reversed(lines):
            first = ln.split(",", 1)[0].strip()
            if not first or first.lower() == "date":
                continue
            try:
                return datetime.strptime(first[:10], "%Y-%m-%d").date()
            except ValueError:
                continue
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Source builders
# ---------------------------------------------------------------------------

def _median_date(dates: List[date]) -> date:
    """Median that works on dates (statistics.median would average the two
    middle values, which is undefined for date objects). Even counts take the
    lower-middle element."""
    ordered = sorted(dates)
    return ordered[(len(ordered) - 1) // 2]


def _age_days(last_date: Optional[date], today: date) -> Optional[int]:
    if last_date is None:
        return None
    return (today - last_date).days


def build_daily_source(name: str, kind: str, last_date: Optional[date],
                       trading_dates: List[date],
                       reference_date: Optional[date], today: date,
                       cadence: str = "daily",
                       detail_prefix: str = "") -> SourceFreshness:
    """Build one daily-cadence row from a resolved last_date."""
    if last_date is None:
        return SourceFreshness(
            name=name, kind=kind, last_date=None, age_days=None,
            lag_trading_days=None, status="missing",
            detail=(detail_prefix or "no data file / empty series"),
            expected_cadence=cadence,
        )
    lag = (trading_day_lag(trading_dates, last_date, reference_date)
           if reference_date is not None and trading_dates else None)
    age = _age_days(last_date, today)
    status = classify_daily(lag, age)
    if detail_prefix:
        detail = detail_prefix
    elif lag is not None:
        detail = f"last {last_date.isoformat()}; {lag} trading day(s) behind reference"
    else:
        detail = f"last {last_date.isoformat()}; no index reference to compare"
    return SourceFreshness(
        name=name, kind=kind, last_date=last_date.isoformat(), age_days=age,
        lag_trading_days=lag, status=status, detail=detail,
        expected_cadence=cadence,
    )


def _build_index_rows(indices_directory: Path, trading_dates: List[date],
                      reference_date: Optional[date],
                      today: date) -> List[SourceFreshness]:
    rows: List[SourceFreshness] = []
    for fname, label in [*CORE_INDICES, VIX_INDEX, *SECTOR_INDICES]:
        try:
            last = last_csv_date(indices_directory / f"{fname}.csv")
        except Exception:
            last = None
        rows.append(build_daily_source(
            name=label, kind="index", last_date=last,
            trading_dates=trading_dates, reference_date=reference_date,
            today=today,
        ))
    return rows


def _build_stock_panel_row(stock_panel_dir: Path, trading_dates: List[date],
                           reference_date: Optional[date],
                           today: date) -> SourceFreshness:
    """Aggregate NSE500 panel row: file count, median last date, and up to five
    worst laggards (symbols whose last date trails the reference)."""
    try:
        files = sorted(stock_panel_dir.glob("*_day.csv"))
    except Exception:
        files = []
    if not files:
        return SourceFreshness(
            name="NSE500 stock panel", kind="stock_panel", last_date=None,
            age_days=None, lag_trading_days=None, status="missing",
            detail=f"no *_day.csv files under {stock_panel_dir}",
            expected_cadence="daily",
        )

    per_symbol: List[tuple] = []  # (symbol, last_date)
    for f in files:
        last = last_csv_date(f)
        if last is not None:
            per_symbol.append((f.name[:-len("_day.csv")], last))

    if not per_symbol:
        return SourceFreshness(
            name="NSE500 stock panel", kind="stock_panel", last_date=None,
            age_days=None, lag_trading_days=None, status="missing",
            detail=f"{len(files)} files present but none had a parseable last row",
            expected_cadence="daily",
        )

    dates = [d for _, d in per_symbol]
    med = _median_date(dates)
    worst_last = min(dates)

    if reference_date is not None and trading_dates:
        lagged = [(s, d, trading_day_lag(trading_dates, d, reference_date))
                  for s, d in per_symbol]
        lagged = [t for t in lagged if t[2] > 0]
        lagged.sort(key=lambda t: t[2], reverse=True)
        worst_lag = lagged[0][2] if lagged else 0
    else:
        lagged = []
        worst_lag = None

    worst_age = _age_days(worst_last, today)
    status = classify_daily(worst_lag, worst_age)

    if lagged:
        laggard_str = ", ".join(f"{s}@{d.isoformat()}(-{lag}td)"
                                for s, d, lag in lagged[:5])
        detail = (f"{len(files)} files; median last {med.isoformat()}; "
                  f"{len(lagged)} lagging: {laggard_str}")
    else:
        detail = f"{len(files)} files; median last {med.isoformat()}; all current"

    return SourceFreshness(
        name="NSE500 stock panel", kind="stock_panel",
        last_date=med.isoformat(), age_days=_age_days(med, today),
        lag_trading_days=worst_lag, status=status, detail=detail,
        expected_cadence="daily",
    )


def _build_cross_asset_rows(cross_asset_dir: Path, registry: Iterable,
                            trading_dates: List[date],
                            reference_date: Optional[date],
                            today: date,
                            primary_dir: Optional[Path] = None) -> List[SourceFreshness]:
    rows: List[SourceFreshness] = []
    for entry in registry:
        asset_id, label, csv_filename = entry
        if csv_filename is None:
            # Deferred asset with no data path — excluded from the report so it
            # doesn't peg the overall status at missing forever.
            continue
        # Mirror cross_asset._asset_path: the tracked NIFTY index (india_10y)
        # syncs into the shared indices dir (indices_data_historical), the
        # futures into cross_asset_dir (indices_data_full). Check the indices
        # dir first so the monitor reports the same file the engine serves.
        path = cross_asset_dir / csv_filename
        if primary_dir is not None and (primary_dir / csv_filename).exists():
            path = primary_dir / csv_filename
        try:
            last = last_csv_date(path)
        except Exception:
            last = None
        rows.append(build_daily_source(
            name=label, kind="cross_asset", last_date=last,
            trading_dates=trading_dates, reference_date=reference_date,
            today=today,
        ))
    return rows


def _build_sector_constituents_row(sc_root: Path, today: date) -> SourceFreshness:
    """Monthly: newest YYYY-MM snapshot directory under the constituents root.
    The month string is treated as the last day of that month for age math."""
    try:
        subdirs = sorted(p for p in sc_root.iterdir()
                         if p.is_dir() and _parse_yyyymm(p.name) is not None)
    except Exception:
        subdirs = []
    if not subdirs:
        return SourceFreshness(
            name="Sector constituents", kind="sector_constituents",
            last_date=None, age_days=None, lag_trading_days=None,
            status="missing", detail=f"no YYYY-MM snapshot dirs under {sc_root}",
            expected_cadence="monthly",
        )
    newest = subdirs[-1]
    snap = _parse_yyyymm(newest.name)  # first of that month
    # Anchor the age at the month end so a mid-month check of the current
    # month's snapshot reads as fresh rather than partway aged.
    month_end = _month_end(snap)
    age = max(0, (today - month_end).days)
    status = classify_monthly(age)
    return SourceFreshness(
        name="Sector constituents", kind="sector_constituents",
        last_date=newest.name, age_days=age, lag_trading_days=None,
        status=status, detail=f"newest snapshot {newest.name}",
        expected_cadence="monthly",
    )


def _build_index_weights_row(weights_root: Path, today: date) -> SourceFreshness:
    """Monthly: one aggregate row across every per-index weights directory. The
    reported last date is the *oldest* of each directory's newest dated file,
    so a single stale index surfaces rather than being masked by fresher peers.
    """
    try:
        subdirs = sorted(p for p in weights_root.iterdir() if p.is_dir())
    except Exception:
        subdirs = []
    if not subdirs:
        return SourceFreshness(
            name="Index weights", kind="index_weights", last_date=None,
            age_days=None, lag_trading_days=None, status="missing",
            detail=f"no per-index weight dirs under {weights_root}",
            expected_cadence="monthly",
        )

    newest_per_dir: List[tuple] = []  # (index_name, newest_date)
    for d in subdirs:
        dated = []
        for f in d.glob("*.csv"):
            parsed = _parse_iso_date(f.stem)
            if parsed is not None:
                dated.append(parsed)
        if dated:
            newest_per_dir.append((d.name, max(dated)))

    if not newest_per_dir:
        return SourceFreshness(
            name="Index weights", kind="index_weights", last_date=None,
            age_days=None, lag_trading_days=None, status="missing",
            detail=f"{len(subdirs)} dirs present, none with a dated CSV",
            expected_cadence="monthly",
        )

    laggard_name, laggard_date = min(newest_per_dir, key=lambda t: t[1])
    age = max(0, (today - laggard_date).days)
    status = classify_monthly(age)
    return SourceFreshness(
        name="Index weights", kind="index_weights",
        last_date=laggard_date.isoformat(), age_days=age,
        lag_trading_days=None, status=status,
        detail=(f"{len(newest_per_dir)} index dirs; oldest snapshot "
                f"{laggard_name}@{laggard_date.isoformat()}"),
        expected_cadence="monthly",
    )


def _build_token_row(today: date) -> SourceFreshness:
    """Kite access-token freshness, reusing system_service's expiry logic."""
    try:
        from app.services.system_service import SystemService

        status = SystemService.check_token_status()
        file_missing = "not found" in (status.message or "").lower()
        hours = None
        if status.expires_at is not None:
            hours = (status.expires_at - datetime.now()).total_seconds() / 3600.0
        tier = classify_token(status.valid, hours, file_missing)
        last = status.expires_at.date().isoformat() if status.expires_at else None
        return SourceFreshness(
            name="Kite access token", kind="token", last_date=last,
            age_days=None, lag_trading_days=None, status=tier,
            detail=status.message or "", expected_cadence="session",
        )
    except Exception as exc:
        return SourceFreshness(
            name="Kite access token", kind="token", last_date=None,
            age_days=None, lag_trading_days=None, status="missing",
            detail=f"token status unavailable: {exc}", expected_cadence="session",
        )


def _build_trades_row(today: date) -> SourceFreshness:
    """Last trade date across all universes from the DB (episodic cadence)."""
    try:
        from sqlalchemy import func

        from app.models.database import get_session_local
        from app.models.models import Trade

        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            last = db.query(func.max(Trade.trade_date)).scalar()
        finally:
            db.close()
        if last is None:
            return SourceFreshness(
                name="Trades (all universes)", kind="trades", last_date=None,
                age_days=None, lag_trading_days=None, status="missing",
                detail="no trades in database", expected_cadence="session",
            )
        age = (today - last).days
        return SourceFreshness(
            name="Trades (all universes)", kind="trades",
            last_date=last.isoformat(), age_days=age, lag_trading_days=None,
            status=classify_trades(age),
            detail=f"most recent trade {last.isoformat()} ({age}d ago)",
            expected_cadence="session",
        )
    except Exception as exc:
        return SourceFreshness(
            name="Trades (all universes)", kind="trades", last_date=None,
            age_days=None, lag_trading_days=None, status="missing",
            detail=f"trade DB unavailable: {exc}", expected_cadence="session",
        )


def _build_portfolio_rows(trading_dates: List[date],
                          reference_date: Optional[date],
                          today: date) -> List[SourceFreshness]:
    """One row per production portfolio: latest holdings snapshot date, which
    the daily pipeline advances every trading day. If the DB is unreachable a
    single aggregate missing row is returned."""
    try:
        from app.models.database import get_session_local
        from app.services.portfolio_db_service import get_latest_snapshot_date

        SessionLocal = get_session_local()
        db = SessionLocal()
        rows: List[SourceFreshness] = []
        try:
            for universe, label in _PORTFOLIO_UNIVERSES:
                try:
                    last = get_latest_snapshot_date(db, universe)
                except Exception:
                    last = None
                rows.append(build_daily_source(
                    name=label, kind="portfolio", last_date=last,
                    trading_dates=trading_dates, reference_date=reference_date,
                    today=today,
                    detail_prefix=(None if last else
                                   f"no holdings snapshot for {universe}") or "",
                ))
        finally:
            db.close()
        return rows
    except Exception as exc:
        return [SourceFreshness(
            name="Portfolios", kind="portfolio", last_date=None, age_days=None,
            lag_trading_days=None, status="missing",
            detail=f"portfolio DB unavailable: {exc}", expected_cadence="daily",
        )]


# ---------------------------------------------------------------------------
# Small date parsers
# ---------------------------------------------------------------------------

def _parse_iso_date(s: str) -> Optional[date]:
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_yyyymm(s: str) -> Optional[date]:
    try:
        return datetime.strptime(s[:7], "%Y-%m").date()
    except (ValueError, TypeError):
        return None


def _month_end(first_of_month: date) -> date:
    if first_of_month.month == 12:
        nxt = date(first_of_month.year + 1, 1, 1)
    else:
        nxt = date(first_of_month.year, first_of_month.month + 1, 1)
    return nxt - timedelta(days=1)


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

def _load_trading_dates(indices_directory: Path) -> List[date]:
    """Load the reference trading calendar from NIFTY_50 (fallback NIFTY_100)."""
    for fname in ("NIFTY_50", "NIFTY_100"):
        path = indices_directory / f"{fname}.csv"
        try:
            if not path.exists():
                continue
            import pandas as pd

            df = pd.read_csv(path, usecols=["date"])
            dates = sorted({pd.Timestamp(d).date() for d in df["date"]})
            if dates:
                return dates
        except Exception:
            continue
    return []


def get_freshness_report(
    *,
    today: Optional[date] = None,
    indices_directory: Optional[Path] = None,
    stock_panel_dir: Optional[Path] = None,
    cross_asset_dir: Optional[Path] = None,
    cross_asset_registry: Optional[Iterable] = None,
    sector_constituents_root: Optional[Path] = None,
    index_weights_root: Optional[Path] = None,
    include_db: bool = True,
    include_token: bool = True,
) -> dict:
    """Inspect every data source and return a structured freshness report.

    All directory arguments are injectable so tests can point at synthetic
    fixtures; production callers pass nothing and the real locations resolve
    via app.insights._paths / app.config.settings.
    """
    if today is None:
        today = date.today()

    # Resolve default locations lazily so the pure helpers stay import-light.
    if indices_directory is None:
        from app.insights._paths import indices_dir
        indices_directory = indices_dir()
    if stock_panel_dir is None:
        from app.config import get_settings
        stock_panel_dir = get_settings().data_dir / "nse500_data_merged"
    if cross_asset_dir is None or cross_asset_registry is None:
        from app.insights import cross_asset as _ca
        if cross_asset_dir is None:
            cross_asset_dir = _ca.INDICES_DIR
        if cross_asset_registry is None:
            cross_asset_registry = _ca.REGISTERED_ASSETS
    if sector_constituents_root is None:
        from app.config import get_settings
        sector_constituents_root = (
            get_settings().data_dir / "data" / "static" / "sector_constituents")
    if index_weights_root is None:
        from app.config import get_settings
        index_weights_root = (
            get_settings().data_dir / "data" / "static" / "index_weights")

    trading_dates = _load_trading_dates(indices_directory)

    # Reference = the latest date across the core equity indices.
    ref_candidates = []
    for fname in ("NIFTY_50", "NIFTY_100"):
        d = last_csv_date(indices_directory / f"{fname}.csv")
        if d is not None:
            ref_candidates.append(d)
    reference_date = max(ref_candidates) if ref_candidates else None

    sources: List[SourceFreshness] = []
    sources.append(_build_stock_panel_row(
        stock_panel_dir, trading_dates, reference_date, today))
    sources.extend(_build_index_rows(
        indices_directory, trading_dates, reference_date, today))
    sources.extend(_build_cross_asset_rows(
        cross_asset_dir, cross_asset_registry, trading_dates, reference_date, today,
        primary_dir=indices_directory))
    sources.append(_build_sector_constituents_row(sector_constituents_root, today))
    sources.append(_build_index_weights_row(index_weights_root, today))
    if include_token:
        sources.append(_build_token_row(today))
    if include_db:
        sources.append(_build_trades_row(today))
        sources.extend(_build_portfolio_rows(trading_dates, reference_date, today))

    overall = _roll_up([s.status for s in sources])

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generated_for_reference_date": (
            reference_date.isoformat() if reference_date else None),
        "overall_status": overall,
        "sources": [s.to_dict() for s in sources],
    }


def _roll_up(statuses: Iterable[str]) -> str:
    worst = "fresh"
    worst_rank = 0
    for s in statuses:
        rank = _SEVERITY.get(s, 0)
        if rank > worst_rank:
            worst_rank = rank
            worst = s
    return worst
