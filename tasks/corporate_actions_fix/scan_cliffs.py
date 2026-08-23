"""Inventory corporate-action cliffs across both price dirs.

Scans every *_day.csv in nse500_data/ (live) and nse500_data_merged/
(deep history) for adjacent-close moves beyond the cliff threshold,
classifies each against known CA ratios, and writes inventory.csv.

Run:  .venv/bin/python tasks/corporate_actions_fix/scan_cliffs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.corporate_actions_fix.ca_lib import (  # noqa: E402
    classify_cliffs, definitive_ca_mask, detect_cliffs,
)

OUT = Path(__file__).resolve().parent / "inventory.csv"
DIRS = {"live": ROOT / "nse500_data", "merged": ROOT / "nse500_data_merged"}


def main():
    rows = []
    for dname, d in DIRS.items():
        for f in sorted(d.glob("*_day.csv")):
            sym = f.name[: -len("_day.csv")]
            df = pd.read_csv(f, parse_dates=["date"]).set_index("date")
            c = classify_cliffs(detect_cliffs(df["close"]))
            if c.empty:
                continue
            c["definitive"] = definitive_ca_mask(c)
            for r in c.itertuples():
                rows.append(dict(dir=dname, symbol=sym, date=str(r.date.date()),
                                 move_pct=r.move_pct, ratio=round(r.ratio, 4),
                                 label=r.label, definitive=bool(r.definitive)))
    inv = pd.DataFrame(rows).sort_values(["symbol", "date", "dir"])
    inv.to_csv(OUT, index=False)

    print(f"{len(inv)} cliffs across {inv.symbol.nunique()} symbols "
          f"-> {OUT.relative_to(ROOT)}")
    print("\nby label:")
    print(inv.groupby("label").size().sort_values(ascending=False).to_string())
    print("\nDEFINITIVE corporate-action damage (auto-repair set):")
    sig = inv[inv.definitive]
    print(sig.to_string(index=False) if len(sig) else "  none")
    amb = inv[(inv.label != "unclassified") & ~inv.definitive]
    print(f"\nambiguous ratio-matches, isolated ±28-40% (verify vs Kite "
          f"before touching): {len(amb)} rows, "
          f"{amb.symbol.nunique()} symbols")
    print(amb.groupby('symbol').size().to_string() if len(amb) else "  none")
    unc = inv[inv.label == "unclassified"]
    print(f"\nunclassified (real crashes or demergers): {len(unc)} rows — "
          "kept as data unless manually actioned")


if __name__ == "__main__":
    main()
