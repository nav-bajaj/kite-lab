"""L6 v2 US retune — staged sweep on SP500 (503 symbols), IS 2010-2017.

Stage 1 (this script): lookback_months ∈ {3, 6, 9, 12}, all other params at
locked L6 v2 BASELINE. Selection on IS Sharpe.

Engine: scripts/_clean_engine.run_strategy() via _momentum_engine.run_momentum().

Run from repo root with venv active:
    python tasks/l6_us_tune_2026/_l6_us_retune.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (  # noqa: E402
    fridays, biweekly_fridays, monthly_first_trading_day, thursdays,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6_BASELINE,
    build_momentum_panels, run_momentum,
)
from scripts.multi_window_oos_eval import period_metrics  # noqa: E402


PRICES_DIR = ROOT / "us_equities_data"
UNIVERSE_CSV = ROOT / "data/static/us_equities_universe.csv"
BENCHMARK_CSV = ROOT / "data/benchmarks/spy.csv"

IS_START = pd.Timestamp("2010-01-01")
IS_END = pd.Timestamp("2017-12-31")


def load_sp500_universe(path: Path) -> set:
    df = pd.read_csv(path)
    mask = df["Index"].isin(["SP500", "BOTH"])
    return set(df[mask]["Symbol"].tolist())


def run_grid_sweep(grid: list[tuple[int, int]], tag: str = "stage1"):
    """grid: list of (lookback_months, skip_days) tuples."""
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / f"experiments/l6_us_tune/{ts}_{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")

    print(f"\n[load] panels from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK_CSV)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    universe = load_sp500_universe(UNIVERSE_CSV)
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    print(f"[univ] SP500: {len(cols)} symbols  "
          f"calendar {calendar[0].date()}..{calendar[-1].date()}")

    # Build momentum panels per (lookback, skip) pair — panel is parametrized
    # on both, so dedupe to avoid wasted work.
    panel_cache: dict[tuple[int, int], dict] = {}

    rows = []
    for (lm, skip) in grid:
        lookback_days = lm * 21
        key = (lookback_days, skip)
        if key not in panel_cache:
            print(f"\n[panels] L{lm} ({lookback_days}d) skip={skip} ...")
            panel_cache[key] = build_momentum_panels(
                close_uni, lookback_days=lookback_days, skip_days=skip,
            )
        panels = panel_cache[key]

        t0 = time.time()
        cfg = {**L6_BASELINE, "lookback_months": lm, "skip_days": skip}
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start=IS_START, end=IS_END, config=cfg,
        )
        elapsed = time.time() - t0
        if res is None or res["equity"].empty:
            print(f"  L{lm}-skip{skip}  [no result]")
            continue

        eq = res["equity"].copy()
        eq["date"] = pd.to_datetime(eq["date"])
        m = period_metrics(eq, f"IS_L{lm}s{skip}", IS_START, IS_END)
        row = {
            "lookback_months": lm,
            "lookback_days": lookback_days,
            "skip_days": skip,
            "is_cagr_pct": m.get("cagr_pct"),
            "is_sharpe": m.get("sharpe"),
            "is_vol_pct": m.get("vol_pct"),
            "is_max_dd_pct": m.get("max_dd_pct"),
            "is_yrs": m.get("yrs"),
            "trades": len(res["trades"]),
            "elapsed_s": round(elapsed, 1),
        }
        rows.append(row)
        eq.to_csv(out_dir / f"equity_L{lm}_s{skip}.csv", index=False)

        print(f"  L{lm}-skip{skip:<2d}  Sharpe={row['is_sharpe']:.2f}  "
              f"CAGR={row['is_cagr_pct']:6.2f}%  "
              f"DD={row['is_max_dd_pct']:6.2f}%  "
              f"trades={row['trades']:5d}  ({elapsed:.1f}s)")

    df = pd.DataFrame(rows).sort_values("is_sharpe", ascending=False)
    df.to_csv(out_dir / f"{tag}_results.csv", index=False)

    print(f"\n{'='*78}")
    print(f"{tag} — lookback × skip sweep (IS {IS_START.date()}..{IS_END.date()})")
    print(f"{'='*78}")
    print(df.to_string(index=False))
    print(f"\n[done] outputs → {out_dir}")
    return df


def run_param_sweep_multi(param_name: str, values: list,
                          tracks: list[dict], tag: str):
    """Sweep a single param across multiple base configs (tracks).

    tracks: list of dicts with track-specific overrides + a 'label' key.
    """
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / f"experiments/l6_us_tune/{ts}_{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")

    print(f"\n[load] panels from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK_CSV)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_sp500_universe(UNIVERSE_CSV)
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    print(f"[univ] SP500: {len(cols)} symbols")

    # Build momentum panels once per unique (lookback, skip) combo across tracks
    panel_cache: dict[tuple[int, int], dict] = {}
    rows = []

    for track in tracks:
        label = track.pop("label", "?")
        base_cfg = {**L6_BASELINE, **track}
        lookback_days = base_cfg["lookback_months"] * 21
        skip = base_cfg["skip_days"]
        key = (lookback_days, skip)
        if key not in panel_cache:
            panel_cache[key] = build_momentum_panels(
                close_uni, lookback_days=lookback_days, skip_days=skip,
            )
        panels = panel_cache[key]
        print(f"\n[track {label}] L{base_cfg['lookback_months']} skip={skip} "
              f"top_n={base_cfg['top_n']} vol_floor={base_cfg['vol_floor']} "
              f"min_hold={base_cfg['min_hold_days']}")
        print(f"[sweep] {param_name} ∈ {values}")

        for v in values:
            cfg = {**base_cfg, param_name: v}
            t0 = time.time()
            res = run_momentum(
                close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
                start=IS_START, end=IS_END, config=cfg,
            )
            elapsed = time.time() - t0
            if res is None or res["equity"].empty:
                print(f"  {label} {param_name}={v}  [no result]")
                continue
            eq = res["equity"].copy()
            eq["date"] = pd.to_datetime(eq["date"])
            m = period_metrics(eq, f"IS_{label}_{param_name}_{v}",
                               IS_START, IS_END)
            row = {
                "track": label,
                param_name: v,
                "is_cagr_pct": m.get("cagr_pct"),
                "is_sharpe": m.get("sharpe"),
                "is_vol_pct": m.get("vol_pct"),
                "is_max_dd_pct": m.get("max_dd_pct"),
                "trades": len(res["trades"]),
            }
            rows.append(row)
            eq.to_csv(out_dir / f"equity_{label}_{param_name}_{v}.csv", index=False)
            print(f"  {label} {param_name}={v:<5}  Sharpe={row['is_sharpe']:.2f}  "
                  f"CAGR={row['is_cagr_pct']:6.2f}%  "
                  f"DD={row['is_max_dd_pct']:6.2f}%  "
                  f"trades={row['trades']:5d}  ({elapsed:.1f}s)")

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / f"{tag}_results.csv", index=False)
    print(f"\n{'='*78}")
    print(f"{tag} — sweep {param_name} × tracks (IS {IS_START.date()}..{IS_END.date()})")
    print(f"{'='*78}")
    print(df.sort_values(["track", param_name]).to_string(index=False))
    print(f"\n  by IS Sharpe:")
    print(df.sort_values("is_sharpe", ascending=False).to_string(index=False))
    print(f"\n[done] outputs → {out_dir}")
    return df


US_WINDOWS = [
    ("IS",       "2010-01-01", "2017-12-31"),
    ("OOS_A",    "2018-01-01", "2019-12-31"),
    ("OOS_B",    "2020-01-01", "2022-12-31"),
    ("OOS_C",    "2023-01-01", "2026-05-13"),
    ("OOS_full", "2018-01-01", "2026-05-13"),
]


def run_oos_validation(tracks: list[dict], tag: str = "stage8_oos"):
    """Run each track over full 2010-today window, slice into IS+OOS windows."""
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / f"experiments/l6_us_tune/{ts}_{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")

    print(f"\n[load] panels from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK_CSV)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_sp500_universe(UNIVERSE_CSV)
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    print(f"[univ] SP500: {len(cols)} symbols")

    panel_cache: dict[tuple[int, int], dict] = {}
    all_window_rows = []
    end = pd.Timestamp(US_WINDOWS[-1][2])

    for track in tracks:
        label = track.pop("label", "?")
        base_cfg = {**L6_BASELINE, **track}
        lookback_days = base_cfg["lookback_months"] * 21
        skip = base_cfg["skip_days"]
        key = (lookback_days, skip)
        if key not in panel_cache:
            panel_cache[key] = build_momentum_panels(
                close_uni, lookback_days=lookback_days, skip_days=skip,
            )
        panels = panel_cache[key]

        print(f"\n[track {label}] L{base_cfg['lookback_months']} "
              f"skip={skip} top_n={base_cfg['top_n']} "
              f"buf={base_cfg['exit_buffer']} min_hold={base_cfg['min_hold_days']} "
              f"vol_floor={base_cfg['vol_floor']} sig={base_cfg['signal_day']} "
              f"stop={base_cfg['drawdown_stop']}")
        t0 = time.time()
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start=US_WINDOWS[0][1], end=end, config=base_cfg,
        )
        print(f"  full backtest done ({time.time()-t0:.1f}s)")
        eq = res["equity"].copy()
        eq["date"] = pd.to_datetime(eq["date"])
        eq.to_csv(out_dir / f"equity_{label}.csv", index=False)
        res["trades"].to_csv(out_dir / f"trades_{label}.csv", index=False)

        for wlabel, ws, we in US_WINDOWS:
            m = period_metrics(eq, wlabel, ws, we)
            all_window_rows.append({"track": label, **m})

    df = pd.DataFrame(all_window_rows)
    df.to_csv(out_dir / f"{tag}_windows.csv", index=False)

    # Pass criteria
    print(f"\n{'='*100}")
    print(f"OOS validation — windowed metrics")
    print(f"{'='*100}")
    for label in df["track"].unique():
        sub = df[df["track"] == label].set_index("window")
        print(f"\n--- {label} ---")
        cols_show = ["start", "end", "yrs", "cagr_pct", "sharpe", "vol_pct", "max_dd_pct"]
        print(sub.reindex([w[0] for w in US_WINDOWS])[cols_show].to_string())
        # Pass criteria
        is_s = sub.loc["IS", "sharpe"]
        oof_s = sub.loc["OOS_full", "sharpe"]
        oa = sub.loc["OOS_A", "sharpe"]
        ob = sub.loc["OOS_B", "sharpe"]
        oc = sub.loc["OOS_C", "sharpe"]
        oof_dd = sub.loc["OOS_full", "max_dd_pct"]
        failures = []
        if is_s < 1.0: failures.append(f"IS Sharpe {is_s:.2f} < 1.0")
        if oof_s < 1.0: failures.append(f"OOS-full Sharpe {oof_s:.2f} < 1.0")
        for nm, v in [("OOS_A", oa), ("OOS_B", ob), ("OOS_C", oc)]:
            if v < 0.7: failures.append(f"{nm} Sharpe {v:.2f} < 0.7")
        if oof_dd < -45.0:
            failures.append(f"OOS-full MaxDD {oof_dd:.2f}% < -45%")
        verdict = "PASS ✓" if not failures else f"FAIL ✗ ({len(failures)})"
        print(f"  Pass criteria: {verdict}")
        for f in failures:
            print(f"    - {f}")

    print(f"\n[done] outputs → {out_dir}")
    return df


def run_param_sweep(param_name: str, values: list, fixed: dict, tag: str):
    """Sweep a single parameter, holding everything else at L6 BASELINE + fixed overrides."""
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / f"experiments/l6_us_tune/{ts}_{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")

    print(f"\n[load] panels from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK_CSV)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_sp500_universe(UNIVERSE_CSV)
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    print(f"[univ] SP500: {len(cols)} symbols")

    base_cfg = {**L6_BASELINE, **fixed}
    lookback_days = base_cfg["lookback_months"] * 21
    skip = base_cfg["skip_days"]
    print(f"[fixed] L{base_cfg['lookback_months']} skip={skip}  "
          f"top_n={base_cfg['top_n']}  buf={base_cfg['exit_buffer']}  "
          f"vol_power={base_cfg['vol_power']}  min_hold={base_cfg['min_hold_days']}")
    print(f"[sweep] {param_name} ∈ {values}")

    panels = build_momentum_panels(
        close_uni, lookback_days=lookback_days, skip_days=skip,
    )

    rows = []
    for v in values:
        cfg = {**base_cfg, param_name: v}
        t0 = time.time()
        res = run_momentum(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
            start=IS_START, end=IS_END, config=cfg,
        )
        elapsed = time.time() - t0
        if res is None or res["equity"].empty:
            print(f"  {param_name}={v}  [no result]")
            continue
        eq = res["equity"].copy()
        eq["date"] = pd.to_datetime(eq["date"])
        m = period_metrics(eq, f"IS_{param_name}_{v}", IS_START, IS_END)
        row = {
            param_name: v,
            "is_cagr_pct": m.get("cagr_pct"),
            "is_sharpe": m.get("sharpe"),
            "is_vol_pct": m.get("vol_pct"),
            "is_max_dd_pct": m.get("max_dd_pct"),
            "trades": len(res["trades"]),
            "elapsed_s": round(elapsed, 1),
        }
        rows.append(row)
        eq.to_csv(out_dir / f"equity_{param_name}_{v}.csv", index=False)
        print(f"  {param_name}={v:<6}  Sharpe={row['is_sharpe']:.2f}  "
              f"CAGR={row['is_cagr_pct']:6.2f}%  "
              f"DD={row['is_max_dd_pct']:6.2f}%  "
              f"trades={row['trades']:5d}  ({elapsed:.1f}s)")

    df = pd.DataFrame(rows).sort_values("is_sharpe", ascending=False)
    df.to_csv(out_dir / f"{tag}_results.csv", index=False)
    print(f"\n{'='*78}")
    print(f"{tag} — sweep {param_name} (IS {IS_START.date()}..{IS_END.date()})")
    print(f"{'='*78}")
    print(df.to_string(index=False))
    print(f"\n[done] outputs → {out_dir}")
    return df


if __name__ == "__main__":
    import sys
    arg = sys.argv[1] if len(sys.argv) > 1 else "lookback_skip"
    if arg == "lookback_skip":
        grid = [(lm, skip) for lm in (3, 6, 9, 12, 15, 18) for skip in (0, 5, 21)]
        run_grid_sweep(grid, tag="stage1_lookback_skip")
    elif arg == "vol_floor":
        run_param_sweep(
            "vol_floor",
            [0.01, 0.02, 0.03, 0.05, 0.10, 0.20],
            fixed={"lookback_months": 12, "skip_days": 0},
            tag="stage2_vol_floor",
        )
    elif arg == "top_n":
        run_param_sweep(
            "top_n",
            [10, 12, 15, 18, 20, 24, 30, 40],
            fixed={"lookback_months": 12, "skip_days": 0, "vol_floor": 0.05},
            tag="stage3_top_n",
        )
    elif arg == "exit_buffer":
        run_param_sweep_multi(
            "exit_buffer",
            [0, 5, 10, 15, 20],
            tracks=[
                {"label": "A_top15", "lookback_months": 12, "skip_days": 0,
                 "vol_floor": 0.05, "top_n": 15},
                {"label": "B_top24", "lookback_months": 12, "skip_days": 0,
                 "vol_floor": 0.05, "top_n": 24},
            ],
            tag="stage4_exit_buffer",
        )
    elif arg == "min_hold_days":
        run_param_sweep_multi(
            "min_hold_days",
            [0, 5, 8, 14, 21],
            tracks=[
                {"label": "A_top15", "lookback_months": 12, "skip_days": 0,
                 "vol_floor": 0.05, "top_n": 15, "exit_buffer": 10},
                {"label": "B_top24", "lookback_months": 12, "skip_days": 0,
                 "vol_floor": 0.05, "top_n": 24, "exit_buffer": 5},
            ],
            tag="stage5_min_hold",
        )
    elif arg == "signal_day":
        run_param_sweep_multi(
            "signal_day",
            ["thursday", "friday"],
            tracks=[
                {"label": "A_top15", "lookback_months": 12, "skip_days": 0,
                 "vol_floor": 0.05, "top_n": 15, "exit_buffer": 10,
                 "min_hold_days": 0},
                {"label": "B_top24", "lookback_months": 12, "skip_days": 0,
                 "vol_floor": 0.05, "top_n": 24, "exit_buffer": 5,
                 "min_hold_days": 21},
            ],
            tag="stage6_signal_day",
        )
    elif arg == "oos":
        run_oos_validation(tracks=[
            {"label": "L6_locked",
             # Indian-locked BASELINE, ran unchanged on US SP500
             "lookback_months": 6, "skip_days": 0, "vol_floor": 0.05,
             "top_n": 24, "exit_buffer": 0, "min_hold_days": 8,
             "signal_day": "thursday", "drawdown_stop": 0.0},
            {"label": "A_top15", "lookback_months": 12, "skip_days": 0,
             "vol_floor": 0.05, "top_n": 15, "exit_buffer": 10,
             "min_hold_days": 0, "signal_day": "thursday",
             "drawdown_stop": 0.0},
            {"label": "B_top24", "lookback_months": 12, "skip_days": 0,
             "vol_floor": 0.05, "top_n": 24, "exit_buffer": 5,
             "min_hold_days": 21, "signal_day": "thursday",
             "drawdown_stop": 0.0},
        ])
    elif arg == "drawdown_stop":
        run_param_sweep_multi(
            "drawdown_stop",
            [0.0, 0.15, 0.20, 0.25, 0.30],
            tracks=[
                {"label": "A_top15", "lookback_months": 12, "skip_days": 0,
                 "vol_floor": 0.05, "top_n": 15, "exit_buffer": 10,
                 "min_hold_days": 0, "signal_day": "thursday"},
                {"label": "B_top24", "lookback_months": 12, "skip_days": 0,
                 "vol_floor": 0.05, "top_n": 24, "exit_buffer": 5,
                 "min_hold_days": 21, "signal_day": "thursday"},
            ],
            tag="stage7_drawdown_stop",
        )
    else:
        raise SystemExit(f"unknown stage: {arg}")
