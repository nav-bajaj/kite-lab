"""H1 — 52-week-high nearness (George-Hwang) as a ranking signal on NSE 500.

Variants (execution production-shaped: top-25, biweekly Friday, exit-buffer
20, 20%-from-peak stop, 7.5% cap, 20bps — the om25_alt harness config):
  GH25          score = close / 252d high (inclusive window, GH definition)
  GH_L6_BLEND   0.5 * pct_rank(GH nearness) + 0.5 * pct_rank(L6 score)
Comparators:
  L6_NSE500     production L6 config (weekly Thu, no stop)
  OM25_N250     production-shaped OM25 tilt score

Diagnostics: top-25 overlap + daily-return corr vs L6 (differentiation bars:
corr < 0.7 AND overlap < 25%), and momentum-crash drawdown windows
(2020-02..2020-06, 2025-01..2025-06) per variant.

Run:
    python tasks/donchian_channel/h1_nearness_experiment.py
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
from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, nearness_to_high,
)

WINDOWS = {
    "IS":    ("2009-09-01", "2016-12-31"),
    "OOS-A": ("2017-01-01", "2019-12-31"),
    "OOS-B": ("2020-01-01", "2022-12-31"),
    "OOS-C": ("2023-01-01", "2026-05-08"),
}

CRASH_WINDOWS = {
    "covid_2020": ("2020-02-01", "2020-06-30"),
    "corr_2025": ("2025-01-01", "2025-06-30"),
}


def make_gh_score(nearness: pd.DataFrame, cols: list[str]):
    sub = nearness[[c for c in cols if c in nearness.columns]]

    def score_fn(signal_date, **_):
        if signal_date not in sub.index:
            return pd.Series(dtype=float)
        s = sub.loc[signal_date].dropna()
        return s

    return score_fn


def make_blend_score(nearness: pd.DataFrame, l6_score_fn, cols: list[str],
                     w_gh: float = 0.5):
    sub = nearness[[c for c in cols if c in nearness.columns]]

    def score_fn(signal_date, **_):
        if signal_date not in sub.index:
            return pd.Series(dtype=float)
        gh = sub.loc[signal_date].dropna()
        l6 = l6_score_fn(signal_date)
        if gh.empty or l6 is None or l6.empty:
            return pd.Series(dtype=float)
        common = gh.index.intersection(l6.index)
        if len(common) < 25:
            return pd.Series(dtype=float)
        gh_r = gh.loc[common].rank(pct=True)
        l6_r = l6.loc[common].rank(pct=True)
        return w_gh * gh_r + (1 - w_gh) * l6_r

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


def extract_top25(score_fn, entry_dates, top_n=25) -> dict:
    out = {}
    for d in entry_dates:
        s = score_fn(d)
        if s is None or s.empty:
            continue
        out[d] = s.sort_values(ascending=False).head(top_n).index.tolist()
    return out


def overlap_stats(a: dict, b: dict) -> dict:
    common = sorted(set(a) & set(b))
    if not common:
        return {"n_dates": 0, "mean_overlap_pct": None}
    ov = [len(set(a[d]) & set(b[d])) / 25 for d in common]
    return {"n_dates": len(common),
            "mean_overlap_pct": round(float(np.mean(ov)) * 100, 2)}


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/donchian_channel/runs" / f"h1_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] engine + OHLC panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200_panel = close_panel.rolling(200, min_periods=200).mean()
    atr_20_panel = close_panel.pct_change().rolling(20).std()
    ohlc = load_ohlc_panels()
    nearness = nearness_to_high(ohlc["close"], ohlc["high"], 252,
                                inclusive=True).reindex(calendar)

    nse500 = load_universe(ROOT / "data/static/nse500_universe.csv")
    nifty250 = load_universe(ROOT / "data/static/nifty250_universe.csv")
    nse500_cols = [s for s in close_panel.columns if s in nse500]
    nifty250_cols = [s for s in close_panel.columns if s in nifty250]

    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(L6_BASELINE["lookback_months"]),
        skip_days=L6_BASELINE["skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=L6_BASELINE["vol_floor"],
        vol_power=L6_BASELINE["vol_power"],
        cross_sectional_zscore=L6_BASELINE["cross_sectional_zscore"],
    )
    index_regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        close_panel[nifty250_cols].pct_change(), index_regime,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )

    gh_score = make_gh_score(nearness, nse500_cols)
    blend_score = make_blend_score(nearness, l6_score, nse500_cols)

    # (label, score_fn, cadence, min_hold, exit_buffer, top_n, stop, use_stop)
    variants = [
        ("GH25",        gh_score,    "biweekly",   0, 20, 25, 0.20, True),
        ("GH_L6_BLEND", blend_score, "biweekly",   0, 20, 25, 0.20, True),
        ("L6_NSE500",   l6_score,    "weekly_thu", 8, 0,  24, 0.0,  False),
        ("OM25_N250",   om25_score,  "biweekly",   0, 20, 25, 0.20, True),
    ]

    rows = []
    for window_name, (start_s, end_s) in WINDOWS.items():
        w_start, w_end = pd.Timestamp(start_s), pd.Timestamp(end_s)
        for (label, score_fn, cadence, min_hold, exit_buf, top_n,
             stop, use_stop) in variants:
            if cadence == "biweekly":
                all_e = biweekly_fridays(calendar); weekly = fridays(calendar)
            else:
                all_e = thursdays(calendar); weekly = thursdays(calendar)
            entry_dates = all_e[(all_e >= w_start) & (all_e <= w_end)]
            weekly_dates = weekly[(weekly >= w_start) & (weekly <= w_end)]
            if len(entry_dates) == 0:
                continue
            full = f"{window_name}_{label}"
            print(f"  {full}")
            res = run_strategy(
                close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark,
                entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
                signal_function=score_fn, signal_function_args={},
                sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
                top_n=top_n, exit_buffer=exit_buf,
                max_weight=0.075, slippage=0.002,
                atr_mult=0.0, atr_min_floor=stop,
                use_trailing_stop=use_stop, use_dma_exit=False,
                weekly_rank_check=False,
                regime_panel=None, bear_exposure=0.0, bear_skips_entries=False,
                min_hold_days=min_hold, initial_capital=1_000_000,
            )
            if res is None:
                rows.append({"label": label, "window": window_name,
                             "error": "no_result"})
                continue
            eq = res["equity"].copy()
            eq["date"] = pd.to_datetime(eq["date"])
            pv = eq.set_index("date")["pv"].astype(float)
            pv = pv.loc[(pv.index >= entry_dates[0]) & (pv.index <= entry_dates[-1])]
            eq.to_csv(out_dir / f"{full}_equity.csv", index=False)
            row = {"label": label, "window": window_name, **metrics_from_pv(pv)}
            for cw_name, (cs, ce) in CRASH_WINDOWS.items():
                sub = pv.loc[pd.Timestamp(cs):pd.Timestamp(ce)]
                if len(sub) > 5:
                    row[f"dd_{cw_name}_pct"] = round(
                        float((sub / sub.cummax() - 1).min()) * 100, 2)
            rows.append(row)

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False)

    print("\n[diagnostics] holdings overlap + daily corr vs L6")
    all_fr = biweekly_fridays(calendar)
    diag = all_fr[(all_fr >= pd.Timestamp("2010-09-01"))
                  & (all_fr <= pd.Timestamp("2026-05-08"))]
    panels = {"GH25": extract_top25(gh_score, diag),
              "BLEND": extract_top25(blend_score, diag),
              "L6": extract_top25(l6_score, diag),
              "OM25": extract_top25(om25_score, diag)}
    ov_rows = []
    for a, b in [("GH25", "L6"), ("BLEND", "L6"), ("GH25", "OM25"),
                 ("GH25", "BLEND"), ("L6", "OM25")]:
        ov_rows.append({"pair": f"{a} vs {b}", **overlap_stats(panels[a], panels[b])})
    ov_df = pd.DataFrame(ov_rows)
    ov_df.to_csv(out_dir / "overlap.csv", index=False)
    print(ov_df.to_string(index=False))

    corr_rows = []
    for window_name in WINDOWS:
        eqs = {}
        for label, *_ in variants:
            f = out_dir / f"{window_name}_{label}_equity.csv"
            if f.exists():
                pv = pd.read_csv(f, parse_dates=["date"]).set_index("date")["pv"]
                eqs[label] = pv.astype(float).pct_change().dropna()
        for a in ("GH25", "GH_L6_BLEND"):
            if a in eqs and "L6_NSE500" in eqs:
                common = eqs[a].index.intersection(eqs["L6_NSE500"].index)
                if len(common) > 10:
                    rho = eqs[a].loc[common].corr(eqs["L6_NSE500"].loc[common])
                    corr_rows.append({"window": window_name,
                                      "pair": f"{a} vs L6",
                                      "daily_ret_corr": round(float(rho), 3)})
    corr_df = pd.DataFrame(corr_rows)
    corr_df.to_csv(out_dir / "daily_corr.csv", index=False)
    print(corr_df.to_string(index=False))

    show = [c for c in ("window", "label", "cagr_pct", "sharpe", "max_dd_pct",
                        "calmar", "dd_covid_2020_pct", "dd_corr_2025_pct")
            if c in summary.columns]
    print("\n=== H1 results ===")
    print(summary[show].to_string(index=False))
    (out_dir / "config.json").write_text(json.dumps({
        "gh": "close / 252d rolling max(high), inclusive (George-Hwang)",
        "blend": "0.5*pct_rank(GH) + 0.5*pct_rank(L6 z-score)",
        "execution": "top-25 biweekly Fri, exit-buffer 20, 20% stop, 7.5% cap, 20bps",
        "windows": WINDOWS,
    }, indent=2))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
