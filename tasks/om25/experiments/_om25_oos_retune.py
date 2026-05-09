"""OM25 IS=2009-2016 / OOS=2017-2026 retune.

Per tasks/oos_retune_2026/PLAN.md. Constrained re-tune of the OM25 strategy:
keep the Omega ratio composite ranking, search hyperparameter space within
bounds. Selection criterion: IS Sharpe (NOT IS CAGR).

Stage 1: score variants (~20 configs) at fixed defaults
Stage 2: execution sensitivity (~45 configs) around top-3 stage-1 winners
Final: re-run overall winner on full panel; evaluate multi-window OOS
"""
from __future__ import annotations

import math
import sys
import time
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy,
    fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import (
    DEFAULT_WINDOWS, evaluate_all_windows, passes_criteria, period_metrics,
)


PRICES_DIR = ROOT / "nse500_data_merged"
UNIVERSE = ROOT / "data/static/nse500_universe.csv"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
IS_END = pd.Timestamp("2016-12-31")


# ---------------------------------------------------------------------------
# Score factory: closure-based, parameterized
# ---------------------------------------------------------------------------

def make_om25_score(returns_universe, *, w_uc=0.5, w_cr=0.5,
                    return_filter=False, lookback=252, min_obs=220):
    """Return a `signal_function(signal_date)` compatible with run_strategy.

    Computes Omega-style upside_capture and capture_ratio over the lookback,
    pct-ranks each, then blends with w_uc and w_cr (normalized).
    Optional positive-return filter pre-screens stocks with negative total
    return over the lookback.
    """
    if w_uc <= 0 and w_cr <= 0:
        raise ValueError("at least one of w_uc, w_cr must be > 0")
    w_sum = w_uc + w_cr
    w_uc_n = w_uc / w_sum
    w_cr_n = w_cr / w_sum

    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback:
            return pd.Series(dtype=float)
        window = returns_universe.iloc[idx - lookback + 1:idx + 1]
        market_ret = window.mean(axis=1)
        results = {}
        for sym in window.columns:
            r = window[sym].dropna()
            if len(r) < min_obs:
                continue
            if return_filter and ((1 + r).prod() - 1) <= 0:
                continue
            common = r.index.intersection(market_ret.index)
            sr = r.loc[common]
            mr = market_ret.loc[common]
            up = mr > 0
            dn = mr < 0
            if up.sum() < 50 or dn.sum() < 50:
                continue
            uc = sr[up].mean() / mr[up].mean() if mr[up].mean() > 0 else 0
            dc = sr[dn].mean() / mr[dn].mean() if mr[dn].mean() < 0 else 1
            ratio = uc / dc if dc > 0 else uc
            results[sym] = {"up": uc, "ratio": ratio}
        if not results:
            return pd.Series(dtype=float)
        df = pd.DataFrame(results).T
        up_pct = df["up"].rank(method="average") / len(df)
        cr_pct = df["ratio"].rank(method="average") / len(df)
        return w_uc_n * up_pct + w_cr_n * cr_pct

    return score_fn


# ---------------------------------------------------------------------------
# Single-config runner
# ---------------------------------------------------------------------------

def run_config(*, returns_uni, close_panel, trade_panel, calendar,
               benchmark_aligned, sma_200, atr_20,
               weekly_filt, monthly_first, biweekly_fri,
               cfg: dict, is_only: bool = True) -> dict:
    """Run a single OM25 config; return IS-period metrics dict."""
    # Build entry dates per cadence
    if cfg["cadence"] == "monthly":
        entry_all = monthly_first
    elif cfg["cadence"] == "biweekly":
        entry_all = biweekly_fri
    else:
        raise ValueError(cfg["cadence"])

    # Need lookback warmup
    min_date = close_panel.index[cfg["lookback"]]
    entry_filt = entry_all[entry_all >= min_date]
    if is_only:
        entry_filt = entry_filt[entry_filt <= IS_END]

    score_fn = make_om25_score(
        returns_uni,
        w_uc=cfg["w_uc"], w_cr=cfg["w_cr"],
        return_filter=cfg["return_filter"],
        lookback=cfg["lookback"], min_obs=cfg["min_obs"],
    )

    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_filt, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        atr_mult=cfg["atr_mult"], atr_min_floor=cfg["atr_min_floor"],
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=cfg["atr_mult"] > 0,
    )
    if res is None:
        return {**cfg, "status": "no_signals"}

    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])

    # Slice to IS for tuning metrics
    is_metrics = period_metrics(eq, "IS_tune", "2009-09-01", IS_END)
    out = {**cfg, "status": "ok"}
    for k in ("cagr_pct", "sharpe", "vol_pct", "max_dd_pct", "yrs", "rows"):
        out[f"is_{k}"] = is_metrics.get(k)
    out["_equity"] = eq  # keep for later if needed
    return out


# ---------------------------------------------------------------------------
# Stage 1 grid: score variants
# ---------------------------------------------------------------------------

STAGE1_BASELINE = dict(
    lookback=252, min_obs=220,
    top_n=25, exit_buffer=15,
    cadence="monthly",
    atr_mult=0.0, atr_min_floor=0.0,
)

STAGE1_GRID = []
# 5 weight combos × 2 return-filter × 2 min-obs = 20 configs
for (w_uc, w_cr) in [(1.0, 0.0), (0.7, 0.3), (0.5, 0.5), (0.3, 0.7), (0.0, 1.0)]:
    for return_filter in (False, True):
        for min_obs in (220, 150):
            cfg = STAGE1_BASELINE | dict(
                w_uc=w_uc, w_cr=w_cr,
                return_filter=return_filter,
                min_obs=min_obs,
            )
            STAGE1_GRID.append(cfg)


# ---------------------------------------------------------------------------
# Stage 2 grid factory: per-winner sub-grids
# ---------------------------------------------------------------------------

def stage2_grid_for_winner(winner: dict) -> list:
    """Generate ~15 stage-2 configs around a stage-1 winner.

    Vary at most 2 dims at a time around the winner baseline.
    """
    base = {k: winner[k] for k in (
        "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
        "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
    )}
    grid = []
    seen = set()

    def add(cfg):
        # Hashable key on sorted items
        key = tuple(sorted((k, v) for k, v in cfg.items()
                            if k != "atr_min_floor" or cfg["atr_mult"] > 0))
        if key in seen:
            return
        seen.add(key)
        grid.append(cfg)

    # Vary lookback (4 values) at base
    for lb in (126, 189, 252, 378):
        scaled_min_obs = int(lb * 220 / 252)
        add(base | dict(lookback=lb, min_obs=scaled_min_obs))
    # Vary top_n × exit_buffer (3 × 3 = 9, dropping 5 to keep cap)
    for tn, bf in [(20, 10), (20, 15), (25, 10), (25, 20), (30, 15), (30, 20)]:
        add(base | dict(top_n=tn, exit_buffer=bf))
    # Vary cadence
    for cad in ("monthly", "biweekly"):
        add(base | dict(cadence=cad))
    # Vary ATR stop
    for atr in (0.0, 4.0, 5.0):
        add(base | dict(atr_mult=atr, atr_min_floor=0.0))
    return grid


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    out_dir = ROOT / f"experiments/oos_retune/{ts}_om25"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")

    print(f"\n[load] prices from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    print(f"[compute] SMA-200 + ATR-20 panels")
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    universe = load_universe(UNIVERSE)
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    returns_uni = close_uni.pct_change()
    print(f"[univ] {len(cols)} symbols, "
          f"{close_panel.index[0].date()} -> {close_panel.index[-1].date()}")

    weekly_fri = fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt_full = weekly_fri[weekly_fri >= close_panel.index[252]]

    # ---- Stage 1 ----
    print(f"\n{'=' * 80}\nStage 1: {len(STAGE1_GRID)} score variants\n{'=' * 80}")
    rows1 = []
    t0 = time.time()
    for i, cfg in enumerate(STAGE1_GRID, 1):
        out = run_config(
            returns_uni=returns_uni, close_panel=close_panel,
            trade_panel=trade_panel, calendar=calendar,
            benchmark_aligned=benchmark_aligned,
            sma_200=sma_200, atr_20=atr_20,
            weekly_filt=weekly_filt_full,
            monthly_first=monthly_first, biweekly_fri=biweekly_fri,
            cfg=cfg, is_only=True,
        )
        out.pop("_equity", None)
        rows1.append(out)
        elapsed = time.time() - t0
        print(f"  [{i:2d}/{len(STAGE1_GRID)}] "
              f"w_uc={cfg['w_uc']} w_cr={cfg['w_cr']} "
              f"filt={cfg['return_filter']} minobs={cfg['min_obs']}  "
              f"IS Sharpe={out.get('is_sharpe', 'NA')}  "
              f"CAGR={out.get('is_cagr_pct', 'NA')}%  "
              f"DD={out.get('is_max_dd_pct', 'NA')}%  ({elapsed:.0f}s)")

    df1 = pd.DataFrame(rows1).sort_values("is_sharpe", ascending=False)
    df1.to_csv(out_dir / "stage1.csv", index=False)
    print(f"\n[stage1] top 5 by IS Sharpe:")
    print(df1.head(5)[["w_uc", "w_cr", "return_filter", "min_obs",
                       "is_sharpe", "is_cagr_pct", "is_max_dd_pct"]]
          .to_string(index=False))

    # Pick top 3
    top3 = df1.head(3).to_dict("records")

    # ---- Stage 2 ----
    print(f"\n{'=' * 80}\nStage 2: sub-grids around top-3 stage-1 winners\n{'=' * 80}")
    rows2 = []
    s2_configs = []
    seen_keys = set()
    for w in top3:
        sub = stage2_grid_for_winner(w)
        for c in sub:
            key = tuple(sorted(c.items()))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            s2_configs.append(c)
    print(f"  total stage-2 configs (deduped): {len(s2_configs)}")

    t0 = time.time()
    for i, cfg in enumerate(s2_configs, 1):
        out = run_config(
            returns_uni=returns_uni, close_panel=close_panel,
            trade_panel=trade_panel, calendar=calendar,
            benchmark_aligned=benchmark_aligned,
            sma_200=sma_200, atr_20=atr_20,
            weekly_filt=weekly_filt_full,
            monthly_first=monthly_first, biweekly_fri=biweekly_fri,
            cfg=cfg, is_only=True,
        )
        out.pop("_equity", None)
        rows2.append(out)
        elapsed = time.time() - t0
        if i % 5 == 0 or i == len(s2_configs):
            print(f"  [{i:2d}/{len(s2_configs)}] "
                  f"IS Sharpe={out.get('is_sharpe', 'NA')}  "
                  f"CAGR={out.get('is_cagr_pct', 'NA')}%  ({elapsed:.0f}s)")

    df2 = pd.DataFrame(rows2).sort_values("is_sharpe", ascending=False)
    df2.to_csv(out_dir / "stage2.csv", index=False)

    # Combine all stage results
    df_all = pd.concat([df1, df2], ignore_index=True).sort_values(
        "is_sharpe", ascending=False
    )
    df_all.to_csv(out_dir / "all_configs.csv", index=False)

    print(f"\n[stage2] top 5 across stage1+stage2 by IS Sharpe:")
    print(df_all.head(5)[["lookback", "w_uc", "w_cr", "return_filter",
                          "top_n", "exit_buffer", "cadence", "atr_mult",
                          "is_sharpe", "is_cagr_pct", "is_max_dd_pct"]]
          .to_string(index=False))

    # ---- Pick winner (highest IS Sharpe) and re-run on full panel ----
    winner = df_all.iloc[0].to_dict()
    print(f"\n{'=' * 80}\nWinner: {winner}\n{'=' * 80}")

    # Re-run on FULL signal dates (through 2026)
    full = run_config(
        returns_uni=returns_uni, close_panel=close_panel,
        trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned,
        sma_200=sma_200, atr_20=atr_20,
        weekly_filt=weekly_filt_full,
        monthly_first=monthly_first, biweekly_fri=biweekly_fri,
        cfg={k: winner[k] for k in (
            "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
            "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
        )},
        is_only=False,
    )
    eq = full["_equity"]
    eq.to_csv(out_dir / "winner_equity.csv", index=False)

    # Multi-window evaluation
    win_eval = evaluate_all_windows(eq)
    win_eval.to_csv(out_dir / "winner_windows.csv", index=False)
    print("\n=== Winner per-window metrics ===")
    print(win_eval.to_string(index=False))

    ok, reasons = passes_criteria(win_eval)
    print("\n=== Pass criteria ===")
    for r in reasons:
        print(f"  {r}")
    print(f"\nOverall: {'PASS' if ok else 'FAIL'}")

    # Compose summary
    summary = {
        "strategy": "OM25",
        "is_window": f"2009-09-01 to {IS_END.date()}",
        "winner_config": {k: winner[k] for k in (
            "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
            "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
        )},
        "passes": ok,
    }
    for _, r in win_eval.iterrows():
        summary[f"{r['window']}_cagr_pct"] = r.get("cagr_pct")
        summary[f"{r['window']}_sharpe"] = r.get("sharpe")
        summary[f"{r['window']}_max_dd_pct"] = r.get("max_dd_pct")

    pd.DataFrame([summary]).to_csv(out_dir / "winner_summary.csv", index=False)
    print(f"\n[wrote] {out_dir}")
    return out_dir


if __name__ == "__main__":
    main()
