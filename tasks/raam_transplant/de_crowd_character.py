"""How does L6's character change as we de-crowd it harder?

E1 used a gentle penalty (lambda=1, ~90% overlap with L6) tuned for
risk-adjusted return. Here we push the SAME mechanism harder to buy
decorrelation and lower overlap on purpose, and watch the whole character
shift — correlation to L6, holdings overlap, volatility, drawdown, and the
book's own internal residual crowding (does it actually spread out?).

Two levers:
  lambda   strength of the diversification penalty (0 = plain L6)
  pool_k   how deep into the momentum list the greedy is allowed to reach
           for a less-correlated name (bigger = more room to diverge)

The point is not "beat L6" — it's to map the trade: how much return do we
give up for how much genuinely-different character, and is there a sweet
spot for a distinct 'de-crowded momentum' sleeve.

Run:  python tasks/raam_transplant/de_crowd_character.py
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._clean_engine import thursdays  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6, build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from residuals import build_residual_panel, avg_pairwise_corr  # noqa: E402
from e1_l6div import (  # noqa: E402
    make_l6div_score, _run_with_score, holdings_overlap, load_index_close,
    NSE500_UNIVERSE_CSV, NIFTY100_INDEX,
)

FULL = ("2009-09-01", "2026-07-20")
# (label, lambda, pool_k)
VARIANTS = [
    ("L6 (plain)", 0.0, 60),
    ("gentle (E1)", 1.0, 60),
    ("moderate", 4.0, 60),
    ("strong", 10.0, 60),
    ("strong+deep", 10.0, 120),
    ("aggressive", 20.0, 120),
    ("max+deep", 40.0, 200),
]


def perf(res, s, e):
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= pd.Timestamp(s)) & (pv.index <= pd.Timestamp(e))]
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return pv, {"cagr": round(cagr * 100, 2), "vol": round(vol * 100, 2), "dd": round(dd * 100, 2),
                "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None}


def book_crowding_avg(score_fn, resid, dates, top_n=24, window=63):
    vals = []
    for d in dates:
        s = score_fn(d)
        if s is None or s.empty:
            continue
        hold = s.sort_values(ascending=False).head(top_n).index
        win = resid.loc[:d].tail(window)[[h for h in hold if h in resid.columns]]
        c = avg_pairwise_corr(win)
        if not np.isnan(c):
            vals.append(c)
    return round(float(np.mean(vals)), 4) if vals else None


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"decrowd_char_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in nse500]
    nifty100 = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()

    l6_panels = build_momentum_panels(close_panel[cols], lookback_days=lookback_months_to_days(L6["lookback_months"]), skip_days=L6["skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=L6["vol_floor"], vol_power=L6["vol_power"], cross_sectional_zscore=L6["cross_sectional_zscore"])
    resid = build_residual_panel(close_panel[cols], nifty100)["residual"]

    diag = thursdays(calendar); diag = diag[(diag >= pd.Timestamp("2010-01-01")) & (diag <= pd.Timestamp(FULL[1]))][::2]

    l6_sfn = make_l6div_score(l6_score, resid, 0.0)
    l6_res = _run_with_score(l6_sfn, close_panel[cols], trade_panel[cols], calendar, benchmark, l6_panels, sma_200[cols], atr_20[cols], *FULL, dict(L6))
    l6_pv, _ = perf(l6_res, *FULL)
    l6_ret = l6_pv.pct_change().dropna()

    rows = []
    for label, lam, pk in VARIANTS:
        sfn = make_l6div_score(l6_score, resid, lam, pool_k=pk)
        res = _run_with_score(sfn, close_panel[cols], trade_panel[cols], calendar, benchmark, l6_panels, sma_200[cols], atr_20[cols], *FULL, dict(L6))
        pv, m = perf(res, *FULL)
        r = pv.pct_change().dropna()
        common = r.index.intersection(l6_ret.index)
        corr = round(float(r.loc[common].corr(l6_ret.loc[common])), 3) if len(common) > 30 else None
        ov = holdings_overlap(l6_sfn, sfn, diag)
        bc = book_crowding_avg(sfn, resid, diag)
        rows.append({"variant": label, "lambda": lam, "pool_k": pk, **m,
                     "corr_L6": corr, "overlap_L6_pct": ov, "book_crowding": bc})
        print(f"  {label:14s} λ={lam:<4} pool={pk:<4} -> {rows[-1]}")

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "character.csv", index=False)
    (out_dir / "character.json").write_text(json.dumps(rows, indent=2, default=str))

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n" + "=" * 84)
    print("DE-CROWDING CHARACTER MORPH (FULL 2009-2026)")
    print("=" * 84)
    print(df[["variant", "lambda", "pool_k", "cagr", "vol", "dd", "sharpe",
              "corr_L6", "overlap_L6_pct", "book_crowding"]].to_string(index=False))
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
