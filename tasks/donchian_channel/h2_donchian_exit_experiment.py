"""H2 — Donchian trailing-exit overlay on unchanged L6 / OM25 entries.

Grid (pre-registered in TASKS.md, no post-hoc N-shopping):
  L6_NSE500   exits: base (rank-only), +don10, +don20, +don55
  OM25_N250   exits: base (20% stop), don10/don20/don55 replacing the stop,
              don20 + stop together

Entries, scores, cadence, sizing identical to the om25_alt harness so
results compare directly against docs/portfolios.md baselines.

Verdict rule: pick N on IS only; accept only if OOS Calmar/MaxDD improves
with CAGR give-up <= 2pp, same direction in all three OOS windows.

Run:
    python tasks/donchian_channel/h2_donchian_exit_experiment.py
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
    load_ohlc_panels, donchian_lower,
)

WINDOWS = {
    "IS":    ("2009-09-01", "2016-12-31"),
    "OOS-A": ("2017-01-01", "2019-12-31"),
    "OOS-B": ("2020-01-01", "2022-12-31"),
    "OOS-C": ("2023-01-01", "2026-05-08"),
}

DON_NS = (10, 20, 55)


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


def collect(result, label, window, active_start, active_end) -> dict:
    if result is None:
        return {"label": label, "window": window, "error": "no_result"}
    eq = result["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= active_start) & (pv.index <= active_end)]
    m = metrics_from_pv(pv)
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9) if len(pv) > 1 else 1
    exits = result["exits"]
    reason_counts = exits["reason"].value_counts().to_dict() if not exits.empty else {}
    n_buys = int((result["trades"]["side"] == "BUY").sum()) if not result["trades"].empty else 0
    return {
        "label": label, "window": window, **m,
        "annual_turnover_buys": round(n_buys / years, 1),
        "exit_reasons": json.dumps(reason_counts),
    }


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/donchian_channel/runs" / f"h2_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] engine price panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200_panel = close_panel.rolling(200, min_periods=200).mean()
    atr_20_panel = close_panel.pct_change().rolling(20).std()

    print("[load] OHLC panels + Donchian low bands")
    ohlc = load_ohlc_panels()
    don_lows = {}
    for n in DON_NS:
        don_lows[n] = donchian_lower(ohlc["low"], n).reindex(calendar)

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
        l6_panels,
        vol_floor=L6_BASELINE["vol_floor"],
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

    # (variant_label, score_fn, cadence, min_hold, exit_buffer, top_n,
    #  stop_floor, use_stop, don_n)
    variants = []
    for tag, don_n in [("base", None)] + [(f"don{n}", n) for n in DON_NS]:
        variants.append((f"L6_{tag}", l6_score, "weekly_thu",
                         L6_BASELINE["min_hold_days"], 0, 24, 0.0, False, don_n))
    variants.append(("OM25_base", om25_score, "biweekly", 0, 20, 25, 0.20, True, None))
    for n in DON_NS:
        variants.append((f"OM25_don{n}_repl", om25_score, "biweekly",
                         0, 20, 25, 0.0, False, n))
    variants.append(("OM25_don20_plus_stop", om25_score, "biweekly",
                     0, 20, 25, 0.20, True, 20))

    rows = []
    for window_name, (start_s, end_s) in WINDOWS.items():
        w_start, w_end = pd.Timestamp(start_s), pd.Timestamp(end_s)
        for (label, score_fn, cadence, min_hold, exit_buf, top_n,
             stop_floor, use_stop, don_n) in variants:
            if cadence == "biweekly":
                all_e = biweekly_fridays(calendar)
                weekly = fridays(calendar)
            else:
                all_e = thursdays(calendar)
                weekly = thursdays(calendar)
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
                atr_mult=0.0, atr_min_floor=stop_floor,
                use_trailing_stop=use_stop, use_dma_exit=False,
                donchian_low_panel=don_lows[don_n] if don_n else None,
                weekly_rank_check=False,
                regime_panel=None, bear_exposure=0.0, bear_skips_entries=False,
                min_hold_days=min_hold, initial_capital=1_000_000,
            )
            if res is not None:
                res["equity"].to_csv(out_dir / f"{full}_equity.csv", index=False)
            rows.append(collect(res, label, window_name,
                                entry_dates[0], entry_dates[-1]))

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False)
    show = ["window", "label", "cagr_pct", "sharpe", "max_dd_pct", "calmar",
            "annual_turnover_buys"]
    print("\n=== H2 results ===")
    print(summary[show].to_string(index=False))
    print("\n=== Exit reasons ===")
    print(summary[["window", "label", "exit_reasons"]].to_string(index=False))
    (out_dir / "config.json").write_text(json.dumps({
        "grid": "L6 x {base,don10,don20,don55}; OM25 x {base,don repl x3,don20+stop}",
        "windows": WINDOWS, "don_ns": DON_NS,
        "note": "donchian panels are prior-window (shift 1); exits weekly cadence",
    }, indent=2, default=str))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
