"""§2 runner — build the signal tape across the whole point-in-time universe.

Writes data/signals_<tier>.csv plus a summary of the E1/E2/failed-poke split,
which is the quantity that sizes the competitor's entry bias.
"""
from __future__ import annotations

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from signals import scan_symbol  # noqa: E402

REPO = "/Users/navdeep/kite-lab"
TASK = f"{REPO}/tasks/breakout_calls_2026"
PIT = os.environ.get("PIT_UNIVERSE", f"{TASK}/data/pit_universe.parquet")


def main():
    os.chdir(REPO)
    pit = pd.read_parquet(PIT, columns=["date", "symbol", "eligible"])
    pit = pit[pit.eligible]
    elig_by_sym = {s: set(g.date) for s, g in pit.groupby("symbol", sort=False)}
    syms = sorted(elig_by_sym)
    print(f"scanning {len(syms):,} symbols that were ever eligible", flush=True)

    rows = []
    for i, s in enumerate(syms, 1):
        try:
            rows.extend(scan_symbol(s, elig_by_sym[s]))
        except Exception as e:                      # one bad series must not kill the run
            print(f"  !! {s}: {type(e).__name__}: {e}", flush=True)
        if i % 250 == 0:
            print(f"  {i}/{len(syms)}  events so far {len(rows):,}", flush=True)

    df = pd.DataFrame(rows)
    os.makedirs(f"{TASK}/data", exist_ok=True)
    df.to_csv(f"{TASK}/data/signals_standard_no_l6.csv", index=False)
    print(f"\nwrote {len(df):,} events -> data/signals_standard_no_l6.csv")
    if len(df):
        print(df.kind.value_counts().to_string())
        e1 = df[df.kind == "E1"]
        print(f"\nE1 events: {len(e1):,}")
        print(f"  on a base that never confirmed (failed poke): {e1.failed_poke.sum():,} "
              f"({e1.failed_poke.mean():.1%})")
        print(f"  filled on a bar that closed above the pivot : {e1.confirmed_same_bar.mean():.1%}")
        print("\nevents per year:")
        print(df.groupby(["year", "kind"]).size().unstack(fill_value=0).to_string())


if __name__ == "__main__":
    main()
