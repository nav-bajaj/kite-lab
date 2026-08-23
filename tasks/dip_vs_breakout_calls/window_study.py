"""Dip25_ts20 across the house IS/OOS windows, vs L6 v2 and OM25 v3,
plus regime-conditional call stats.

Windows follow tasks/donchian_channel/h2 (the portfolio-research
convention): IS 2009-09..2016-12, OOS-A 2017-2019, OOS-B 2020-2022,
OOS-C 2023-now. IS start is clipped to 2010-06-01 (panel coverage —
same reason the donchian H4 line used that start); OOS-C extends to
2026-08-19 (data end) rather than h2's 2026-05-08.

Regime = OM25's confirmed NIFTY-100 200DMA regime panel (bull/bear at
the call's signal date).

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/window_study.py
"""

from __future__ import annotations

import json
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
    load_ohlc_panels, load_universe_symbols,
)
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402
from tasks.dip_vs_breakout_calls.experiment import (  # noqa: E402
    CLIFF_SYMBOLS, simulate, slot_curve, curve_metrics,
)

OUT_DIR = Path(__file__).resolve().parent
WINDOWS = {
    "IS":    ("2010-06-01", "2016-12-31"),
    "OOS-A": ("2017-01-01", "2019-12-31"),
    "OOS-B": ("2020-01-01", "2022-12-31"),
    "OOS-C": ("2023-01-01", "2026-08-19"),
}


def main():
    # ---- dip panels (artifact-excluded universe) ----
    keep = [s for s in load_universe_symbols() if s not in CLIFF_SYMBOLS]
    panels = load_ohlc_panels(symbols=keep)
    close, trade = panels["close"], panels["trade"]
    rank = build_score_rank(close, 126)
    ret5 = close / close.shift(5) - 1.0
    dip = ((ret5 < -0.05) & (rank >= 0.75)).fillna(False)

    regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=close.index)

    # ---- engine panels for L6 / OM25 ----
    close_e, trade_e = load_price_panels(ROOT / "nse500_data_merged")
    cal_e = close_e.index
    bench = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(cal_e).ffill()
    sma200 = close_e.rolling(200, min_periods=200).mean()
    atr20 = close_e.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / "data/static/nse500_universe.csv")
    n250 = load_universe(ROOT / "data/static/nifty250_universe.csv")
    l6_panels = build_momentum_panels(
        close_e[[s for s in close_e.columns if s in nse500]],
        lookback_days=lookback_months_to_days(L6_BASELINE["lookback_months"]),
        skip_days=L6_BASELINE["skip_days"])
    l6_score = make_momentum_score(
        l6_panels, vol_floor=L6_BASELINE["vol_floor"],
        vol_power=L6_BASELINE["vol_power"],
        cross_sectional_zscore=L6_BASELINE["cross_sectional_zscore"])
    regime_e = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=cal_e)
    om25_score = make_om25_tilt_score(
        close_e[[s for s in close_e.columns if s in n250]].pct_change(), regime_e,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"])

    rows = []
    all_calls = []
    for wname, (s_, e_) in WINDOWS.items():
        ws, we = pd.Timestamp(s_), pd.Timestamp(e_)

        # dip
        calls, counts, _ = simulate(close, trade, dip, rank, cap=25,
                                    end=we, use_ts20=True, start=ws)
        pv = slot_curve(calls, close, 25, we, start=ws)
        closed = calls[calls.status == "closed"]
        yrs = (we - ws).days / 365.25
        rows.append(dict(window=wname, strategy="Dip feed",
                         **curve_metrics(pv),
                         n_calls=len(closed),
                         calls_per_year=round(len(closed) / yrs, 1),
                         win_pct=round((closed.pnl_pct > 0).mean() * 100, 1),
                         mean_pnl=round(closed.pnl_pct.mean() * 100, 2),
                         median_pnl=round(closed.pnl_pct.median() * 100, 2),
                         med_hold=int(closed.hold_td.median())))
        c = calls.copy()
        c["window"] = wname
        all_calls.append(c)

        # L6 / OM25
        for label, score_fn, cadence, min_hold, exit_buf, top_n, stop, use_stop in [
            ("L6 v2", l6_score, "weekly_thu", L6_BASELINE["min_hold_days"], 0, 24, 0.0, False),
            ("OM25 v3", om25_score, "biweekly", 0, 20, 25, 0.20, True),
        ]:
            if cadence == "biweekly":
                all_e_, weekly = biweekly_fridays(cal_e), fridays(cal_e)
            else:
                all_e_ = weekly = thursdays(cal_e)
            entry = all_e_[(all_e_ >= ws) & (all_e_ <= we)]
            wk = weekly[(weekly >= ws) & (weekly <= we)]
            res = run_strategy(
                close_panel=close_e, trade_panel=trade_e, calendar=cal_e,
                benchmark_aligned=bench, entry_signal_dates=entry,
                weekly_signal_dates=wk, signal_function=score_fn,
                signal_function_args={}, sma_200_panel=sma200,
                atr_20_panel=atr20, top_n=top_n, exit_buffer=exit_buf,
                max_weight=0.075, slippage=0.002, atr_mult=0.0,
                atr_min_floor=stop, use_trailing_stop=use_stop,
                use_dma_exit=False, weekly_rank_check=False,
                regime_panel=None, bear_exposure=0.0,
                bear_skips_entries=False, min_hold_days=min_hold,
                initial_capital=1_000_000)
            eq = res["equity"].copy()
            eq["date"] = pd.to_datetime(eq["date"])
            pv2 = eq.set_index("date")["pv"].astype(float)
            pv2 = pv2[(pv2.index >= ws) & (pv2.index <= we)]
            pv2 = pv2 / pv2.iloc[0]
            rows.append(dict(window=wname, strategy=label, **curve_metrics(pv2)))
        print(f"[done] {wname}")

    df = pd.DataFrame(rows)
    df.to_csv(OUT_DIR / "window_comparison.csv", index=False)
    print("\n=== windows ===")
    print(df.to_string(index=False))

    # ---- regime split of dip calls (all windows pooled) ----
    calls = pd.concat(all_calls, ignore_index=True)
    calls = calls[calls.status == "closed"]
    sig_dates = pd.to_datetime(calls.signal_date)
    calls["regime"] = regime.reindex(sig_dates).to_numpy()
    calls["regime"] = np.where(calls["regime"], "bull", "bear")
    print("\n=== dip calls by regime at entry (closed calls, all windows) ===")
    g = calls.groupby("regime").agg(
        n=("pnl_pct", "size"),
        win_pct=("pnl_pct", lambda x: round((x > 0).mean() * 100, 1)),
        mean_pnl=("pnl_pct", lambda x: round(x.mean() * 100, 2)),
        median_pnl=("pnl_pct", lambda x: round(x.median() * 100, 2)),
        p5=("pnl_pct", lambda x: round(x.quantile(.05) * 100, 1)),
        med_hold=("hold_td", "median"))
    print(g.to_string())
    calls.to_csv(OUT_DIR / "calls_all_windows.csv", index=False)


if __name__ == "__main__":
    main()
