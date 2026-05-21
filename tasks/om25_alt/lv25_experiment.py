"""LV25 — Low-Volatility 25.

Score = percentile-rank of negative 252-day realized volatility (lower vol =
higher rank). Top 25 stocks from NSE 500. Production-shaped engine config.

Differentiation hypothesis: the low-volatility factor is documented globally
as the most orthogonal-to-momentum factor in equities. We expect LV25 to
underperform momentum on CAGR (textbook tradeoff) but offer:
    - Much lower daily-return correlation with L6 / OM25
    - Lower holdings overlap
    - Different drawdown profile (low-vol typically holds up better in
      market crashes but lags in mega-rallies)

Eligibility (mirrors OM25 v3 for fair comparison):
    - >= 220 valid daily returns in the 252-day window
    - Positive 252d total return (quality screen)

Engine config matches OM25 v3:
    top-25, exit-buffer 20, biweekly Friday signals, 100% exposure,
    20% from-peak drawdown stop on always, max 7.5% per position,
    20bps slippage.

Runs all four windows (IS + OOS A/B/C) for:
    - LV25 (this experiment)
    - L6 baseline (NSE 500 momentum)
    - OM25 production (Nifty 250 UC/CR)
    - OM25 score on NSE 500 (apples-to-apples universe comparison)

Diagnostics: per-window CAGR/Sharpe/MaxDD, daily-return correlations,
top-25 holdings overlap (Jaccard at every biweekly Friday).
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


WINDOWS = {
    "IS":    ("2009-09-01", "2016-12-31"),
    "OOS-A": ("2017-01-01", "2019-12-31"),
    "OOS-B": ("2020-01-01", "2022-12-31"),
    "OOS-C": ("2023-01-01", "2026-05-08"),
}

NSE500_UNIVERSE_CSV = "data/static/nse500_universe.csv"
NIFTY250_UNIVERSE_CSV = "data/static/nifty250_universe.csv"


def make_lv25_score(returns_universe: pd.DataFrame,
                     *,
                     lookback: int = 252,
                     min_obs: int = 220,
                     vol_floor_daily: float = 0.003,
                     return_filter: bool = True):
    """Score = percentile-rank of negative 252-day realized volatility.

    Higher score = lower volatility.

    Eligibility:
      - >= min_obs valid daily returns in window
      - Positive 252d total return when return_filter=True (quality screen)
      - Daily realized vol >= vol_floor_daily (filter dead/illiquid stocks
        with artificially low vol; default ~5% annualised)
    """
    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback:
            return pd.Series(dtype=float)

        window = returns_universe.iloc[idx - lookback + 1:idx + 1]
        results = {}
        for sym in window.columns:
            r = window[sym].dropna()
            if len(r) < min_obs:
                continue
            if return_filter and ((1 + r).prod() - 1) <= 0:
                continue
            vol = r.std()
            if vol < vol_floor_daily:
                continue
            results[sym] = -float(vol)

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
    return {
        "label": label, **config,
        "start": str(pv.index[0].date()) if len(pv) > 0 else None,
        "end": str(pv.index[-1].date()) if len(pv) > 0 else None,
        "years": round((pv.index[-1] - pv.index[0]).days / 365.25, 2) if len(pv) > 1 else 0,
        **m,
        "n_buys": int((result["trades"]["side"] == "BUY").sum()) if not result["trades"].empty else 0,
        "n_sells": int((result["trades"]["side"] == "SELL").sum()) if not result["trades"].empty else 0,
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
    ap.add_argument("--output-dir", type=Path, default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or ROOT / "tasks/om25_alt/runs" / f"lv25_{ts}"
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

    nse500_returns = close_panel[nse500_cols].pct_change()
    nifty250_returns = close_panel[nifty250_cols].pct_change()

    index_regime = build_regime_panel_confirmed(
        args.regime_index, OM25_LOCKED["regime_ma_window"],
        OM25_LOCKED["regime_confirm_days"], calendar=calendar,
    )

    # === Score functions ===
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
        ("LV25_NSE500",     lv25_score,         "biweekly", 0,                            20),
        ("L6_NSE500",       l6_score,           "weekly_thu", L6_BASELINE["min_hold_days"], 0),
        ("OM25_Nifty250",   om25_score_nifty250, "biweekly", 0,                            20),
        ("OM25_NSE500",     om25_score_nse500,  "biweekly", 0,                            20),
    ]
    stop_cfg = {"LV25_NSE500": (0.20, True),
                "L6_NSE500":   (0.0,  False),
                "OM25_Nifty250": (0.20, True),
                "OM25_NSE500":   (0.20, True)}

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
    panels = {
        "LV25":         extract_top25_panel(lv25_score,           diag_entries),
        "L6":           extract_top25_panel(l6_score,             diag_entries),
        "OM25_N250":    extract_top25_panel(om25_score_nifty250,  diag_entries),
        "OM25_NSE500":  extract_top25_panel(om25_score_nse500,    diag_entries),
    }
    print(f"  {len(diag_entries)} diagnostic rebalance dates")

    overlap_rows = []
    pairs = [("LV25", "L6"), ("LV25", "OM25_N250"), ("LV25", "OM25_NSE500"),
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
    print(corr_df.to_string(index=False))

    show = ["window", "variant", "cagr_pct", "sharpe", "max_dd_pct", "calmar"]
    print("\n=== Results ===")
    print(summary[show].to_string(index=False))

    (out_dir / "config.json").write_text(json.dumps({
        "score": "percentile-rank of -realized_vol over 252-day lookback",
        "lookback": 252,
        "min_obs": 220,
        "return_filter": True,
        "vol_floor_daily": 0.003,
        "universe": "NSE 500",
        "windows": WINDOWS,
    }, indent=2, default=str))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
