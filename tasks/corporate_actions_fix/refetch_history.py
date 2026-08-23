"""Path A repair: full-depth adjusted refetch from Kite for damaged
symbols, rebuilding both the live and merged CSVs.

Kite serves history adjusted as of today, so a deep refetch is the
authoritative repair for splits/bonuses (demergers are NOT price-
adjusted by Kite — those stay in corporate_actions.json). Needs a live
access token (run on a trading morning after pipeline login, or on the
Railway volume where the pipeline runs).

Usage:
  --probe-depth SYMBOL   check how far back Kite serves day candles
  --symbols A,B,C        repair these symbols
  --from-inventory       repair every CA-signature symbol in inventory.csv
  --start 2009-01-01     fetch start (default)
  --apply                actually write (default is dry-run reporting)

Run:  .venv/bin/python tasks/corporate_actions_fix/refetch_history.py --probe-depth RELIANCE
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
for p in (str(ROOT), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from history_utils import fetch_history, init_kite_client  # noqa: E402

LIVE_DIR = ROOT / "nse500_data"
MERGED_DIR = ROOT / "nse500_data_merged"
INVENTORY = Path(__file__).resolve().parent / "inventory.csv"
COLS = ["date", "open", "high", "low", "close", "volume"]


def fetch_day_candles(kite, symbol: str, start: pd.Timestamp,
                      end: pd.Timestamp) -> pd.DataFrame:
    """Full-depth day candles via the shared chunked fetcher."""
    df = fetch_history(kite, symbol, start, end, interval="day")
    if df is None or df.empty:
        return pd.DataFrame(columns=COLS)
    return df[COLS]


def repair_symbol(kite, symbol: str, start: pd.Timestamp, apply: bool) -> str:
    """Kite's freshly-served history is authoritative: it reproduces real
    crashes identically and serves CA-adjusted prices. Compare against
    the stored merged file to report what actually changes, then (with
    --apply) replace both stores."""
    fresh = fetch_day_candles(kite, symbol, start, pd.Timestamp.today())
    if fresh.empty:
        return "no_data"
    merged_f = MERGED_DIR / f"{symbol}_day.csv"
    n_diff, n_common = 0, 0
    if merged_f.exists():
        stored = pd.read_csv(merged_f, parse_dates=["date"]).set_index("date")["close"]
        fs = fresh.set_index("date")["close"]
        common = stored.index.intersection(fs.index)
        n_common = len(common)
        if n_common:
            n_diff = int((abs(fs.loc[common] / stored.loc[common] - 1) > 0.005).sum())
        # guard against a truncated response wiping stored history
        if len(fs) < 0.60 * len(stored):
            return (f"refused: fresh depth {len(fs)} rows vs stored "
                    f"{len(stored)} — raise --start or fall back to Path B")
    verdict = ("no_op: fresh matches stored — real events, no CA"
               if n_common and n_diff == 0 else
               f"{n_diff}/{n_common} stored rows differ (CA re-base)")
    if not apply:
        return (f"dry_run: {len(fresh)} rows "
                f"{fresh.date.min().date()}..{fresh.date.max().date()}; {verdict}")
    live_rows = fresh[fresh.date >= pd.Timestamp("2020-01-01")]
    live_rows.to_csv(LIVE_DIR / f"{symbol}_day.csv", index=False)
    fresh.to_csv(MERGED_DIR / f"{symbol}_day.csv", index=False)
    return f"repaired ({verdict}): live {len(live_rows)} rows, merged {len(fresh)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-depth")
    ap.add_argument("--symbols")
    ap.add_argument("--from-inventory", action="store_true")
    ap.add_argument("--start", default="2009-01-01")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    kite = init_kite_client()
    start = pd.Timestamp(args.start)

    if args.probe_depth:
        df = fetch_day_candles(kite, args.probe_depth, pd.Timestamp("2005-01-01"),
                               pd.Timestamp.today())
        print(f"{args.probe_depth}: {len(df)} day candles, "
              f"earliest {df.date.min().date() if len(df) else 'none'}")
        return

    if args.from_inventory:
        inv = pd.read_csv(INVENTORY)
        symbols = sorted(inv[inv.definitive].symbol.unique())
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        ap.error("need --symbols, --from-inventory, or --probe-depth")

    print(f"{'Repairing' if args.apply else 'Dry-run over'} {len(symbols)} symbols "
          f"from {start.date()}")
    for sym in symbols:
        try:
            print(f"  {sym:14s} {repair_symbol(kite, sym, start, args.apply)}")
        except Exception as exc:
            print(f"  {sym:14s} FAILED: {exc}")


if __name__ == "__main__":
    main()
