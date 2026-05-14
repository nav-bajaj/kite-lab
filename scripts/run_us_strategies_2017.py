"""Run L6 v2, OM25 v3, TL25 v3, and COMBO Defensive against the US panel.

OOS-style validation port: same locked parameters as the Indian production
strategies, but swap NSE/Nifty inputs for US equivalents:
  - prices_dir = us_equities_data
  - universe   = data/static/us_equities_universe.csv (S&P 500 + Nasdaq 100)
  - benchmark  = data/benchmarks/spy.csv
  - regime     = SPY 100-DMA, 3-day confirm (replaces NIFTY 100)

Run from repo root with venv active:
    python scripts/run_us_strategies_2017.py
    python scripts/run_us_strategies_2017.py --start 2017-01-01 --end 2026-05-13
    python scripts/run_us_strategies_2017.py --output-dir experiments/us_strategies_2017
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._clean_engine import (  # noqa: E402
    run_strategy, compute_metrics,
    fridays, biweekly_fridays, thursdays,
)
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6_BASELINE,
    build_momentum_panels, make_momentum_score,
)
from scripts.om25_v3 import (  # noqa: E402
    LOCKED as OM25_LOCKED,
    build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.tl25_v3 import (  # noqa: E402
    V3_LOCKED as TL25_LOCKED,
    build_tl25_panels, make_tl25_score,
)
from scripts.combo_defensive import (  # noqa: E402
    LOCKED as COMBO_LOCKED,
    make_combo_score_fn,
)


PRICES_DIR = ROOT / "us_equities_data"
UNIVERSE_CSV = ROOT / "data/static/us_equities_universe.csv"
BENCHMARK_CSV = ROOT / "data/benchmarks/spy.csv"
REGIME_CSV = ROOT / "data/benchmarks/spy.csv"  # SPY is also the regime index


def lookback_months_to_days(months: int) -> int:
    return int(round(months * 21))


def _filter_entries(entry_all, weekly_all, start_ts, end_ts):
    entries = entry_all[(entry_all >= start_ts) & (entry_all <= end_ts)]
    weeklies = weekly_all[(weekly_all >= start_ts) & (weekly_all <= end_ts)]
    return entries, weeklies


def run_l6_v2(ctx, start_ts, end_ts):
    cfg = L6_BASELINE
    entry_all = thursdays(ctx["calendar"])
    weekly_all = thursdays(ctx["calendar"])
    entries, weeklies = _filter_entries(entry_all, weekly_all, start_ts, end_ts)

    panels = build_momentum_panels(
        ctx["close_uni"],
        lookback_days=lookback_months_to_days(cfg["lookback_months"]),
        skip_days=cfg["skip_days"],
    )
    score_fn = make_momentum_score(
        panels,
        vol_floor=cfg["vol_floor"], vol_power=cfg["vol_power"],
        cross_sectional_zscore=cfg["cross_sectional_zscore"],
    )
    return run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entries, weekly_signal_dates=weeklies,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        max_weight=cfg["max_weight"], slippage=cfg["slippage"],
        atr_mult=0.0, atr_min_floor=cfg["drawdown_stop"],
        use_trailing_stop=cfg["drawdown_stop"] > 0.0,
        use_dma_exit=False, weekly_rank_check=False,
        regime_panel=None, bear_exposure=0.0,
        min_hold_days=cfg["min_hold_days"],
        initial_capital=1_000_000,
    )


def run_om25_v3(ctx, start_ts, end_ts):
    cfg = OM25_LOCKED
    entry_all = biweekly_fridays(ctx["calendar"])
    weekly_all = fridays(ctx["calendar"])
    entries, weeklies = _filter_entries(entry_all, weekly_all, start_ts, end_ts)

    returns_uni = ctx["close_uni"].pct_change()
    score_fn = make_om25_tilt_score(
        returns_uni, ctx["regime_panel"],
        bull_w_uc=cfg["bull_w_uc"], bull_w_cr=cfg["bull_w_cr"],
        bear_w_uc=cfg["bear_w_uc"], bear_w_cr=cfg["bear_w_cr"],
        return_filter=cfg["return_filter"],
        lookback=cfg["lookback"], min_obs=cfg["min_obs"],
    )
    return run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entries, weekly_signal_dates=weeklies,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        max_weight=cfg["max_weight"], slippage=cfg["slippage"],
        atr_mult=0.0, atr_min_floor=cfg["drawdown_stop_pct"],
        use_trailing_stop=cfg["drawdown_stop_pct"] > 0.0,
        use_dma_exit=False, weekly_rank_check=False,
        regime_panel=None, bear_exposure=0.0,
        initial_capital=1_000_000,
    )


def run_tl25_v3(ctx, start_ts, end_ts):
    cfg = TL25_LOCKED
    entry_all = biweekly_fridays(ctx["calendar"])
    weekly_all = fridays(ctx["calendar"])
    entries, weeklies = _filter_entries(entry_all, weekly_all, start_ts, end_ts)

    panels = build_tl25_panels(
        ctx["close_uni"],
        dma_short=cfg["dma_short"], dma_long=cfg["dma_long"],
        dma_persist_ref=cfg["dma_persist_ref"],
        persistence_window=cfg["persistence_window"],
        drawdown_window=cfg["drawdown_window"],
        drawdown_concavity=cfg["drawdown_concavity"],
        momentum_window=cfg["momentum_window"],
    )
    score_fn = make_tl25_score(
        panels,
        w_persistence=cfg["w_persistence"],
        w_drawdown=cfg["w_drawdown"],
        w_momentum=cfg["w_momentum"],
    )
    return run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entries, weekly_signal_dates=weeklies,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        max_weight=cfg["max_weight"], slippage=cfg["slippage"],
        atr_mult=cfg["atr_mult"], atr_min_floor=cfg["atr_min_floor"],
        use_trailing_stop=cfg["use_trailing_stop"],
        use_dma_exit=cfg["use_dma_exit"],
        weekly_rank_check=cfg["weekly_rank_check"],
        regime_panel=None, bear_exposure=0.0,
        initial_capital=1_000_000,
    )


def run_combo_defensive(ctx, start_ts, end_ts):
    cfg = COMBO_LOCKED
    # Cadence: biweekly Friday signal → next-day exec (per LOCKED)
    entry_all = biweekly_fridays(ctx["calendar"])
    weekly_all = fridays(ctx["calendar"])
    entries, weeklies = _filter_entries(entry_all, weekly_all, start_ts, end_ts)

    # L6 component
    l6_panels = build_momentum_panels(
        ctx["close_uni"],
        lookback_days=lookback_months_to_days(cfg["l6_lookback_months"]),
        skip_days=cfg["l6_skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels,
        vol_floor=cfg["l6_vol_floor"], vol_power=cfg["l6_vol_power"],
        cross_sectional_zscore=True,
    )
    # OM25 component (same single US universe — Indian COMBO uses Nifty250 for OM25
    # vs NSE500 for L6, but for the US port we only have one universe CSV)
    returns_uni = ctx["close_uni"].pct_change()
    om25_score = make_om25_tilt_score(
        returns_uni, ctx["regime_panel"],
        bull_w_uc=cfg["om25_bull_w_uc"], bull_w_cr=cfg["om25_bull_w_cr"],
        bear_w_uc=cfg["om25_bear_w_uc"], bear_w_cr=cfg["om25_bear_w_cr"],
        return_filter=cfg["om25_return_filter"],
        lookback=cfg["om25_lookback"], min_obs=cfg["om25_min_obs"],
    )
    combo_score = make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=cfg["n_per_strategy"],
    )
    return run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entries, weekly_signal_dates=weeklies,
        signal_function=combo_score, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        max_weight=cfg["max_weight"], slippage=cfg["slippage"],
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
        weekly_rank_check=False,
        regime_panel=ctx["regime_panel"],
        bear_exposure=cfg["regime_bear_exposure"],
        bear_skips_entries=False,
        min_hold_days=cfg["min_hold_days"],
        initial_capital=1_000_000,
    )


def trim_to_window(result, start_ts):
    """Trim equity series to start at start_ts (engine begins at first entry)."""
    eq = result["equity"]
    if eq.empty:
        return result
    eq2 = eq[eq["date"] >= start_ts].reset_index(drop=True)
    if eq2.empty:
        return result
    # Rebase PV so the windowed CAGR computes off the trimmed start
    base = eq2["pv"].iloc[0]
    eq2 = eq2.copy()
    eq2["pv"] = eq2["pv"] * (1_000_000 / base)
    trades = result["trades"]
    if not trades.empty and "date" in trades.columns:
        trades = trades[pd.to_datetime(trades["date"]) >= start_ts]
    exits = result["exits"]
    if not exits.empty and "exit_date" in exits.columns:
        exits = exits[pd.to_datetime(exits["exit_date"]) >= start_ts]
    return {"equity": eq2, "trades": trades, "exits": exits}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--output-dir", type=Path,
                    default=ROOT / "experiments/us_strategies_2017")
    return ap.parse_args()


def main():
    args = parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    print(f"[load] US panels from {PRICES_DIR} ...")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK_CSV)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_universe(UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  calendar: {calendar[0].date()}..{calendar[-1].date()}   "
          f"universe: {len(cols)} symbols")

    print(f"[regime] SPY 100-DMA, 3-day confirm")
    regime_panel = build_regime_panel_confirmed(
        REGIME_CSV, ma_window=100, confirm_days=3, calendar=calendar,
    )
    bear_days = (~regime_panel.fillna(True).astype(bool)).sum()
    print(f"  bear days: {bear_days} / {len(regime_panel)} "
          f"({100*bear_days/len(regime_panel):.1f}%)")

    ctx = {
        "close_panel": close_panel, "trade_panel": trade_panel,
        "calendar": calendar, "benchmark_aligned": benchmark_aligned,
        "sma_200": sma_200, "atr_20": atr_20,
        "close_uni": close_uni, "regime_panel": regime_panel,
    }

    start_ts = pd.Timestamp(args.start)
    end_ts = pd.Timestamp(args.end) if args.end else calendar[-1]
    print(f"[window] {start_ts.date()}..{end_ts.date()}")

    strategies = [
        ("L6 v2",            run_l6_v2),
        ("OM25 v3",          run_om25_v3),
        ("TL25 v3",          run_tl25_v3),
        ("COMBO Defensive",  run_combo_defensive),
    ]

    rows = []
    yearly_frames = {}
    for label, fn in strategies:
        print(f"\n[run] {label} ...")
        res = fn(ctx, start_ts, end_ts)
        if res is None or res["equity"].empty:
            print(f"  [skipped — no result]")
            continue
        # Save full-window outputs
        sdir = out / label.replace(" ", "_").lower()
        sdir.mkdir(parents=True, exist_ok=True)
        res["equity"].to_csv(sdir / "equity.csv", index=False)
        res["trades"].to_csv(sdir / "trades.csv", index=False)
        res["exits"].to_csv(sdir / "exits.csv", index=False)

        # Metrics on trimmed window (2017+)
        trimmed = trim_to_window(res, start_ts)
        m = compute_metrics(trimmed, label=label)
        yearly_frames[label] = m.pop("yearly")
        rows.append(m)
        print(f"  CAGR {m['cagr']*100:6.2f}%  Sharpe {m['sharpe']:.2f}  "
              f"MaxDD {m['max_dd']*100:6.2f}%  Sortino {m['sortino']:.2f}  "
              f"Calmar {m['calmar']:.2f}  trades={m['trades']}")

    # Benchmark stat reference
    bm = benchmark_aligned.loc[start_ts:end_ts].dropna()
    if not bm.empty:
        bm_ret = bm.pct_change().dropna()
        bm_total = bm.iloc[-1] / bm.iloc[0] - 1
        bm_years = (bm.index[-1] - bm.index[0]).days / 365.25
        bm_cagr = (1 + bm_total) ** (1 / bm_years) - 1
        bm_vol = bm_ret.std() * np.sqrt(252)
        bm_peak = bm.cummax()
        bm_dd = (bm / bm_peak - 1).min()
        bm_sharpe = bm_cagr / bm_vol if bm_vol > 0 else 0
        rows.append({
            "label": "SPY (benchmark)",
            "cagr": bm_cagr, "max_dd": bm_dd, "sharpe": bm_sharpe,
            "sortino": np.nan, "calmar": bm_cagr / abs(bm_dd) if bm_dd < 0 else 0,
            "vol": bm_vol, "beta": 1.0, "corr": 1.0,
            "avg_cash": 0.0, "avg_holdings": 1.0,
            "trades": 0, "cost_drag": 0.0, "hit_rate": np.nan,
            "final_pv": 1_000_000 * (1 + bm_total),
            "longest_dd_days": np.nan,
        })

    # Build summary table
    df = pd.DataFrame(rows)
    cols_order = [
        "label", "cagr", "max_dd", "sharpe", "sortino", "calmar",
        "vol", "longest_dd_days", "beta", "corr",
        "avg_holdings", "avg_cash", "trades", "hit_rate", "cost_drag",
        "final_pv",
    ]
    df = df[[c for c in cols_order if c in df.columns]]
    df.to_csv(out / "summary.csv", index=False)

    print("\n" + "=" * 105)
    print(f"US strategies — {start_ts.date()} to {end_ts.date()}")
    print("=" * 105)
    fmt = (
        "{:<20} {:>7} {:>7} {:>7} {:>7} {:>7} {:>7} {:>7} {:>6} {:>7} {:>8}"
    )
    print(fmt.format("Strategy", "CAGR", "MaxDD", "Sharpe", "Sortino", "Calmar",
                     "Vol", "Beta", "Hold", "Hit", "Trades"))
    print("-" * 105)
    for _, r in df.iterrows():
        print(fmt.format(
            r["label"][:20],
            f"{r['cagr']*100:.2f}%",
            f"{r['max_dd']*100:.2f}%",
            f"{r['sharpe']:.2f}",
            f"{r['sortino']:.2f}" if pd.notna(r['sortino']) else "-",
            f"{r['calmar']:.2f}",
            f"{r['vol']*100:.2f}%",
            f"{r.get('beta', np.nan):.2f}" if pd.notna(r.get('beta', np.nan)) else "-",
            f"{r['avg_holdings']:.1f}" if pd.notna(r['avg_holdings']) else "-",
            f"{r['hit_rate']*100:.1f}%" if pd.notna(r.get('hit_rate', np.nan)) else "-",
            f"{int(r['trades'])}",
        ))
    print("=" * 105)
    print(f"\n[done] outputs → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
