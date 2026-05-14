"""How have the COMBO regime variants performed in the recent rally?

User's concern: high cash levels protect against DDs but if the market
bounces sharply while we're waiting for the regime to flip back to bull,
the strategy misses the recovery. April-May 2026 has been a strong rally
across all production strategies (L6, OM25 v3, TL25 v3) — how did the
cash-heavy variants do?

Tests across the last several months:
  - 1 month, 3 month, 6 month, 2026 YTD trailing returns
  - Regime state day-by-day for the recent period
  - When regime flipped (and whether each variant caught the bounce)

Configs compared:
  - L6 standalone (Aggressive production)
  - OM25 v3 (Conservative production)
  - TL25 v3 (production)
  - COMBO 50/50 no regime (just the diversification, no overlay)
  - COMBO + Binary 50% (current locked Defensive)
  - COMBO + Binary 50% + ALT 1
  - COMBO + Binary 30% + ALT 1 (proposed update)
  - COMBO + Binary 25% + ALT 1 (most aggressive cash)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, biweekly_fridays, fridays, thursdays,
)
from scripts._momentum_engine import (
    BASELINE as MM_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days, run_momentum,
)
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.tl25_v3 import (
    V3_LOCKED as TL25_LOCKED, build_tl25_panels, make_tl25_score,
)
from scripts.combo_defensive import LOCKED as COMBO_LOCKED, make_combo_score_fn
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe


# Reference end-date for "recent" analysis
END_DATE = "2026-05-12"


def trailing_returns(eq: pd.DataFrame, end_date: str) -> dict:
    pv = eq.set_index("date")["pv"].astype(float)
    pv.index = pd.to_datetime(pv.index)
    end_ts = pd.Timestamp(end_date)
    pv = pv[pv.index <= end_ts]
    if pv.empty:
        return {}
    end_val = pv.iloc[-1]
    out = {}
    for days, label in [(21, "1mo"), (63, "3mo"), (126, "6mo"), (252, "1yr")]:
        if len(pv) > days:
            start_val = pv.iloc[-days - 1]
            out[label] = round((end_val / start_val - 1) * 100, 2)
    # YTD 2026
    ytd_start = pd.Timestamp("2026-01-01")
    pv_ytd = pv[pv.index >= ytd_start]
    if not pv_ytd.empty:
        out["YTD_2026"] = round((pv_ytd.iloc[-1] / pv_ytd.iloc[0] - 1) * 100, 2)
    return out


def main():
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    # L6 panels + score
    nse500_uni = load_universe(ROOT / "data/static/nse500_universe.csv")
    nse500_cols = [s for s in close_panel.columns if s in nse500_uni]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(MM_BASELINE["lookback_months"]),
        skip_days=MM_BASELINE["skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=MM_BASELINE["vol_floor"],
        vol_power=MM_BASELINE["vol_power"], cross_sectional_zscore=True,
    )
    # OM25 v3
    nifty250_uni = load_universe(ROOT / "data/static/nifty250_universe.csv")
    nifty250_cols = [s for s in close_panel.columns if s in nifty250_uni]
    om25_returns = close_panel[nifty250_cols].pct_change()
    om25_regime_for_score = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime_for_score,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )
    # TL25 v3
    tl25_panels = build_tl25_panels(
        close_panel[nse500_cols],
        dma_short=TL25_LOCKED["dma_short"], dma_long=TL25_LOCKED["dma_long"],
        dma_persist_ref=TL25_LOCKED["dma_persist_ref"],
        persistence_window=TL25_LOCKED["persistence_window"],
        drawdown_window=TL25_LOCKED["drawdown_window"],
        drawdown_concavity=TL25_LOCKED["drawdown_concavity"],
        momentum_window=TL25_LOCKED["momentum_window"],
    )
    tl25_score = make_tl25_score(
        tl25_panels,
        w_persistence=TL25_LOCKED["w_persistence"],
        w_drawdown=TL25_LOCKED["w_drawdown"],
        w_momentum=TL25_LOCKED["w_momentum"],
    )

    # Regime panel
    binary_100 = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 100, 3, calendar=calendar,
    )

    # ===== Diagnostic: regime state day-by-day for last 6 months =====
    print(f"\n{'=' * 100}")
    print("REGIME PANEL STATE — last 6 months")
    print(f"{'=' * 100}")
    end_ts = pd.Timestamp(END_DATE)
    start_recent = end_ts - pd.Timedelta(days=180)
    regime_recent = binary_100[(binary_100.index >= start_recent) & (binary_100.index <= end_ts)]
    # bool → bull (True) or bear (False)
    print(f"State today (2026-05-12): "
          f"{'BULL (invested)' if binary_100.get(end_ts, True) else 'BEAR (de-risked)'}")
    # State counts
    bull_days = regime_recent.sum()
    bear_days = (~regime_recent).sum()
    print(f"Last 6 months: {bull_days} bull days, {bear_days} bear days "
          f"({100*bear_days/(bull_days+bear_days):.0f}% in bear)")

    # Flip dates (when regime changed)
    state_changes = regime_recent[regime_recent != regime_recent.shift(1)]
    print(f"\nRegime flips in last 6 months:")
    for d, v in state_changes.items():
        print(f"  {d.date()}: → {'BULL' if v else 'BEAR'}")

    # ===== Run all configs =====
    ctx = dict(close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                sma_200=sma_200, atr_20=atr_20)
    combo = make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=COMBO_LOCKED["n_per_strategy"],
    )

    def _run_combo(regime, bear_exp, skip_entries, signal_day="friday", cadence="biweekly"):
        if signal_day == "thursday":
            entry_all = thursdays(calendar)
        else:
            entry_all = biweekly_fridays(calendar) if cadence == "biweekly" else fridays(calendar)
        weekly_all = fridays(calendar) if signal_day == "friday" else thursdays(calendar)
        s = pd.Timestamp("2009-09-01"); e = end_ts
        entry_dates = entry_all[(entry_all >= s) & (entry_all <= e)]
        weekly_filt = weekly_all[(weekly_all >= s) & (weekly_all <= e)]
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=combo, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=24, exit_buffer=0,
            max_weight=0.075, slippage=0.002,
            atr_mult=0.0, atr_min_floor=0.0,
            use_trailing_stop=False, use_dma_exit=False,
            weekly_rank_check=False,
            regime_panel=regime, bear_exposure=bear_exp,
            bear_skips_entries=skip_entries,
            min_hold_days=8, initial_capital=1_000_000,
        )
        return res["equity"]

    def _run_l6():
        # L6 standalone Thursday weekly (production)
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=l6_panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start="2009-09-01", end=END_DATE, config={},
        )
        return res["equity"]

    def _run_single(score_fn, cadence="biweekly", signal_day="friday"):
        # OM25 v3 / TL25 v3 standalone
        if signal_day == "thursday":
            entry_all = thursdays(calendar) if cadence == "weekly" else biweekly_fridays(calendar)  # fallback
        else:
            entry_all = biweekly_fridays(calendar) if cadence == "biweekly" else fridays(calendar)
        weekly_all = fridays(calendar)
        s = pd.Timestamp("2009-09-01"); e = end_ts
        entry_dates = entry_all[(entry_all >= s) & (entry_all <= e)]
        weekly_filt = weekly_all[(weekly_all >= s) & (weekly_all <= e)]
        # OM25 has 20% DD stop in its production form; we mirror via atr_min_floor
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=25, exit_buffer=20,
            max_weight=0.075, slippage=0.002,
            atr_mult=0.0, atr_min_floor=0.20,
            use_trailing_stop=True, use_dma_exit=False,
            weekly_rank_check=False,
            regime_panel=None, bear_exposure=0.0,
            min_hold_days=0, initial_capital=1_000_000,
        )
        return res["equity"]

    print("\n[run] computing equity curves ...")
    runs = {}
    print("  L6 standalone ...")
    runs["L6 standalone (Aggressive prod)"] = _run_l6()
    print("  OM25 v3 standalone ...")
    runs["OM25 v3 (Conservative prod)"] = _run_single(om25_score, "biweekly", "friday")
    print("  TL25 v3 standalone ...")
    runs["TL25 v3 (prod)"] = _run_single(tl25_score, "biweekly", "friday")
    print("  COMBO no regime ...")
    runs["COMBO no regime"] = _run_combo(None, 0.0, True)
    print("  COMBO + Binary 50% (locked) ...")
    runs["COMBO + Binary 50% (locked, skip_entries=True)"] = _run_combo(binary_100, 0.5, True)
    print("  COMBO + Binary 50% + ALT 1 ...")
    runs["COMBO + Binary 50% + ALT 1"] = _run_combo(binary_100, 0.5, False)
    print("  COMBO + Binary 30% + ALT 1 (proposed) ...")
    runs["COMBO + Binary 30% + ALT 1 (proposed)"] = _run_combo(binary_100, 0.3, False)
    print("  COMBO + Binary 25% + ALT 1 ...")
    runs["COMBO + Binary 25% + ALT 1"] = _run_combo(binary_100, 0.25, False)

    print(f"\n{'=' * 110}")
    print("TRAILING RETURNS — through 2026-05-12")
    print(f"{'=' * 110}")
    rows = []
    for label, eq in runs.items():
        tr = trailing_returns(eq, END_DATE)
        rows.append({"strategy": label, **tr})
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))

    print(f"\n[wrote] tasks/MM-tuning/combo_recent_performance.csv")
    df.to_csv(ROOT / "tasks/MM-tuning/combo_recent_performance.csv", index=False)


if __name__ == "__main__":
    main()
