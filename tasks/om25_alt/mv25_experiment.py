"""MV25 — Moderate-Vol Momentum 25.

A two-step picker:
    1. Pre-filter NSE 500: drop top 30% by 252-day realized vol
       (keeps the bottom ~70% — moderately-low to mid-vol names)
    2. Rank the survivors by 126-day raw return (no vol adjustment in score)
    3. Top 25, production-shaped execution

Hypothesis: filter out the wildest names before applying momentum. Should
recover most of momentum's CAGR while clipping the drawdown contribution
of high-beta small-caps that drive L6's bigger crashes. Also expected to
have lower turnover than L6 (low-vol names are stickier).

Engine config matches OM25 v3:
    top-25, exit-buffer 20, biweekly Friday signals, 100% exposure,
    20% from-peak stop on always, max 7.5% per position, 20bps slippage.

Comparisons: L6 (NSE 500 momentum), OM25 Nifty 250 (production),
OM25 NSE 500 (same-universe control), LV25 (pure low-vol).

Diagnostics: per-window CAGR/Sharpe/MaxDD/Calmar, daily-return
correlations, top-25 holdings overlap, annualised turnover.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (  # noqa: E402
    biweekly_fridays, fridays, thursdays, run_strategy,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.om25_v3 import (  # noqa: E402
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from tasks.om25_alt.lv25_experiment import make_lv25_score  # noqa: E402


WINDOWS = {
    "IS":    ("2009-09-01", "2016-12-31"),
    "OOS-A": ("2017-01-01", "2019-12-31"),
    "OOS-B": ("2020-01-01", "2022-12-31"),
    "OOS-C": ("2023-01-01", "2026-05-08"),
}

NSE500_UNIVERSE_CSV = "data/static/nse500_universe.csv"
NIFTY250_UNIVERSE_CSV = "data/static/nifty250_universe.csv"


def make_mv25_score(close_panel: pd.DataFrame,
                     returns_universe: pd.DataFrame,
                     *,
                     vol_lookback: int = 252,
                     mom_lookback: int = 126,
                     min_vol_obs: int = 220,
                     vol_cutoff_pct: float = 0.70,
                     vol_floor_daily: float = 0.003,
                     vol_measure: str = "total"):
    """Score = percentile-rank of 126d raw return, among bottom vol_cutoff_pct
    by 252d volatility (vol_measure='total' or 'downside').

    Downside vol = semi-deviation: sqrt(mean(min(r, 0)^2)). Rewards stocks
    whose vol comes from upside moves rather than downside crashes.

    Eligibility:
      - >= min_vol_obs valid daily returns in the 252d vol window
      - realized vol >= vol_floor_daily (filter near-dead stocks)
      - 252d window of valid close prices
      - 126d momentum is well-defined (close 126 days back exists)
    """
    close = close_panel[returns_universe.columns]

    def _vol_of(r: pd.Series) -> float:
        if vol_measure == "downside":
            dev = np.minimum(r.values, 0.0)
            return float(np.sqrt((dev ** 2).mean()))
        return float(r.std())

    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < vol_lookback:
            return pd.Series(dtype=float)
        if idx < mom_lookback:
            return pd.Series(dtype=float)

        # Step 1: 252-day volatility per stock (total or downside)
        window_vol = returns_universe.iloc[idx - vol_lookback + 1:idx + 1]
        vols = {}
        for sym in window_vol.columns:
            r = window_vol[sym].dropna()
            if len(r) < min_vol_obs:
                continue
            v = _vol_of(r)
            if v < vol_floor_daily:
                continue
            vols[sym] = v

        if len(vols) < 25:
            return pd.Series(dtype=float)

        # Step 2: keep bottom vol_cutoff_pct by vol
        vol_series = pd.Series(vols)
        threshold = vol_series.quantile(vol_cutoff_pct)
        eligible = vol_series[vol_series <= threshold].index.tolist()

        # Step 3: 126d raw momentum on eligible
        cur_close = close.iloc[idx]
        past_close = close.iloc[idx - mom_lookback]
        results = {}
        for sym in eligible:
            cc = cur_close.get(sym, np.nan)
            pc = past_close.get(sym, np.nan)
            if pd.isna(cc) or pd.isna(pc) or pc <= 0:
                continue
            results[sym] = float(cc / pc - 1.0)

        if not results:
            return pd.Series(dtype=float)
        scores = pd.Series(results)
        return scores.rank(method="average") / len(scores)

    return score_fn


def metrics_from_pv(pv: pd.Series) -> dict:
    if len(pv) < 2:
        return {}
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    dd = (pv / pv.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd < 0 else np.nan
    return {
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(sharpe, 3),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(dd * 100, 2),
        "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None,
    }


def collect_metrics(result, label, config, active_start, active_end) -> dict:
    if result is None:
        return {"label": label, **config, "error": "no_result"}
    eq = result["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= active_start) & (pv.index <= active_end)]
    m = metrics_from_pv(pv)
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9) if len(pv) > 1 else 1
    n_buys = int((result["trades"]["side"] == "BUY").sum()) if not result["trades"].empty else 0
    n_sells = int((result["trades"]["side"] == "SELL").sum()) if not result["trades"].empty else 0
    return {
        "label": label, **config,
        "start": str(pv.index[0].date()) if len(pv) > 0 else None,
        "end": str(pv.index[-1].date()) if len(pv) > 0 else None,
        "years": round(years, 2),
        **m,
        "n_buys": n_buys,
        "n_sells": n_sells,
        "annual_turnover_buys": round(n_buys / years, 1),
    }


def extract_top25_panel(score_fn, entry_dates, top_n=25) -> dict:
    out = {}
    for d in entry_dates:
        try:
            s = score_fn(d)
        except Exception:
            continue
        if s is None or s.empty:
            continue
        out[d] = s.sort_values(ascending=False).head(top_n).index.tolist()
    return out


def jaccard(a: list, b: list) -> float:
    sa, sb = set(a), set(b)
    union = sa | sb
    return len(sa & sb) / len(union) if union else float("nan")


def overlap_stats(panel_a: dict, panel_b: dict) -> dict:
    common_dates = sorted(set(panel_a) & set(panel_b))
    if not common_dates:
        return {"n_dates": 0, "mean_jaccard": None, "mean_overlap_pct": None}
    jacs = [jaccard(panel_a[d], panel_b[d]) for d in common_dates]
    overlaps = [len(set(panel_a[d]) & set(panel_b[d])) / 25 for d in common_dates]
    return {
        "n_dates": len(common_dates),
        "mean_jaccard": round(float(np.mean(jacs)), 3),
        "mean_overlap_pct": round(float(np.mean(overlaps)) * 100, 2),
    }


def run_one_window(*, label, score_fn, close_panel, trade_panel, calendar,
                   benchmark, entry_dates, weekly_dates,
                   sma_200_panel, atr_20_panel, args, config,
                   active_start, active_end, out_dir,
                   atr_min_floor=0.20, use_trailing_stop=True,
                   min_hold_days=0, exit_buffer=20, top_n=25):
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
        top_n=top_n, exit_buffer=exit_buffer,
        max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=atr_min_floor,
        use_trailing_stop=use_trailing_stop, use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
        bear_skips_entries=False, min_hold_days=min_hold_days,
        initial_capital=args.initial_capital,
    )
    if res is not None:
        res["equity"].to_csv(out_dir / f"{label}_equity.csv", index=False)
    return collect_metrics(res, label, config, active_start, active_end)


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path, default=ROOT / "indices_data_historical/NIFTY_100.csv")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--vol-cutoff-pct", type=float, default=0.70,
                    help="Keep stocks with vol below this percentile (default 0.70 = drop top 30%%)")
    ap.add_argument("--mom-lookback", type=int, default=126,
                    help="Momentum lookback in trading days (default 126 = 6 months)")
    ap.add_argument("--vol-measure", choices=["total", "downside"], default="total",
                    help="Vol filter measure: 'total' (std) or 'downside' (semi-deviation)")
    ap.add_argument("--output-dir", type=Path, default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    suffix = "mv25d" if args.vol_measure == "downside" else "mv25"
    out_dir = args.output_dir or ROOT / "tasks/om25_alt/runs" / f"{suffix}_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] price panels")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark).reindex(calendar).ffill()
    sma_200_panel = close_panel.rolling(200, min_periods=200).mean()
    atr_20_panel = close_panel.pct_change().rolling(20).std()

    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    nifty250 = load_universe(ROOT / NIFTY250_UNIVERSE_CSV)
    nse500_cols = [s for s in close_panel.columns if s in nse500]
    nifty250_cols = [s for s in close_panel.columns if s in nifty250]
    print(f"       NSE 500: {len(nse500_cols)} symbols  Nifty 250: {len(nifty250_cols)} symbols")
    print(f"       MV25 config: vol_cutoff_pct={args.vol_cutoff_pct}  mom_lookback={args.mom_lookback}")

    nse500_returns = close_panel[nse500_cols].pct_change()
    nifty250_returns = close_panel[nifty250_cols].pct_change()

    index_regime = build_regime_panel_confirmed(
        args.regime_index, OM25_LOCKED["regime_ma_window"],
        OM25_LOCKED["regime_confirm_days"], calendar=calendar,
    )

    # === Score functions ===
    mv25_score = make_mv25_score(
        close_panel, nse500_returns,
        vol_cutoff_pct=args.vol_cutoff_pct,
        mom_lookback=args.mom_lookback,
        vol_measure=args.vol_measure,
    )
    mv25_label = "MV25d_NSE500" if args.vol_measure == "downside" else "MV25_NSE500"

    lv25_score = make_lv25_score(nse500_returns)

    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(L6_BASELINE["lookback_months"]),
        skip_days=L6_BASELINE["skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels,
        vol_floor=L6_BASELINE["vol_floor"],
        vol_power=L6_BASELINE["vol_power"],
        cross_sectional_zscore=L6_BASELINE["cross_sectional_zscore"],
    )

    om25_score_nifty250 = make_om25_tilt_score(
        nifty250_returns, index_regime,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )

    om25_score_nse500 = make_om25_tilt_score(
        nse500_returns, index_regime,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )

    rows: list[dict] = []
    variants = [
        (mv25_label,        mv25_score,          "biweekly",  0,                              20),
        ("LV25_NSE500",     lv25_score,          "biweekly",  0,                              20),
        ("L6_NSE500",       l6_score,            "weekly_thu", L6_BASELINE["min_hold_days"],  0),
        ("OM25_Nifty250",   om25_score_nifty250, "biweekly",  0,                              20),
        ("OM25_NSE500",     om25_score_nse500,   "biweekly",  0,                              20),
    ]
    stop_cfg = {
        mv25_label:      (0.20, True),
        "LV25_NSE500":   (0.20, True),
        "L6_NSE500":     (0.0,  False),
        "OM25_Nifty250": (0.20, True),
        "OM25_NSE500":   (0.20, True),
    }

    for window_name, (start_s, end_s) in WINDOWS.items():
        w_start, w_end = pd.Timestamp(start_s), pd.Timestamp(end_s)
        for v_label, score_fn, cadence, min_hold, exit_buf in variants:
            if cadence == "biweekly":
                all_e = biweekly_fridays(calendar); weekly = fridays(calendar)
            else:
                all_e = thursdays(calendar); weekly = thursdays(calendar)
            entry_dates = all_e[(all_e >= w_start) & (all_e <= w_end)]
            weekly_dates = weekly[(weekly >= w_start) & (weekly <= w_end)]
            if len(entry_dates) == 0:
                continue
            stop, use_stop = stop_cfg[v_label]
            label = f"{window_name}_{v_label}"
            print(f"  {label}")
            rows.append(run_one_window(
                label=label, score_fn=score_fn,
                close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
                benchmark=benchmark,
                entry_dates=entry_dates, weekly_dates=weekly_dates,
                sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel, args=args,
                config={"window": window_name, "variant": v_label},
                active_start=entry_dates[0], active_end=entry_dates[-1],
                out_dir=out_dir,
                atr_min_floor=stop, use_trailing_stop=use_stop,
                min_hold_days=min_hold, exit_buffer=exit_buf,
            ))

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False)

    # === Diagnostics: holdings overlap ===
    print("\n[diagnostics] computing top-25 holdings panels")
    all_fridays = biweekly_fridays(calendar)
    diag_entries = all_fridays[(all_fridays >= pd.Timestamp("2010-09-01"))
                                & (all_fridays <= pd.Timestamp("2026-05-08"))]
    mv_diag_key = "MV25d" if args.vol_measure == "downside" else "MV25"
    panels = {
        mv_diag_key:    extract_top25_panel(mv25_score,           diag_entries),
        "LV25":         extract_top25_panel(lv25_score,           diag_entries),
        "L6":           extract_top25_panel(l6_score,             diag_entries),
        "OM25_N250":    extract_top25_panel(om25_score_nifty250,  diag_entries),
        "OM25_NSE500":  extract_top25_panel(om25_score_nse500,    diag_entries),
    }
    print(f"  {len(diag_entries)} diagnostic rebalance dates")

    overlap_rows = []
    pairs = [(mv_diag_key, "L6"), (mv_diag_key, "OM25_N250"), (mv_diag_key, "OM25_NSE500"),
             (mv_diag_key, "LV25"), ("LV25", "L6"),
             ("L6", "OM25_N250"), ("L6", "OM25_NSE500"),
             ("OM25_N250", "OM25_NSE500")]
    for a, b in pairs:
        st = overlap_stats(panels[a], panels[b])
        overlap_rows.append({"pair": f"{a} vs {b}", **st})
    overlap_df = pd.DataFrame(overlap_rows)
    overlap_df.to_csv(out_dir / "overlap.csv", index=False)
    print("\n=== Holdings overlap (top-25, every biweekly Friday) ===")
    print(overlap_df.to_string(index=False))

    # === Diagnostics: daily-return correlation from equity curves ===
    print("\n[diagnostics] daily-return correlations")
    corr_rows = []
    for window_name in WINDOWS:
        eq_by_var = {}
        for v_label, *_ in variants:
            f = out_dir / f"{window_name}_{v_label}_equity.csv"
            if not f.exists():
                continue
            pv = pd.read_csv(f, parse_dates=["date"]).set_index("date")["pv"].astype(float)
            eq_by_var[v_label] = pv.pct_change().dropna()
        labels = list(eq_by_var.keys())
        for i, a in enumerate(labels):
            for b in labels[i+1:]:
                common = eq_by_var[a].index.intersection(eq_by_var[b].index)
                if len(common) < 10:
                    continue
                rho = eq_by_var[a].loc[common].corr(eq_by_var[b].loc[common])
                corr_rows.append({"window": window_name, "pair": f"{a} vs {b}",
                                  "n_days": len(common), "daily_ret_corr": round(float(rho), 3)})
    corr_df = pd.DataFrame(corr_rows)
    corr_df.to_csv(out_dir / "daily_corr.csv", index=False)
    print("\n=== Daily-return correlation per window ===")
    # Show only MV25-relevant rows in console (full table in CSV)
    mv25_corr = corr_df[corr_df["pair"].str.contains(mv25_label.split("_")[0])]
    print(mv25_corr.to_string(index=False))

    show = ["window", "variant", "cagr_pct", "sharpe", "max_dd_pct", "calmar", "annual_turnover_buys"]
    print("\n=== Results ===")
    print(summary[show].to_string(index=False))

    (out_dir / "config.json").write_text(json.dumps({
        "score": "percentile-rank of 126d raw return, among bottom vol_cutoff_pct by 252d vol",
        "vol_lookback": 252,
        "mom_lookback": args.mom_lookback,
        "vol_cutoff_pct": args.vol_cutoff_pct,
        "min_vol_obs": 220,
        "vol_floor_daily": 0.003,
        "universe": "NSE 500",
        "windows": WINDOWS,
    }, indent=2, default=str))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
