"""OM25 V2 OOS walkthrough on the GDF-stitched panel.

Production V2 stack (locked-in May 2026 wrap-up):
  - Composite signal: 0.5 * pct_rank(UC) + 0.5 * pct_rank(CR)
  - 252d lookback, min 220 valid obs, NO positive-return prefilter
  - Top-N=25, exit_buffer=15 (rank-out at >40)
  - Equal weight 1/N, max 7.5%, drift after entry
  - NO trailing stop, 200 DMA hard exit on weekly check
  - 20 bps slippage

Two cadences (production picks):
  - Monthly entry  (1st trading day signal)
  - Bi-weekly entry (every other Friday signal)

Runs on nse500_data_merged/ (GDF 2009-2019 + Kite 2020+) and slices each
equity curve at the OOS/IS boundary (2020-07-10 by default) to produce
period-level metrics.

Usage:
  python tasks/om25/experiments/_om25_v2_oos.py
"""
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy,
    fridays, biweekly_fridays, monthly_first_trading_day,
    score_om25_composite,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe


PRICES_DIR = ROOT / "nse500_data_merged"
UNIVERSE = ROOT / "data/static/nse500_universe.csv"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
IS_BOUNDARY = pd.Timestamp("2020-07-10")
PROD_OM25_START = pd.Timestamp("2021-02-02")  # production OM25 backtest start


def period_metrics(eq: pd.DataFrame, label: str) -> dict:
    if eq.empty:
        return {"label": label, "rows": 0}
    pv = eq.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    if rets.empty or pv.iloc[0] <= 0:
        return {"label": label, "rows": len(pv)}
    days = (pv.index[-1] - pv.index[0]).days
    yrs = max(days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    sh = (rets.mean() * 252) / vol if vol > 0 else float("nan")
    cum = pv / pv.cummax()
    return {
        "label": label,
        "start": pv.index[0].date(),
        "end": pv.index[-1].date(),
        "yrs": round(yrs, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(sh, 2),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round((cum.min() - 1) * 100, 2),
        "end_value": round(pv.iloc[-1], 2),
    }


def yearly_breakdown(eq: pd.DataFrame, label: str):
    pv = eq.set_index("date")["pv"].astype(float).sort_index()
    rows = []
    for y, gp in pv.groupby(pv.index.year):
        if len(gp) < 5:
            continue
        r = gp.pct_change().dropna()
        cagr = gp.iloc[-1] / gp.iloc[0] - 1
        vol = r.std() * math.sqrt(252)
        sh = (r.mean() * 252) / vol if vol > 0 else float("nan")
        cum = gp / gp.cummax()
        era = "OOS" if y < IS_BOUNDARY.year else ("IS-bridge" if y == IS_BOUNDARY.year else "IS")
        rows.append({"year": y, "ret_pct": round(cagr * 100, 2),
                     "vol_pct": round(vol * 100, 1),
                     "sharpe": round(sh, 2),
                     "max_dd_pct": round((cum.min() - 1) * 100, 1),
                     "era": era})
    df = pd.DataFrame(rows)
    print(f"\n--- {label} year-by-year ---")
    print(df.to_string(index=False))
    return df


def main():
    print(f"Loading prices from {PRICES_DIR}...")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)

    universe = load_universe(UNIVERSE)
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    returns_uni = close_uni.pct_change()
    print(f"Universe: {len(cols)} symbols, {close_panel.index[0].date()} -> {close_panel.index[-1].date()}")

    min_date = close_uni.index[252]
    weekly_filt = weekly_fri[weekly_fri >= min_date]

    cadences = [("monthly", monthly_first), ("biweekly", biweekly_fri)]

    all_summary_rows = []
    out_dir = ROOT / f"experiments/oos_walkthrough/om25_v2_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    for cadence_label, sig_dates in cadences:
        print(f"\n{'=' * 80}\nOM25 V2 — {cadence_label} entry\n{'=' * 80}")
        entry_filt = sig_dates[sig_dates >= min_date]
        args = {"returns_universe": returns_uni, "min_obs": 220}
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_filt, weekly_signal_dates=weekly_filt,
            signal_function=score_om25_composite, signal_function_args=args,
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=25, exit_buffer=15,
            atr_mult=0.0, atr_min_floor=0.0,
            max_weight=0.075, slippage=0.002,
            use_trailing_stop=False,
        )
        if res is None:
            print(f"  [no result for {cadence_label}]")
            continue

        eq = res["equity"]
        eq.to_csv(out_dir / f"equity_{cadence_label}.csv", index=False)
        eq["date"] = pd.to_datetime(eq["date"])

        full = period_metrics(eq, f"V2-{cadence_label} full")
        oos_2020 = period_metrics(eq[eq["date"] < IS_BOUNDARY],
                                   f"V2-{cadence_label} OOS (until 2020-07)")
        oos_2021 = period_metrics(eq[eq["date"] < PROD_OM25_START],
                                   f"V2-{cadence_label} OOS (until prod start 2021-02)")
        is_2020 = period_metrics(eq[eq["date"] >= IS_BOUNDARY],
                                  f"V2-{cadence_label} IS (from 2020-07)")
        is_2021 = period_metrics(eq[eq["date"] >= PROD_OM25_START],
                                  f"V2-{cadence_label} IS (from prod 2021-02)")

        rows = [full, oos_2020, is_2020, oos_2021, is_2021]
        for r in rows:
            print(f"  {r['label']:48s}  CAGR={r.get('cagr_pct', 'NA'):>6}%  "
                  f"Sharpe={r.get('sharpe', 'NA'):>5}  MaxDD={r.get('max_dd_pct', 'NA'):>7}%  "
                  f"yrs={r.get('yrs', 'NA')}")
            all_summary_rows.append(r)

        yearly_breakdown(eq, f"V2-{cadence_label}")

    summary_df = pd.DataFrame(all_summary_rows)
    summary_df.to_csv(out_dir / "v2_oos_summary.csv", index=False)
    print(f"\n[wrote] {out_dir}/v2_oos_summary.csv")


if __name__ == "__main__":
    main()
