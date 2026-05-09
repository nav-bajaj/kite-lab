"""Diff GDF vs Kite on stocks with known corporate actions.

ITC      - ITC Hotels demerger 2025-01-06 (TrueData failed to adjust)
ANGELONE - 1:9 bonus 2026-01-27 (Kite local CSV failed to adjust)
IRCTC    - 5:1 split 2021-10-28
TRENT    - control (no recent CA)
RELIANCE - control
"""
from __future__ import annotations
import asyncio, sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from data_pipeline.gdf_client import GDFClient  # noqa


SYMBOLS = ["ITC", "ANGELONE", "IRCTC", "TRENT", "RELIANCE", "SBIN"]


def load_kite(sym):
    p = ROOT / "nse500_data" / f"{sym}_day.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    df["date"] = df["date"].dt.tz_localize(None).dt.normalize()
    return df


async def main():
    end = pd.Timestamp("2026-05-09")
    start = pd.Timestamp("2020-01-01")

    async with GDFClient() as c:
        for sym in SYMBOLS:
            try:
                gdf = await c.get_history(sym, start, end)
            except Exception as e:
                print(f"\n=== {sym} ===  ERROR: {e}")
                continue
            kite = load_kite(sym)
            if kite is None or kite.empty:
                print(f"\n=== {sym} ===  no Kite file")
                continue

            m = gdf[["date","close"]].merge(kite[["date","close"]], on="date",
                                            how="inner", suffixes=("_gdf","_kite"))
            if m.empty:
                print(f"\n=== {sym} ===  no overlap")
                continue
            m["diff_pct"] = (m["close_gdf"] - m["close_kite"]) / m["close_kite"] * 100
            m["ratio"]    = m["close_gdf"] / m["close_kite"]
            m["ratio_jump"] = m["ratio"].diff().abs()

            print(f"\n=== {sym} ===  GDF rows={len(gdf)}  Kite rows={len(kite)}  overlap={len(m)}")
            print(f"  diff%     min/median/max = {m['diff_pct'].min():+.2f} / "
                  f"{m['diff_pct'].median():+.2f} / {m['diff_pct'].max():+.2f}")
            print(f"  ratio     min/median/max = {m['ratio'].min():.4f} / "
                  f"{m['ratio'].median():.4f} / {m['ratio'].max():.4f}")
            top = m.nlargest(4, "ratio_jump")[["date","close_gdf","close_kite","ratio","ratio_jump"]]
            print("  top ratio jumps:")
            for _, r in top.iterrows():
                print(f"    {r['date'].date()}  GDF={r['close_gdf']:9.2f}  Kite={r['close_kite']:9.2f}  "
                      f"ratio={r['ratio']:.4f}  jump={r['ratio_jump']:.4f}")

            (ROOT / "gdf_test").mkdir(exist_ok=True)
            m.to_csv(ROOT / "gdf_test" / f"{sym}_diff.csv", index=False)


asyncio.run(main())
