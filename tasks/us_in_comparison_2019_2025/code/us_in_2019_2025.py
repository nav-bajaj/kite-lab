"""Core Momentum (L6 v2) + Quality Momentum (OM25 v3), India vs US,
metrics computed on the common window 2019-01-01 .. 2025-12-31.

India: run locked production configs on NSE500/Nifty250 panels from 2017
(same treatment as the us-data branch harness), then slice the window.
US: slice the saved equity curves from experiments/us_strategies_2017/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Users/navdeep/kite-lab")
sys.path.insert(0, str(ROOT))

from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts._clean_engine import (
    run_strategy, compute_metrics, fridays, biweekly_fridays, thursdays,
)
from scripts._momentum_engine import (
    BASELINE as L6_BASELINE, build_momentum_panels, make_momentum_score,
)
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)

WIN_START = pd.Timestamp("2019-01-01")
WIN_END = pd.Timestamp("2025-12-31")
RUN_START = pd.Timestamp("2017-01-01")


def lookback_months_to_days(months: int) -> int:
    return int(round(months * 21))


def slice_result(equity: pd.DataFrame, trades: pd.DataFrame,
                 exits: pd.DataFrame) -> dict:
    eq = equity.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq[(eq["date"] >= WIN_START) & (eq["date"] <= WIN_END)]
    eq = eq.sort_values("date").reset_index(drop=True)
    base = eq["pv"].iloc[0]
    eq["pv"] = eq["pv"] * (1_000_000 / base)
    tr = trades.copy()
    if not tr.empty and "date" in tr.columns:
        tr["date"] = pd.to_datetime(tr["date"])
        tr = tr[(tr["date"] >= WIN_START) & (tr["date"] <= WIN_END)]
    ex = exits.copy()
    if not ex.empty and "exit_date" in ex.columns:
        ex["exit_date"] = pd.to_datetime(ex["exit_date"])
        ex = ex[(ex["exit_date"] >= WIN_START) & (ex["exit_date"] <= WIN_END)]
    return {"equity": eq, "trades": tr, "exits": ex}


def benchmark_metrics(bm: pd.Series, label: str) -> dict:
    bm = bm.loc[WIN_START:WIN_END].dropna()
    ret = bm.pct_change().dropna()
    total = bm.iloc[-1] / bm.iloc[0] - 1
    years = (bm.index[-1] - bm.index[0]).days / 365.25
    cagr = (1 + total) ** (1 / years) - 1
    vol = ret.std() * np.sqrt(252)
    dd = (bm / bm.cummax() - 1).min()
    yearly = bm.resample("YE").last().pct_change().dropna()
    return {"label": label, "cagr": cagr, "max_dd": dd,
            "sharpe": cagr / vol if vol > 0 else 0,
            "sortino": np.nan, "calmar": cagr / abs(dd) if dd < 0 else 0,
            "vol": vol, "beta": 1.0, "corr": 1.0, "trades": 0,
            "hit_rate": np.nan, "final_pv": 1_000_000 * (1 + total),
            "yearly": yearly}


def run_india():
    prices_dir = ROOT / "nse500_data_merged"
    print(f"[india] loading panels from {prices_dir} ...")
    close_panel, trade_panel = load_price_panels(prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "indices_data_historical/NIFTY_100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    print(f"  calendar {calendar[0].date()}..{calendar[-1].date()}, "
          f"{close_panel.shape[1]} symbols")

    results = {}

    # --- L6 v2 (Core Momentum) on NSE 500 ---
    cfg = L6_BASELINE
    uni = load_universe(ROOT / cfg["universe_csv"])
    close_uni = close_panel[[s for s in close_panel.columns if s in uni]]
    print(f"[india] L6 v2: universe {close_uni.shape[1]} symbols")
    entry_all = thursdays(calendar)
    entries = entry_all[(entry_all >= RUN_START)]
    panels = build_momentum_panels(
        close_uni,
        lookback_days=lookback_months_to_days(cfg["lookback_months"]),
        skip_days=cfg["skip_days"],
    )
    score_fn = make_momentum_score(
        panels, vol_floor=cfg["vol_floor"], vol_power=cfg["vol_power"],
        cross_sectional_zscore=cfg["cross_sectional_zscore"],
    )
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entries, weekly_signal_dates=entries,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        max_weight=cfg["max_weight"], slippage=cfg["slippage"],
        atr_mult=0.0, atr_min_floor=cfg["drawdown_stop"],
        use_trailing_stop=cfg["drawdown_stop"] > 0.0,
        use_dma_exit=False, weekly_rank_check=False,
        regime_panel=None, bear_exposure=0.0,
        min_hold_days=cfg["min_hold_days"],
        initial_capital=1_000_000,
    )
    results["Core Momentum (L6 v2) — India"] = res
    print("  done")

    # --- OM25 v3 (Quality Momentum) on Nifty 250 ---
    cfg = OM25_LOCKED
    uni = load_universe(ROOT / cfg["universe_csv"])
    close_uni = close_panel[[s for s in close_panel.columns if s in uni]]
    print(f"[india] OM25 v3: universe {close_uni.shape[1]} symbols")
    regime_panel = build_regime_panel_confirmed(
        ROOT / cfg["regime_index_path"],
        ma_window=cfg["regime_ma_window"],
        confirm_days=cfg["regime_confirm_days"],
        calendar=calendar,
    )
    entry_all = biweekly_fridays(calendar)
    weekly_all = fridays(calendar)
    entries = entry_all[(entry_all >= RUN_START)]
    weeklies = weekly_all[(weekly_all >= RUN_START)]
    returns_uni = close_uni.pct_change()
    score_fn = make_om25_tilt_score(
        returns_uni, regime_panel,
        bull_w_uc=cfg["bull_w_uc"], bull_w_cr=cfg["bull_w_cr"],
        bear_w_uc=cfg["bear_w_uc"], bear_w_cr=cfg["bear_w_cr"],
        return_filter=cfg["return_filter"],
        lookback=cfg["lookback"], min_obs=cfg["min_obs"],
    )
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entries, weekly_signal_dates=weeklies,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        max_weight=cfg["max_weight"], slippage=cfg["slippage"],
        atr_mult=0.0, atr_min_floor=cfg["drawdown_stop_pct"],
        use_trailing_stop=cfg["drawdown_stop_pct"] > 0.0,
        use_dma_exit=False, weekly_rank_check=False,
        regime_panel=None, bear_exposure=0.0,
        initial_capital=1_000_000,
    )
    results["Quality Momentum (OM25 v3) — India"] = res
    print("  done")

    return results, benchmark


def load_us():
    base = ROOT / "experiments/us_strategies_2017"
    out = {}
    for label, sub in [("Core Momentum (L6 v2) — US", "l6_v2"),
                       ("Quality Momentum (OM25 v3) — US", "om25_v3")]:
        eq = pd.read_csv(base / sub / "equity.csv")
        tr = pd.read_csv(base / sub / "trades.csv")
        ex = pd.read_csv(base / sub / "exits.csv")
        out[label] = {"equity": eq, "trades": tr, "exits": ex}
    spy = pd.read_csv(base / "l6_v2" / "equity.csv", parse_dates=["date"])
    spy = spy.set_index("date")["benchmark"]
    return out, spy


def main():
    india_results, nifty100 = run_india()
    us_results, spy = load_us()

    def yearly_from_pv(pv: pd.Series) -> pd.Series:
        ye = pv.resample("YE").last()
        base = pd.Series([pv.iloc[0]],
                         index=[pv.index[0] - pd.Timedelta(days=1)])
        return pd.concat([base, ye]).pct_change().dropna()

    rows = []
    yearly = {}
    for label, res in {**india_results, **us_results}.items():
        sliced = slice_result(res["equity"], res["trades"], res["exits"])
        m = compute_metrics(sliced, label=label)
        m.pop("yearly")
        yearly[label] = yearly_from_pv(sliced["equity"].set_index("date")["pv"])
        rows.append(m)

    for bm_label, series in [("NIFTY 100 (India benchmark)", nifty100),
                             ("SPY (US benchmark)", spy)]:
        m = benchmark_metrics(series, bm_label)
        m.pop("yearly")
        yearly[bm_label] = yearly_from_pv(
            series.loc[WIN_START:WIN_END].dropna())
        rows.append(m)

    df = pd.DataFrame(rows)
    cols = ["label", "cagr", "max_dd", "sharpe", "sortino", "calmar",
            "vol", "beta", "hit_rate", "trades", "final_pv"]
    df = df[[c for c in cols if c in df.columns]]
    out_dir = Path(__file__).parent
    df.to_csv(out_dir / "summary_2019_2025.csv", index=False)

    ydf = pd.DataFrame({k: (v * 100).round(2) for k, v in yearly.items()})
    ydf.index = ydf.index.year
    ydf = ydf.loc[(ydf.index >= 2019) & (ydf.index <= 2025)]
    ydf.to_csv(out_dir / "yearly_2019_2025.csv")

    pd.set_option("display.width", 250)
    print("\n=== Metrics 2019-01-01 .. 2025-12-31 ===")
    with pd.option_context("display.float_format", "{:.4f}".format):
        print(df.to_string(index=False))
    print("\n=== Calendar-year returns (%) ===")
    print(ydf.to_string())


if __name__ == "__main__":
    main()
