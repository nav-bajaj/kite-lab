"""Low-volatility revisited — as a conservative sleeve, not a momentum rival.

om25_alt already showed a naive low-vol strategy (LV25) is decorrelated but
low-return, and rejected it on a momentum-style bar (Sharpe 1.5+/CAGR 30%+).
This revisit changes the QUESTION: is there a low-vol strategy with a
genuinely different character — low correlation to L6, materially lower
drawdown/vol — that a conservative investor would prefer to just holding
the NIFTY 100? Lower CAGR than momentum is acceptable; a smoother ride is
the product.

Two paper-faithful choices distinguish this from LV25:
  1. Volatility is EWMA(lambda=0.94) (RiskMetrics), the paper's V estimator,
     not plain 252d realized std.
  2. The paper warns raw low-vol is "blind to trend" and overweights
     declining low-vol names. So LV_TREND ranks low-vol only among names in
     an uptrend (close > 200-DMA AND positive 126d momentum) — low-vol done
     the paper's way (V paired with T).

Variants: LV_NAIVE, LV_TREND, and LV_TREND + 20%-from-peak drawdown stop
(a conservative product wants explicit downside protection). All vs L6 and
a NIFTY 100 buy-and-hold reference, on the four windows, net of 20bps.

Run:  python tasks/raam_transplant/lv_revisit.py
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
from scripts._clean_engine import run_strategy, thursdays  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from e1_l6div import load_index_close, holdings_overlap, NSE500_UNIVERSE_CSV, NIFTY100_INDEX  # noqa: E402

WINDOWS = [
    ("IS", "2009-09-01", "2016-12-31"),
    ("OOS-A", "2017-01-01", "2019-12-31"),
    ("OOS-B", "2020-01-01", "2022-12-31"),
    ("OOS-C", "2023-01-01", "2026-07-20"),
    ("FULL", "2009-09-01", "2026-07-20"),
]
TOP_N = 24
EWMA_LAMBDA = 0.94
VOL_MIN_OBS = 220


def ewma_vol_panel(returns: pd.DataFrame, lam: float = EWMA_LAMBDA) -> pd.DataFrame:
    """Annualised EWMA volatility (RiskMetrics). Lower = calmer."""
    var = returns.pow(2).ewm(alpha=1 - lam, min_periods=VOL_MIN_OBS).mean()
    return np.sqrt(var) * math.sqrt(252)


def make_lv_score(ewma_vol: pd.DataFrame, returns_252: pd.DataFrame, *,
                  trend_gate=None):
    """Rank = low EWMA vol (highest rank = calmest). Eligibility: positive
    trailing-252d return; optional trend_gate(date)->set of uptrending names."""
    def score_fn(signal_date, **_):
        if signal_date not in ewma_vol.index:
            return pd.Series(dtype=float)
        vol_row = ewma_vol.loc[signal_date].dropna()
        ret_row = returns_252.loc[signal_date] if signal_date in returns_252.index else None
        if ret_row is not None:
            vol_row = vol_row[ret_row.reindex(vol_row.index) > 0]  # positive 252d return
        if trend_gate is not None:
            keep = trend_gate(signal_date)
            vol_row = vol_row[vol_row.index.isin(keep)]
        if vol_row.empty:
            return vol_row
        # low vol -> high score
        return (-vol_row).rank(method="average") / len(vol_row)
    return score_fn


def perf(pv: pd.Series) -> dict:
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"cagr_pct": round(cagr * 100, 2), "vol_pct": round(vol * 100, 2),
            "max_dd_pct": round(dd * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "calmar": round(cagr / abs(dd), 3) if dd < 0 else None}


def pv_from(res, s, e) -> pd.Series:
    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    return pv.loc[(pv.index >= pd.Timestamp(s)) & (pv.index <= pd.Timestamp(e))]


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"lv_revisit_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in nse500]
    # Full-history NIFTY 100 index as the conservative buy-and-hold reference
    # (the data/benchmarks series doesn't cover the deep windows).
    nifty100_bh = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()

    returns = close_panel[cols].pct_change()
    ewma_vol = ewma_vol_panel(returns)
    ret_252 = close_panel[cols] / close_panel[cols].shift(252) - 1.0
    mom_126 = close_panel[cols] / close_panel[cols].shift(126) - 1.0
    sma200_c = sma_200[cols]

    def trend_gate(d):
        if d not in close_panel.index:
            return set()
        up = (close_panel[cols].loc[d] > sma200_c.loc[d]) & (mom_126.loc[d] > 0)
        return set(up[up].index)

    # scores
    l6_panels = build_momentum_panels(close_panel[cols],
                                      lookback_days=lookback_months_to_days(L6["lookback_months"]),
                                      skip_days=L6["skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=L6["vol_floor"], vol_power=L6["vol_power"],
                                   cross_sectional_zscore=L6["cross_sectional_zscore"])
    lv_naive = make_lv_score(ewma_vol, ret_252)
    lv_trend = make_lv_score(ewma_vol, ret_252, trend_gate=trend_gate)

    def run(score_fn, s, e, dd_stop=0.0):
        ed = thursdays(calendar)
        ed = ed[(ed >= pd.Timestamp(s)) & (ed <= pd.Timestamp(e))]
        if len(ed) == 0:
            return None
        return run_strategy(
            close_panel=close_panel[cols], trade_panel=trade_panel[cols], calendar=calendar,
            benchmark_aligned=benchmark, entry_signal_dates=ed, weekly_signal_dates=ed,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma_200[cols], atr_20_panel=atr_20[cols],
            top_n=TOP_N, exit_buffer=0, max_weight=0.075, slippage=0.002,
            atr_mult=0.0, atr_min_floor=dd_stop, use_trailing_stop=dd_stop > 0,
            use_dma_exit=False, weekly_rank_check=False,
            regime_panel=None, bear_exposure=0.0, bear_skips_entries=False,
            min_hold_days=8, initial_capital=1_000_000)

    variants = [("L6", l6_score, 0.0), ("LV_NAIVE", lv_naive, 0.0),
                ("LV_TREND", lv_trend, 0.0), ("LV_TREND_DD20", lv_trend, 0.20)]

    rows = []
    pv_cache = {}
    for wn, s, e in WINDOWS:
        # NIFTY100 buy-hold reference (full-history index)
        bpv = nifty100_bh.loc[(nifty100_bh.index >= pd.Timestamp(s)) & (nifty100_bh.index <= pd.Timestamp(e))].dropna()
        rows.append({"window": wn, "strategy": "NIFTY100_BH", **perf(bpv)})
        for label, sfn, dd in variants:
            res = run(sfn, s, e, dd_stop=dd)
            if res is None:
                continue
            pv = pv_from(res, s, e)
            pv_cache[(wn, label)] = pv
            rows.append({"window": wn, "strategy": label, **perf(pv)})

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False)

    # character vs L6: daily-return correlation + holdings overlap (FULL window)
    print("\n[character] correlation + overlap vs L6 (FULL)")
    char = []
    l6_pv = pv_cache.get(("FULL", "L6"))
    l6_ret = l6_pv.pct_change().dropna() if l6_pv is not None else None
    diag_dates = thursdays(calendar)
    diag_dates = diag_dates[(diag_dates >= pd.Timestamp("2010-01-01")) & (diag_dates <= pd.Timestamp("2026-07-20"))][::2]
    for label, sfn, dd in variants:
        if label == "L6":
            continue
        pv = pv_cache.get(("FULL", label))
        corr = None
        if pv is not None and l6_ret is not None:
            r = pv.pct_change().dropna()
            common = r.index.intersection(l6_ret.index)
            if len(common) > 30:
                corr = round(float(r.loc[common].corr(l6_ret.loc[common])), 3)
        ov = holdings_overlap(l6_score, sfn, diag_dates)
        char.append({"strategy": label, "daily_corr_to_L6": corr, "holdings_overlap_pct_L6": ov})
    char_df = pd.DataFrame(char)
    char_df.to_csv(out_dir / "character.csv", index=False)

    (out_dir / "report.json").write_text(json.dumps(
        {"summary": rows, "character": char}, indent=2, default=str))

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n" + "=" * 78)
    print("LOW-VOL REVISITED — conservative-sleeve lens")
    print("=" * 78)
    for wn, _, _ in WINDOWS:
        sub = summary[summary["window"] == wn]
        print(f"\n[{wn}]")
        print(sub[["strategy", "cagr_pct", "vol_pct", "max_dd_pct", "sharpe", "calmar"]].to_string(index=False))
    print("\nCharacter vs L6 (FULL window):")
    print(char_df.to_string(index=False))
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
