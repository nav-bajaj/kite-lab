"""Fetch USDINR, Gold, and Crude OHLC history via Kite Connect.

DIAGNOSTIC NOTE (2026-05-29): the initial probe revealed MCXGOLDEX and
MCXCRUDEX (the MCX spot-equivalent INDEX segment) only return the
single most-recent day via `historical_data`, NOT proper history.
Kite Connect's history endpoint does NOT support index series in the
MCX INDICES segment. Likewise, USDINR's `continuous=True` flag only
works on the MONTHLY contract token (e.g., USDINR26JUNFUT), not the
weekly expiries.

Working configuration:

  - GOLD       — token 117574919 (GOLD26JUNFUT), continuous=True
                  Stitched front-month MCX gold future; verified ~15y
                  of history available (back to Oct 2010)
  - CRUDEOIL   — token 127768327 (CRUDEOIL26JUNFUT), continuous=True
                  Stitched front-month MCX crude oil future
  - USDINR     — token 1689859 (USDINR26JUNFUT), continuous=True
                  Stitched front-month NSE CDS USDINR future

IMPORTANT: the instrument tokens above are SPECIFIC monthly contracts
that will eventually expire. The continuous=True flag tells the API to
return the stitched-front-month series for that CONTRACT FAMILY, but
the token still has to point at a valid contract. Before each fetch
this script verifies the token is still in `data/instruments_full.csv`;
if not, it picks the next active monthly contract for the same family.
For the production daily pipeline, regenerate `instruments_full.csv`
first.

USAGE
-----
    # Quick probe — last 90 days only, to verify shape
    python scripts/fetch_cross_asset_history.py --probe

    # Full history
    python scripts/fetch_cross_asset_history.py --from 2010-01-01

OUTPUT
------
Writes CSVs to the `indices_data_full/` directory, resolved at runtime
(see `_resolve_output_dir`): `$KITE_BACKUP_SOURCE_ROOT/indices_data_full`
on Railway (the mounted /data volume), `~/Documents/stock_data/indices_data_full`
on the Mac. Schema: `date,open,high,low,close,volume` — matches the
existing index files so `cross_asset.py` picks them up automatically.

After a successful fetch, clear the cross_asset engine cache and the
snapshot's USDINR / gold / crude entries will populate with real data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import pandas as pd

# Bootstrap so `from history_utils import ...` works
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from history_utils import init_kite_client, to_local_naive  # noqa: E402


# Where the rest of the index CSVs live. Keep these in lockstep with the
# reader at kite-api/app/insights/cross_asset.py (_resolve_indices_dir).
#
# This used to be a hardcoded Mac absolute path, which crashed the daily
# pipeline on Railway: the job runs as the non-root `appuser`, so
# `mkdir(parents=True)` on /Users/... raised PermissionError after ~1.5s —
# the "Fetch cross-asset data: FAILED (1.5s)" the daily cron kept reporting.
# Resolve it instead so it lands on the persistent volume in prod and stays
# put on the Mac.
def _resolve_output_dir() -> Path:
    # 1. Explicit override wins (tests, ad-hoc backfills).
    override = os.environ.get("CROSS_ASSET_OUTPUT_DIR")
    if override:
        return Path(override)
    # 2. Railway: KITE_BACKUP_SOURCE_ROOT is set to /data (the mounted volume),
    #    which is also where upload_to_gdrive.py reads indices_data_full from.
    root = os.environ.get("KITE_BACKUP_SOURCE_ROOT")
    if root:
        return Path(root) / "indices_data_full"
    # 3. Railway volume present but env unset — still land on the volume.
    if Path("/data").is_dir():
        return Path("/data") / "indices_data_full"
    # 4. Mac-local default (unchanged from the original hardcoded path).
    return Path.home() / "Documents" / "stock_data" / "indices_data_full"


OUTPUT_DIR = _resolve_output_dir()


# Asset → (instrument_token, exchange/segment label, kite kwargs)
# The instrument tokens below are pulled from `data/instruments_full.csv`
# at the time this script was written. If Kite Connect rotates them
# (rare for indices, more common for individual futures contracts),
# update them by grepping the instruments file:
#   grep "MCXGOLDEX\|MCXCRUDEX" data/instruments_full.csv
#   grep "USDINR.*FUT," data/instruments_full.csv | head -1
ASSETS: dict[str, dict] = {
    "GOLD": {
        "instrument_name": "GOLD",          # name field in instruments_full.csv
        "segment": "MCX-FUT",
        "monthly_suffix": "FUT",            # picks GOLD26JUNFUT, not the weekly variants
        "fallback_token": 117574919,        # GOLD26JUNFUT — used if dynamic resolution fails
        "continuous": True,
        "description": "Continuous front-month MCX gold future (INR per 10g)",
    },
    "CRUDEOIL": {
        "instrument_name": "CRUDEOIL",
        "segment": "MCX-FUT",
        "monthly_suffix": "FUT",
        "fallback_token": 127768327,
        "continuous": True,
        "description": "Continuous front-month MCX crude oil future (INR per barrel)",
    },
    "USDINR": {
        "instrument_name": "USDINR",
        "segment": "CDS-FUT",
        "monthly_suffix": "FUT",            # picks USDINR26JUNFUT, not the weekly DDMMFUTs
        "fallback_token": 1689859,
        "continuous": True,
        "description": "Continuous front-month USDINR future",
    },
}


_MONTH_TOKEN_RE = __import__("re").compile(
    r"^(?P<name>[A-Z]+)(?P<yr>\d{2})(?P<mon>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)FUT$"
)


def _resolve_active_monthly_token(cfg: dict, today: dt.date) -> int:
    """Find the soonest non-expired MONTHLY contract for the asset family.

    Reads `data/instruments_full.csv` and looks for tradingsymbols matching
    `<NAME><YY><MMM>FUT` (e.g., USDINR26JUNFUT, GOLD26AUGFUT). Picks the
    contract with the earliest expiry that is >= today. Falls back to the
    hardcoded token if anything goes wrong (file missing, no matches, etc.).
    """
    fallback = cfg["fallback_token"]
    instruments_path = Path("data/instruments_full.csv")
    if not instruments_path.exists():
        print(f"  ! instruments_full.csv missing — using fallback token {fallback}")
        return fallback
    try:
        df = pd.read_csv(instruments_path)
    except Exception as exc:
        print(f"  ! could not read instruments_full.csv ({exc}) — fallback {fallback}")
        return fallback

    df = df[df["segment"] == cfg["segment"]]
    df = df[df["name"] == cfg["instrument_name"]]
    df = df[df["tradingsymbol"].astype(str).str.match(_MONTH_TOKEN_RE)]
    if df.empty:
        print(f"  ! no monthly contracts found for {cfg['instrument_name']} — fallback {fallback}")
        return fallback

    df = df.copy()
    df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")
    df = df.dropna(subset=["expiry"])
    df = df[df["expiry"].dt.date >= today]
    if df.empty:
        print(f"  ! all monthly contracts expired for {cfg['instrument_name']} — fallback {fallback}")
        return fallback

    chosen = df.sort_values("expiry").iloc[0]
    sym = chosen["tradingsymbol"]
    token = int(chosen["instrument_token"])
    print(f"  resolved active monthly contract: {sym} (token {token}, expiry {chosen['expiry'].date()})")
    return token


def _fetch_one(kite, name: str, cfg: dict,
               start: pd.Timestamp, end: pd.Timestamp,
               today: dt.date) -> pd.DataFrame:
    """Fetch one asset with chunked requests. Kite Connect caps single
    historical requests at ~2000 days for daily data, so we chunk.

    Resolves the active monthly contract token dynamically — the
    `continuous=True` flag still does the front-month stitching, but
    the API requires the anchor token to be a valid (non-expired)
    contract.
    """
    token = _resolve_active_monthly_token(cfg, today)
    print(f"\n[{name}] {cfg['segment']} · token={token} · continuous={cfg['continuous']}")
    print(f"  fetching {start.date()} → {end.date()} …")

    chunk_days = 1900
    cur = start
    frames: list[pd.DataFrame] = []
    while cur < end:
        chunk_end = min(cur + pd.Timedelta(days=chunk_days), end)
        try:
            candles = kite.historical_data(
                instrument_token=token,
                from_date=cur.to_pydatetime(),
                to_date=(chunk_end + pd.Timedelta(days=1)).to_pydatetime(),
                interval="day",
                continuous=cfg["continuous"],
                oi=False,
            )
        except Exception as exc:
            print(f"  ! chunk {cur.date()}→{chunk_end.date()} failed: {exc}")
            cur = chunk_end
            continue
        if candles:
            frames.append(pd.DataFrame(candles))
            print(f"  chunk {cur.date()}→{chunk_end.date()}: {len(candles)} candles")
        else:
            print(f"  chunk {cur.date()}→{chunk_end.date()}: empty")
        cur = chunk_end

    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["date"] = to_local_naive(df["date"])
    df = (df.sort_values("date")
            .drop_duplicates(subset=["date"])
            .reset_index(drop=True))
    # Keep only the columns our schema expects
    keep = ["date", "open", "high", "low", "close", "volume"]
    keep = [c for c in keep if c in df.columns]
    return df[keep]


def _last_date(out_path: Path) -> pd.Timestamp | None:
    """Return the last date in an existing CSV, or None if file missing."""
    if not out_path.exists():
        return None
    try:
        df = pd.read_csv(out_path, usecols=["date"], parse_dates=["date"])
        if df.empty:
            return None
        return df["date"].max()
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="from_date", default=None,
                    help="Start date YYYY-MM-DD. Default: 90 days back (probe mode).")
    ap.add_argument("--probe", action="store_true",
                    help="Probe mode — fetch last 90 days only, regardless of --from.")
    ap.add_argument("--incremental", action="store_true",
                    help="Incremental mode — for each asset, fetch only dates after "
                         "the most recent date already in its CSV. Used by the daily "
                         "pipeline. Falls back to a 90-day probe if the CSV is missing.")
    ap.add_argument("--to", dest="to_date", default=None,
                    help="End date YYYY-MM-DD. Default: today.")
    ap.add_argument("--out-dir", default=str(OUTPUT_DIR),
                    help=f"Output directory. Default: {OUTPUT_DIR}")
    args = ap.parse_args()

    today = dt.date.today()
    end = pd.Timestamp(args.to_date) if args.to_date else pd.Timestamp(today)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine the global start date for the run. In incremental mode,
    # each asset uses its own per-CSV last-date.
    if args.incremental:
        global_start = None  # Per-asset below
    elif args.probe or args.from_date is None:
        global_start = pd.Timestamp(today) - pd.Timedelta(days=90)
    else:
        global_start = pd.Timestamp(args.from_date)

    print(f"=== fetch_cross_asset_history ===")
    print(f"Mode: {'incremental' if args.incremental else 'probe' if args.probe else 'full'}")
    print(f"End date: {end.date()}")
    print(f"Output dir: {out_dir}")

    kite = init_kite_client()

    summary: list[tuple[str, int, str | None]] = []
    for name, cfg in ASSETS.items():
        out_path = out_dir / f"{name}.csv"

        if args.incremental:
            last = _last_date(out_path)
            if last is None:
                # CSV missing — fall back to 90 day probe so daily-pipeline
                # bootstrap is graceful. For full history, run with --from.
                start = pd.Timestamp(today) - pd.Timedelta(days=90)
                print(f"\n[{name}] CSV missing — bootstrapping last 90 days")
            else:
                start = last + pd.Timedelta(days=1)
                if start >= end:
                    print(f"\n[{name}] up-to-date ({last.date()})")
                    summary.append((name, 0, "up-to-date"))
                    continue
        else:
            start = global_start

        new_df = _fetch_one(kite, name, cfg, start, end, today)
        if new_df.empty:
            print(f"[{name}] no new candles")
            summary.append((name, 0, None))
            continue

        if args.incremental and out_path.exists():
            # Append: read existing, concat, dedupe on date, sort
            existing = pd.read_csv(out_path, parse_dates=["date"])
            merged = (pd.concat([existing, new_df], ignore_index=True)
                        .drop_duplicates(subset=["date"])
                        .sort_values("date"))
            merged.to_csv(out_path, index=False)
            added = len(merged) - len(existing)
            print(f"[{name}] appended {added} new rows (total {len(merged)})")
            summary.append((name, added,
                            f"+{added} new (last={merged['date'].max().date()})"))
        else:
            new_df.to_csv(out_path, index=False)
            date_range = f"{new_df['date'].min().date()} → {new_df['date'].max().date()}"
            print(f"[{name}] wrote {len(new_df)} rows ({date_range}) to {out_path}")
            summary.append((name, len(new_df), date_range))

    print("\n=== Summary ===")
    for name, n, date_range in summary:
        print(f"  {name:<12} {n:>5} rows   {date_range or '— no data'}")


if __name__ == "__main__":
    main()
