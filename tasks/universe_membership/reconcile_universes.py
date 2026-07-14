"""Reconcile fresh NSE index lists (2026-07-14) against data/static universes.

For each universe: report additions, removals, and renames. A rename is an
ISIN present in both old and new lists under different symbols, or a symbol
covered by scripts.history_utils.SYMBOL_ALIASES (fetch-layer aliases for
tickers that changed on NSE). Also checks local price-file coverage for
additions so we know what to fetch before cutover.

Read-only: writes nothing outside tasks/universe_membership/.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
NEW_DIR = Path(__file__).resolve().parent / "data" / "nse_lists_2026-07-14"
STATIC = ROOT / "data" / "static"
PRICES = Path("/Users/navdeep/Documents/stock_data/nse500_data")

# old universe file -> new NSE list (nifty50 has no old file: fully new)
PAIRS = [
    ("nse500_universe.csv", "ind_nifty500list.csv", "nse500"),
    ("nifty250_universe.csv", "ind_nifty250list.csv", "nifty250"),
    ("nifty100_universe.csv", "ind_nifty100list.csv", "nifty100"),
    (None, "ind_nifty50list.csv", "nifty50"),
]

SYMBOL_ALIASES = {
    "RELINFRA": "RELINFRA-BE",
    "AKZOINDIA": "JSWDULUX",
    "LTIM": "LTM",
}
ALIAS_REVERSE = {v: k for k, v in SYMBOL_ALIASES.items()}


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    if "ISIN Code" in df.columns:
        df["ISIN Code"] = df["ISIN Code"].astype(str).str.strip()
    return df


for old_name, new_name, uid in PAIRS:
    new = load(NEW_DIR / new_name)
    print(f"\n{'=' * 70}\n[{uid}] new list: {len(new)} rows", end="")
    if old_name is None:
        print(" — NEW UNIVERSE (no existing file)")
        missing = [s for s in new["Symbol"]
                   if not (PRICES / f"{s}_day.csv").exists()
                   and not (PRICES / f"{SYMBOL_ALIASES.get(s, s)}_day.csv").exists()
                   and not (PRICES / f"{ALIAS_REVERSE.get(s, s)}_day.csv").exists()]
        print(f"  price files missing: {missing or 'none'}")
        continue

    old = load(STATIC / old_name)
    print(f" | old file: {len(old)} rows")

    old_by_isin = dict(zip(old["ISIN Code"], old["Symbol"])) if "ISIN Code" in old.columns else {}
    new_by_isin = dict(zip(new["ISIN Code"], new["Symbol"]))
    old_syms, new_syms = set(old["Symbol"]), set(new["Symbol"])

    renames = []
    # same ISIN, different symbol
    for isin, osym in old_by_isin.items():
        nsym = new_by_isin.get(isin)
        if nsym and nsym != osym:
            renames.append((osym, nsym, "isin"))
    # fetch-layer aliases not already caught by ISIN
    for osym, nsym in SYMBOL_ALIASES.items():
        if osym in old_syms and nsym in new_syms and (osym, nsym, "isin") not in renames:
            renames.append((osym, nsym, "alias"))

    renamed_old = {r[0] for r in renames}
    renamed_new = {r[1] for r in renames}

    added = sorted(new_syms - old_syms - renamed_new)
    removed = sorted(old_syms - new_syms - renamed_old)

    print(f"  renames ({len(renames)}):")
    for osym, nsym, how in sorted(renames):
        print(f"    {osym:<12} -> {nsym:<12} [{how}]")
    print(f"  added ({len(added)}):")
    for s in added:
        name = new.loc[new["Symbol"] == s, "Company Name"].iloc[0]
        have = (PRICES / f"{s}_day.csv").exists()
        rows = 0
        if have:
            rows = sum(1 for _ in open(PRICES / f"{s}_day.csv")) - 1
        print(f"    {s:<12} {name[:45]:<46} prices: {'%4d rows' % rows if have else 'MISSING'}")
    print(f"  removed ({len(removed)}):")
    for s in removed:
        name = old.loc[old["Symbol"] == s, "Company Name"].iloc[0] if "Company Name" in old.columns else ""
        print(f"    {s:<12} {name[:45]}")
