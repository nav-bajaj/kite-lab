"""Phase 0.2 — reproduce the L6 v2 production baseline.

Validates the research harness against the published numbers in
docs/portfolios.md BEFORE any raam_transplant experiment is trusted:

    L6 v2 (2020-07-10 → 2026-02-02, IS-only tune):
        CAGR 59.4% · Sharpe 1.92 · MaxDD -30.0% · turnover 123% · hit 49.3%

If this window reproduces within tolerance (~1pp CAGR / ~0.05 Sharpe,
allowing for the newer/refreshed panel), the harness is sound and the
four research-window rows below become the L6 comparator every
experiment (E1/E2/E3) is judged against.

L6 config is the locked production BASELINE from _momentum_engine.py:
NSE 500, 126d vol-adjusted momentum, weekly Thursday signal → Friday
OHLC/4, top-24, min-hold 8d, no stop, no regime overlay, 20bps slippage.

Run:
    python tasks/raam_transplant/baseline_l6.py
Writes tasks/raam_transplant/runs/baseline_l6_<ts>/summary.csv + equity CSVs.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6_BASELINE, build_momentum_panels, run_momentum,
    lookback_months_to_days,
)

NSE500_UNIVERSE_CSV = "data/static/nse500_universe.csv"

# Docs-parity window (validation) + the four research windows (record).
DOCS_WINDOW = ("DOCS_2020-2026", "2020-07-10", "2026-02-02")
RESEARCH_WINDOWS = [
    ("IS",    "2009-09-01", "2016-12-31"),
    ("OOS-A", "2017-01-01", "2019-12-31"),
    ("OOS-B", "2020-01-01", "2022-12-31"),
    ("OOS-C", "2023-01-01", "2026-07-20"),  # extended to the refreshed panel edge
    ("ERA-2021plus", "2021-01-01", "2026-07-20"),
]

DOCS_TARGET = {"cagr_pct": 59.4, "sharpe": 1.92, "max_dd_pct": -30.0,
               "turnover_pct": 123.0, "hit_pct": 49.3}


def metrics_from_result(result, active_start, active_end) -> dict:
    """CAGR/Sharpe/MaxDD/Calmar/vol from the equity curve (rf=5% to match
    the convention docs/portfolios.md and om25_alt reproduced under), plus
    annualized turnover and hit rate from the trade log."""
    eq = result["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= active_start) & (pv.index <= active_end)]
    if len(pv) < 2:
        return {"error": "short_pv"}

    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    dd = (pv / pv.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd < 0 else np.nan

    trades = result.get("trades")
    n_buys = int((trades["side"] == "BUY").sum()) if trades is not None and not trades.empty else 0
    # Annualized turnover = buy notional / avg capital / years.
    turnover_pct = None
    hit_pct = None
    if trades is not None and not trades.empty:
        buys = trades[trades["side"] == "BUY"]
        if "notional" in trades.columns and len(buys):
            avg_pv = pv.mean()
            turnover_pct = round(buys["notional"].sum() / avg_pv / years * 100, 1)
        sells = trades[trades["side"] == "SELL"]
        if "pnl_pct" in sells.columns and len(sells):
            hit_pct = round((sells["pnl_pct"] > 0).mean() * 100, 1)

    return {
        "start": str(pv.index[0].date()), "end": str(pv.index[-1].date()),
        "years": round(years, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(sharpe, 3),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(dd * 100, 2),
        "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None,
        "turnover_pct": turnover_pct,
        "hit_pct": hit_pct,
        "n_buys": n_buys,
    }


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"baseline_l6_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] price panels from nse500_data_merged")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    print(f"       panel: {close_panel.shape[1]} symbols, "
          f"{calendar[0].date()} → {calendar[-1].date()}")

    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200_panel = close_panel.rolling(200, min_periods=200).mean()
    atr_20_panel = close_panel.pct_change().rolling(20).std()

    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    nse500_cols = [s for s in close_panel.columns if s in nse500]
    print(f"       NSE 500 universe: {len(nse500_cols)} symbols in panel")

    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(L6_BASELINE["lookback_months"]),
        skip_days=L6_BASELINE["skip_days"],
    )

    rows = []
    all_windows = [DOCS_WINDOW] + RESEARCH_WINDOWS
    for wname, start_s, end_s in all_windows:
        print(f"  [run] {wname}  {start_s} → {end_s}")
        res = run_momentum(
            close_panel=close_panel[nse500_cols], trade_panel=trade_panel[nse500_cols],
            calendar=calendar, benchmark_aligned=benchmark, panels=l6_panels,
            sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
            start=start_s, end=end_s, config=dict(L6_BASELINE),
        )
        if res is None:
            rows.append({"window": wname, "error": "no_entry_dates"})
            continue
        res["equity"].to_csv(out_dir / f"{wname}_equity.csv", index=False)
        m = metrics_from_result(res, pd.Timestamp(start_s), pd.Timestamp(end_s))
        rows.append({"window": wname, **m})

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False)

    # Docs-parity check
    docs_row = next((r for r in rows if r["window"] == DOCS_WINDOW[0]), None)
    deltas = {}
    if docs_row and "cagr_pct" in docs_row:
        for k, tgt in DOCS_TARGET.items():
            got = docs_row.get(k)
            if got is not None:
                deltas[k] = {"target": tgt, "got": got, "delta": round(got - tgt, 2)}
    (out_dir / "docs_parity.json").write_text(json.dumps(deltas, indent=2))

    pd.set_option("display.width", 160, "display.max_columns", 20)
    print("\n" + "=" * 70)
    print("L6 v2 baseline — reproduction")
    print("=" * 70)
    cols = ["window", "start", "end", "years", "cagr_pct", "sharpe",
            "max_dd_pct", "calmar", "turnover_pct", "hit_pct", "n_buys"]
    print(summary[[c for c in cols if c in summary.columns]].to_string(index=False))
    print("\nDocs-parity (target → got → delta):")
    for k, v in deltas.items():
        print(f"  {k:14s} {v['target']:>7} → {v['got']:>7}  ({v['delta']:+})")
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
