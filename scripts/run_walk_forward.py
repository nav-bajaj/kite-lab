"""Walk-forward robustness orchestrator (OM25 v3 + TL25 v3).

Single-process load-once design — pre-load panels and per-strategy panels,
then loop per (strategy, universe, window) calling `_clean_engine.run_strategy`
directly. ~1s per backtest; the full Phase 1 sweep finishes in minutes
instead of hours.

See tasks/walk_forward/PLAN.md and ~/.claude/plans/sunny-seeking-hartmanis.md
for the design rationale.

Phase 0 smell test:
    python scripts/run_walk_forward.py \\
        --strategies tl25_v3 --universes nse500 \\
        --windows W01 W07 W13 \\
        --output tasks/walk_forward/results/smell_test

Phase 1 production-universe sweep:
    python scripts/run_walk_forward.py \\
        --strategies tl25_v3 om25_v3 --universes production \\
        --windows all --workers 8 \\
        --output tasks/walk_forward/results/phase1
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics

from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED,
    build_regime_panel_confirmed,
    make_om25_tilt_score,
)
from scripts.tl25_v3 import (
    V3_LOCKED as TL25_LOCKED,
    build_tl25_panels,
    make_tl25_score,
)


# === Window definitions (copy from tasks/walk_forward/PLAN.md) ===
# Each entry: (window_id, is_start, is_end, oos_start, oos_end)
WINDOWS: dict[str, tuple[str, str, str, str]] = {
    "W01": ("2010-09-01", "2013-08-31", "2013-09-01", "2014-08-31"),
    "W02": ("2011-09-01", "2014-08-31", "2014-09-01", "2015-08-31"),
    "W03": ("2012-09-01", "2015-08-31", "2015-09-01", "2016-08-31"),
    "W04": ("2013-09-01", "2016-08-31", "2016-09-01", "2017-08-31"),
    "W05": ("2014-09-01", "2017-08-31", "2017-09-01", "2018-08-31"),
    "W06": ("2015-09-01", "2018-08-31", "2018-09-01", "2019-08-31"),
    "W07": ("2016-09-01", "2019-08-31", "2019-09-01", "2020-08-31"),
    "W08": ("2017-09-01", "2020-08-31", "2020-09-01", "2021-08-31"),
    "W09": ("2018-09-01", "2021-08-31", "2021-09-01", "2022-08-31"),
    "W10": ("2019-09-01", "2022-08-31", "2022-09-01", "2023-08-31"),
    "W11": ("2020-09-01", "2023-08-31", "2023-09-01", "2024-08-31"),
    "W12": ("2021-09-01", "2024-08-31", "2024-09-01", "2025-08-31"),
    "W13": ("2022-09-01", "2025-08-31", "2025-09-01", "2026-05-08"),
}


# === Param grids per strategy ===
# TL25 — 6 combos (3 weight variants × 2 DD stops)
TL25_GRID: list[dict] = [
    {"w_p": 0.40, "w_d": 0.20, "w_m": 0.40, "dd_stop": 0.20},  # V3 locked
    {"w_p": 0.40, "w_d": 0.20, "w_m": 0.40, "dd_stop": 0.15},
    {"w_p": 0.50, "w_d": 0.20, "w_m": 0.30, "dd_stop": 0.20},
    {"w_p": 0.50, "w_d": 0.20, "w_m": 0.30, "dd_stop": 0.15},
    {"w_p": 0.30, "w_d": 0.30, "w_m": 0.40, "dd_stop": 0.20},
    {"w_p": 0.30, "w_d": 0.30, "w_m": 0.40, "dd_stop": 0.15},
]

# OM25 — 9 combos (3 weight variants × 3 cadences)
OM25_GRID: list[dict] = [
    {"bull_uc": 0.7, "bull_cr": 0.3, "cadence": "monthly"},
    {"bull_uc": 0.7, "bull_cr": 0.3, "cadence": "biweekly"},
    {"bull_uc": 0.7, "bull_cr": 0.3, "cadence": "weekly"},
    {"bull_uc": 0.5, "bull_cr": 0.5, "cadence": "monthly"},
    {"bull_uc": 0.5, "bull_cr": 0.5, "cadence": "biweekly"},  # V3 locked
    {"bull_uc": 0.5, "bull_cr": 0.5, "cadence": "weekly"},
    {"bull_uc": 0.3, "bull_cr": 0.7, "cadence": "monthly"},
    {"bull_uc": 0.3, "bull_cr": 0.7, "cadence": "biweekly"},
    {"bull_uc": 0.3, "bull_cr": 0.7, "cadence": "weekly"},
]


# === Locked baselines (used in per-window OOS evaluation as comparator) ===
TL25_BASELINE = {"w_p": 0.40, "w_d": 0.20, "w_m": 0.40, "dd_stop": 0.20}
OM25_BASELINE = {"bull_uc": 0.5, "bull_cr": 0.5, "cadence": "biweekly"}


# === Universe → file mapping ===
UNIVERSE_FILES = {
    "nse500":   ROOT / "data/static/nse500_universe.csv",
    "nifty250": ROOT / "data/static/nifty250_universe.csv",
    "nifty100": ROOT / "data/static/nifty100_universe.csv",
}
PRODUCTION_UNIVERSE = {
    "tl25_v3": "nse500",
    "om25_v3": "nifty250",
}


# === Anti-overfit floors ===
DD_FLOOR = -0.45   # reject IS configs with DD worse than this
MIN_TRADES = 40    # reject IS configs with fewer than this many round trips


# ============================================================
# Helpers
# ============================================================

def _entry_dates_for_cadence(calendar, cadence: str) -> pd.DatetimeIndex:
    if cadence == "weekly":
        return fridays(calendar)
    if cadence == "biweekly":
        return biweekly_fridays(calendar)
    if cadence == "monthly":
        return monthly_first_trading_day(calendar)
    raise ValueError(f"unknown cadence {cadence!r}")


def _filter_dates(dates: pd.DatetimeIndex, start: str, end: str) -> pd.DatetimeIndex:
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    return dates[(dates >= s) & (dates <= e)]


def metrics_from_equity(eq: pd.DataFrame, start: str, end: str) -> dict:
    """Slice equity to window and compute Sharpe/CAGR/MaxDD/etc."""
    return period_metrics(eq, label="window", start=start, end=end)


# ============================================================
# Context (loaded once per process)
# ============================================================

class Context:
    """Pre-loaded panels + indicators shared across all backtests."""

    def __init__(self, prices_dir: Path, benchmark_path: Path,
                 regime_index_path: Path, universes: list[str]):
        print(f"[ctx] loading price panels from {prices_dir.name} ...", flush=True)
        t0 = time.time()
        self.close_panel, self.trade_panel = load_price_panels(prices_dir)
        self.calendar = self.close_panel.index
        self.benchmark = load_benchmark(benchmark_path)
        self.benchmark_aligned = self.benchmark.reindex(self.calendar).ffill()
        self.sma_200 = self.close_panel.rolling(200, min_periods=200).mean()
        self.atr_20 = self.close_panel.pct_change().rolling(20).std()
        print(f"  panels: {len(self.calendar)} days × {self.close_panel.shape[1]} symbols")

        # Date sets per cadence
        self.weekly_fri = fridays(self.calendar)
        self.biweekly_fri = biweekly_fridays(self.calendar)
        self.monthly_first = monthly_first_trading_day(self.calendar)

        # OM25 regime panel (loaded once)
        print(f"[ctx] OM25 regime panel ({regime_index_path.name}, 100-DMA, 3-day confirm) ...",
              flush=True)
        self.regime_panel = build_regime_panel_confirmed(
            regime_index_path,
            OM25_LOCKED["regime_ma_window"],
            OM25_LOCKED["regime_confirm_days"],
            calendar=self.calendar,
        )

        # Per-universe price + returns slices, plus TL25 panels
        self.universe_cache: dict[str, dict] = {}
        for u in universes:
            print(f"[ctx] building universe context for {u} ...", flush=True)
            symbols = load_universe(UNIVERSE_FILES[u])
            cols = [s for s in self.close_panel.columns if s in symbols]
            close_uni = self.close_panel[cols]
            returns_uni = close_uni.pct_change()
            # TL25 panels at the V3 locked windows; configs share these as long
            # as windows don't vary (current grid keeps windows fixed at V3).
            tl25_panels = build_tl25_panels(
                close_uni,
                dma_short=TL25_LOCKED["dma_short"],
                dma_long=TL25_LOCKED["dma_long"],
                dma_persist_ref=TL25_LOCKED["dma_persist_ref"],
                persistence_window=TL25_LOCKED["persistence_window"],
                drawdown_window=TL25_LOCKED["drawdown_window"],
                drawdown_concavity=TL25_LOCKED["drawdown_concavity"],
                momentum_window=TL25_LOCKED["momentum_window"],
            )
            self.universe_cache[u] = {
                "symbols": symbols, "cols": cols,
                "close_uni": close_uni, "returns_uni": returns_uni,
                "tl25_panels": tl25_panels,
            }
        print(f"[ctx] ready in {time.time() - t0:.1f}s", flush=True)


# ============================================================
# Strategy adapters
# ============================================================

def build_score_fn(strategy: str, params: dict, ctx: Context, universe: str):
    """Return (score_fn, cadence) for the strategy + params."""
    uc = ctx.universe_cache[universe]
    if strategy == "tl25_v3":
        score_fn = make_tl25_score(
            uc["tl25_panels"],
            w_persistence=params["w_p"],
            w_drawdown=params["w_d"],
            w_momentum=params["w_m"],
        )
        return score_fn, "biweekly"
    elif strategy == "om25_v3":
        score_fn = make_om25_tilt_score(
            uc["returns_uni"], ctx.regime_panel,
            bull_w_uc=params["bull_uc"], bull_w_cr=params["bull_cr"],
            bear_w_uc=OM25_LOCKED["bear_w_uc"],
            bear_w_cr=OM25_LOCKED["bear_w_cr"],
            return_filter=OM25_LOCKED["return_filter"],
            lookback=OM25_LOCKED["lookback"],
            min_obs=OM25_LOCKED["min_obs"],
        )
        return score_fn, params["cadence"]
    raise ValueError(f"unknown strategy {strategy!r}")


def strategy_engine_params(strategy: str, params: dict) -> dict:
    """Returns engine params (top_n, exit_buffer, stops, etc.) per strategy."""
    if strategy == "tl25_v3":
        return dict(
            top_n=TL25_LOCKED["top_n"],
            exit_buffer=TL25_LOCKED["exit_buffer"],
            max_weight=TL25_LOCKED["max_weight"],
            slippage=TL25_LOCKED["slippage"],
            atr_mult=0.0,
            atr_min_floor=params["dd_stop"],
            use_trailing_stop=params["dd_stop"] > 0,
            use_dma_exit=False,
            weekly_rank_check=True,
        )
    elif strategy == "om25_v3":
        return dict(
            top_n=OM25_LOCKED["top_n"],
            exit_buffer=OM25_LOCKED["exit_buffer"],
            max_weight=OM25_LOCKED["max_weight"],
            slippage=OM25_LOCKED["slippage"],
            atr_mult=0.0,
            atr_min_floor=OM25_LOCKED["drawdown_stop_pct"],
            use_trailing_stop=True,
            use_dma_exit=False,
            weekly_rank_check=False,
        )
    raise ValueError(f"unknown strategy {strategy!r}")


# ============================================================
# Single backtest call
# ============================================================

def run_one_backtest(strategy: str, params: dict, ctx: Context, universe: str,
                      entry_start: str, entry_end: str) -> Optional[dict]:
    """Run a single backtest restricted to entry_dates in [entry_start, entry_end].

    Returns dict with 'equity', 'trades', 'exits' DataFrames, or None if
    the engine couldn't run.
    """
    score_fn, cadence = build_score_fn(strategy, params, ctx, universe)
    entry_dates_all = _entry_dates_for_cadence(ctx.calendar, cadence)
    entry_dates = _filter_dates(entry_dates_all, entry_start, entry_end)
    weekly_filt = _filter_dates(ctx.weekly_fri, entry_start, entry_end)

    if len(entry_dates) == 0:
        return None

    engine_params = strategy_engine_params(strategy, params)
    res = run_strategy(
        close_panel=ctx.close_panel, trade_panel=ctx.trade_panel,
        calendar=ctx.calendar, benchmark_aligned=ctx.benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx.sma_200, atr_20_panel=ctx.atr_20,
        regime_panel=None, bear_exposure=0.0,
        initial_capital=1_000_000,
        **engine_params,
    )
    return res


# ============================================================
# Per-window orchestration
# ============================================================

def grid_for(strategy: str) -> list[dict]:
    return TL25_GRID if strategy == "tl25_v3" else OM25_GRID


def baseline_for(strategy: str) -> dict:
    return TL25_BASELINE if strategy == "tl25_v3" else OM25_BASELINE


def _config_id(strategy: str, params: dict) -> str:
    if strategy == "tl25_v3":
        return f"P{params['w_p']:.2f}_D{params['w_d']:.2f}_M{params['w_m']:.2f}_S{int(params['dd_stop']*100)}"
    return f"UC{params['bull_uc']:.1f}_CR{params['bull_cr']:.1f}_{params['cadence'][:1].upper()}"


def is_metrics(strategy: str, params: dict, ctx: Context, universe: str,
                is_start: str, is_end: str) -> dict:
    res = run_one_backtest(strategy, params, ctx, universe, is_start, is_end)
    if res is None or res.get("equity") is None or res["equity"].empty:
        return {"config_id": _config_id(strategy, params), "ok": False,
                "reason": "no equity"}
    eq = res["equity"]; trades = res["trades"]
    m = metrics_from_equity(eq, is_start, is_end)
    return {
        "config_id": _config_id(strategy, params),
        "ok": True,
        **{k: params[k] for k in params},
        "n_trades": len(trades),
        "is_cagr_pct": m.get("cagr_pct"),
        "is_sharpe": m.get("sharpe"),
        "is_vol_pct": m.get("vol_pct"),
        "is_max_dd_pct": m.get("max_dd_pct"),
    }


def oos_metrics(strategy: str, params: dict, ctx: Context, universe: str,
                 oos_start: str, oos_end: str) -> dict:
    res = run_one_backtest(strategy, params, ctx, universe, oos_start, oos_end)
    if res is None or res.get("equity") is None or res["equity"].empty:
        return {"config_id": _config_id(strategy, params), "ok": False}
    eq = res["equity"]; trades = res["trades"]
    m = metrics_from_equity(eq, oos_start, oos_end)
    return {
        "config_id": _config_id(strategy, params),
        "ok": True,
        **{k: params[k] for k in params},
        "n_trades": len(trades),
        "oos_cagr_pct": m.get("cagr_pct"),
        "oos_sharpe": m.get("sharpe"),
        "oos_vol_pct": m.get("vol_pct"),
        "oos_max_dd_pct": m.get("max_dd_pct"),
        "equity": eq,
    }


def sweep_window(strategy: str, universe: str, window_id: str, ctx: Context,
                  out_dir: Path) -> dict:
    """Per-window: IS sweep → pick top/bottom → OOS evaluate 3 configs."""
    is_start, is_end, oos_start, oos_end = WINDOWS[window_id]
    out_dir.mkdir(parents=True, exist_ok=True)

    # IS sweep — all combos
    is_rows = []
    for params in grid_for(strategy):
        r = is_metrics(strategy, params, ctx, universe, is_start, is_end)
        is_rows.append(r)
    is_df = pd.DataFrame(is_rows)
    is_df.to_csv(out_dir / "is_sweep.csv", index=False)

    # Apply floors
    eligible = is_df[
        (is_df.get("ok") == True)  # noqa: E712
        & (is_df.get("is_max_dd_pct", -100) > DD_FLOOR * 100)
        & (is_df.get("n_trades", 0) >= MIN_TRADES)
    ].copy()

    if eligible.empty:
        return {"window_id": window_id, "strategy": strategy, "universe": universe,
                "status": "no_eligible_is_configs", "is_df": is_df}

    # Sort by IS Sharpe (tie-break: lower turnover proxy = lower n_trades)
    eligible = eligible.sort_values(["is_sharpe", "n_trades"],
                                     ascending=[False, True])
    challenger_id = eligible.iloc[0]["config_id"]
    worst_id = eligible.iloc[-1]["config_id"]

    # Look up the params for challenger / worst
    def _params_by_id(cid: str) -> dict:
        for p in grid_for(strategy):
            if _config_id(strategy, p) == cid:
                return p
        return {}

    challenger_params = _params_by_id(challenger_id)
    worst_params = _params_by_id(worst_id)
    baseline_params = baseline_for(strategy)

    # OOS evaluations (3)
    oos_rows = []
    for tag, params in [("challenger", challenger_params),
                         ("baseline", baseline_params),
                         ("worst", worst_params)]:
        r = oos_metrics(strategy, params, ctx, universe, oos_start, oos_end)
        eq = r.pop("equity", None)
        r["role"] = tag
        oos_rows.append(r)
        # Save OOS equity for this role
        if eq is not None:
            eq_out = eq.copy()
            eq_out.to_csv(out_dir / f"oos_{tag}_equity.csv", index=False)
    oos_df = pd.DataFrame(oos_rows)
    oos_df.to_csv(out_dir / "oos_results.csv", index=False)

    # Per-window summary line
    by_role = {r["role"]: r for r in oos_rows}
    challenger_oos = by_role["challenger"].get("oos_sharpe")
    baseline_oos = by_role["baseline"].get("oos_sharpe")
    worst_oos = by_role["worst"].get("oos_sharpe")
    summary = {
        "window_id": window_id,
        "strategy": strategy,
        "universe": universe,
        "is_start": is_start, "is_end": is_end,
        "oos_start": oos_start, "oos_end": oos_end,
        "n_eligible": len(eligible),
        "challenger_id": challenger_id,
        "challenger_is_sharpe": eligible.iloc[0]["is_sharpe"],
        "challenger_oos_sharpe": challenger_oos,
        "challenger_oos_dd": by_role["challenger"].get("oos_max_dd_pct"),
        "baseline_oos_sharpe": baseline_oos,
        "baseline_oos_dd": by_role["baseline"].get("oos_max_dd_pct"),
        "worst_id": worst_id,
        "worst_is_sharpe": eligible.iloc[-1]["is_sharpe"],
        "worst_oos_sharpe": worst_oos,
        "best_minus_worst_oos": (challenger_oos - worst_oos)
            if (challenger_oos is not None and worst_oos is not None
                and not pd.isna(challenger_oos) and not pd.isna(worst_oos))
            else None,
        "challenger_beats_baseline": (challenger_oos - baseline_oos)
            if (challenger_oos is not None and baseline_oos is not None
                and not pd.isna(challenger_oos) and not pd.isna(baseline_oos))
            else None,
        "baseline_pass": (baseline_oos is not None
                          and not pd.isna(baseline_oos)
                          and baseline_oos >= 0.7),
    }
    return summary


# ============================================================
# Worker entry point (for multiprocessing — Phase 1+)
# ============================================================

_WORKER_CTX: Optional[Context] = None
_WORKER_CONFIG: Optional[dict] = None


def _worker_init(prices_dir_str: str, benchmark_str: str, regime_str: str,
                  universes_list: list[str]):
    global _WORKER_CTX, _WORKER_CONFIG
    _WORKER_CTX = Context(
        prices_dir=Path(prices_dir_str),
        benchmark_path=Path(benchmark_str),
        regime_index_path=Path(regime_str),
        universes=universes_list,
    )


def _worker_run(args):
    strategy, universe, window_id, out_dir_str = args
    out_dir = Path(out_dir_str)
    return sweep_window(strategy, universe, window_id, _WORKER_CTX, out_dir)


# ============================================================
# CLI entry
# ============================================================

def parse_args():
    ap = argparse.ArgumentParser(description="Walk-forward orchestrator")
    ap.add_argument("--strategies", nargs="+", default=["tl25_v3"],
                    choices=["tl25_v3", "om25_v3"])
    ap.add_argument("--universes", nargs="+", default=["nse500"],
                    help="One of: nse500, nifty250, nifty100, production "
                         "('production' is per-strategy locked universe).")
    ap.add_argument("--windows", nargs="+", default=["W01", "W07", "W13"],
                    help="Window IDs (W01-W13) or 'all'.")
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path,
                    default=ROOT / "indices_data_historical/NIFTY_100.csv")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "tasks/walk_forward/results/smell_test")
    ap.add_argument("--workers", type=int, default=1,
                    help=">1 enables ProcessPoolExecutor parallelism")
    return ap.parse_args()


def _expand_windows(window_args: list[str]) -> list[str]:
    if window_args == ["all"]:
        return list(WINDOWS.keys())
    bad = [w for w in window_args if w not in WINDOWS]
    if bad:
        raise SystemExit(f"unknown windows: {bad}. Valid: {list(WINDOWS.keys())}")
    return window_args


def _resolve_jobs(strategies: list[str], universes: list[str]) -> list[tuple[str, str]]:
    """Resolve (strategy, universe) pairs. 'production' means each strategy's locked universe."""
    jobs = []
    for s in strategies:
        for u in universes:
            if u == "production":
                jobs.append((s, PRODUCTION_UNIVERSE[s]))
            else:
                jobs.append((s, u))
    return list(dict.fromkeys(jobs))  # dedupe, preserve order


def main():
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    windows = _expand_windows(args.windows)
    jobs = _resolve_jobs(args.strategies, args.universes)
    universes_needed = sorted(set(u for _, u in jobs))

    print(f"[start] {len(jobs)} (strategy, universe) pairs × {len(windows)} windows "
          f"= {len(jobs) * len(windows)} window-runs")
    for s, u in jobs:
        print(f"        {s} on {u}")
    print(f"        windows: {' '.join(windows)}")
    print(f"        output: {args.output}")

    t0 = time.time()

    # === Run ===
    summaries: list[dict] = []
    if args.workers <= 1:
        # Sequential single-process
        ctx = Context(
            prices_dir=args.prices_dir,
            benchmark_path=args.benchmark,
            regime_index_path=args.regime_index,
            universes=universes_needed,
        )
        for s, u in jobs:
            for w in windows:
                t_w = time.time()
                out_dir = args.output / f"{s}_{u}" / w
                print(f"[run] {s}/{u}/{w} ...", flush=True)
                summary = sweep_window(s, u, w, ctx, out_dir)
                summaries.append(summary)
                print(f"      done in {time.time() - t_w:.1f}s — "
                      f"chal OOS={summary.get('challenger_oos_sharpe')} "
                      f"base OOS={summary.get('baseline_oos_sharpe')} "
                      f"best-worst={summary.get('best_minus_worst_oos')}",
                      flush=True)
    else:
        # Multiprocessing
        tasks = [(s, u, w, str(args.output / f"{s}_{u}" / w))
                 for (s, u) in jobs for w in windows]
        with ProcessPoolExecutor(
            max_workers=args.workers,
            initializer=_worker_init,
            initargs=(str(args.prices_dir), str(args.benchmark),
                      str(args.regime_index), universes_needed),
        ) as ex:
            futures = {ex.submit(_worker_run, t): t for t in tasks}
            for fut in as_completed(futures):
                t = futures[fut]
                summary = fut.result()
                summaries.append(summary)
                print(f"[done] {t[0]}/{t[1]}/{t[2]} — "
                      f"chal OOS={summary.get('challenger_oos_sharpe')} "
                      f"base OOS={summary.get('baseline_oos_sharpe')}",
                      flush=True)

    # === Cross summary ===
    cross_df = pd.DataFrame(summaries)
    cross_path = args.output / "cross_summary.csv"
    cross_df.to_csv(cross_path, index=False)

    # === Print pass-rate table to stdout ===
    print(f"\n{'=' * 90}")
    print("Pass-rate table (locked v3 baseline OOS Sharpe >= 0.7)")
    print(f"{'=' * 90}")
    if "baseline_pass" in cross_df.columns:
        pass_rates = (
            cross_df.groupby(["strategy", "universe"])["baseline_pass"]
            .agg(["sum", "count", "mean"])
            .rename(columns={"sum": "passes", "count": "windows", "mean": "pass_rate"})
        )
        pass_rates["pass_rate"] = (pass_rates["pass_rate"] * 100).round(1)
        print(pass_rates.to_string())

    # === IS-best vs IS-worst gap diagnostic ===
    print(f"\n{'=' * 90}")
    print("IS-best vs IS-worst OOS Sharpe gap per window")
    print(f"  gap < 0.20 → IS Sharpe ranking carries no signal for that window")
    print(f"{'=' * 90}")
    if "best_minus_worst_oos" in cross_df.columns:
        gaps = cross_df[
            ["strategy", "universe", "window_id", "best_minus_worst_oos",
             "challenger_beats_baseline"]
        ].copy()
        gaps["best_minus_worst_oos"] = gaps["best_minus_worst_oos"].round(3)
        gaps["challenger_beats_baseline"] = gaps["challenger_beats_baseline"].round(3)
        print(gaps.to_string(index=False))

    print(f"\n[wrote] {cross_path}")
    print(f"[done] {len(summaries)} window-runs in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
