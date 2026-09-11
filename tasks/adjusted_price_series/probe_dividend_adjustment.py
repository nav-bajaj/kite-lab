"""Decide empirically whether Kite's historical feed is dividend-adjusted.

Non-destructive: fetches into memory, compares against the stored panel,
writes nothing to nse500_data/.

Method: our panel is append-only, so its old rows are a frozen snapshot of
Kite's adjustment state at download time. Re-fetching the same old dates now
and diffing isolates whatever adjustment Kite has applied since.

Read the result off the CONTROL group. High-dividend names diverging while
zero-dividend names match exactly is the signature of dividend adjustment.
Everything diverging by a similar amount is something else (a split, a
data revision) and is NOT evidence of dividend adjustment.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import pandas as pd
from history_utils import fetch_history, init_kite_client

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "nse500_data"

# High, regular dividend payers — expected to diverge if dividends are adjusted
HIGH_YIELD = ["COALINDIA", "HINDZINC", "IOC", "ONGC", "POWERGRID", "NTPC", "ITC"]
# Zero / negligible dividend — the control. These should match exactly either way.
CONTROL = ["DMART", "ADANIENT", "TRENT"]

START, END = "2020-01-01", "2020-03-01"


def compare(kite, symbol):
    stored_path = PANEL / f"{symbol}_day.csv"
    if not stored_path.exists():
        return None
    stored = (pd.read_csv(stored_path, parse_dates=["date"])
                .drop_duplicates("date").set_index("date")["close"])
    live = fetch_history(kite, symbol, START, END, interval="day")
    if live.empty:
        return None
    live["date"] = pd.to_datetime(live["date"]).dt.tz_localize(None).dt.normalize()
    live = live.drop_duplicates("date").set_index("date")["close"]

    both = pd.concat([stored.rename("stored"), live.rename("live")], axis=1).dropna()
    both = both[(both.index >= START) & (both.index <= END)]
    if both.empty:
        return None
    ratio = (both["live"] / both["stored"])
    return {
        "symbol": symbol, "days": len(both),
        "stored": round(both["stored"].iloc[0], 2),
        "live": round(both["live"].iloc[0], 2),
        "mean_ratio": round(ratio.mean(), 5),
        "spread": round(ratio.max() - ratio.min(), 5),
    }


def main():
    kite = init_kite_client()
    for label, syms in (("HIGH-YIELD", HIGH_YIELD), ("CONTROL (no dividend)", CONTROL)):
        print(f"\n=== {label} — stored vs live, {START}..{END} ===")
        print(f"{'symbol':<12}{'days':>5}{'stored':>10}{'live':>10}{'live/stored':>13}{'spread':>10}")
        for s in syms:
            try:
                r = compare(kite, s)
            except Exception as exc:
                print(f"{s:<12}  ERROR: {exc}")
                continue
            if r is None:
                print(f"{s:<12}  no overlap")
                continue
            print(f"{r['symbol']:<12}{r['days']:>5}{r['stored']:>10}{r['live']:>10}"
                  f"{r['mean_ratio']:>13}{r['spread']:>10}")

    print("""
Reading the result
------------------
  All ratios ~1.0000            -> feed is NOT dividend-adjusted. Nothing to
                                   defend; our panel already matches the feed.
  High-yield < 1.0, control 1.0 -> feed IS dividend-adjusted. Our stored history
                                   is price-return and must be protected from
                                   any re-download.
  Everything shifted alike      -> not dividends. Investigate before concluding.
""")


if __name__ == "__main__":
    main()
