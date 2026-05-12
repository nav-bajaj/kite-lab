"""Calmar-based IS selection study on a long anchored window.

Fixed universe (Nifty 250), fixed cadence (biweekly entry + weekly exit/DD
check), tight param grid varying weights and DD-stop only.

Long anchored IS (2009-09 → 2016-12) — same window as oos_retune_2026 — then
OOS (2017-01 → 2026-05).

Selection comparison:
  - IS-best by Sharpe (for reference)
  - IS-best by Calmar (the test)
  - Locked v3 baseline (production comparator)

The point: walk-forward Phase 4 ruled out Calmar over short 3y IS windows.
Could a long 7.3y IS window — where Calmar gets enough drawdown observations
to estimate cleanly — behave differently?

Output: tasks/calmar_study/
  - is_sweep_tl25_v3.csv, is_sweep_om25_v3.csv
  - oos_picks.csv
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics

from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.tl25_v3 import (
    V3_LOCKED as TL25_LOCKED, build_tl25_panels, make_tl25_score,
)


UNIVERSE = "nifty250"
UNIVERSE_FILE = ROOT / "data/static/nifty250_universe.csv"

IS_START, IS_END = "2009-09-01", "2016-12-31"
OOS_START, OOS_END = "2017-01-01", "2026-05-08"


# === Param grids (cadence fixed: biweekly entry + weekly exit check) ===

# TL25 — 5 weight variants × 2 DD stops = 10 combos
TL25_GRID = []
for w in [(0.40, 0.20, 0.40),   # locked v3 weights
          (0.50, 0.20, 0.30),
          (0.30, 0.30, 0.40),
          (0.50, 0.30, 0.20),
          (0.40, 0.40, 0.20)]:
    for stop in [0.15, 0.20]:
        TL25_GRID.append({
            "w_p": w[0], "w_d": w[1], "w_m": w[2], "dd_stop": stop,
        })

# OM25 — 3 UC/CR weights
OM25_GRID = []
for (uc, cr) in [(0.7, 0.3), (0.5, 0.5), (0.3, 0.7)]:
    OM25_GRID.append({"bull_uc": uc, "bull_cr": cr})


# Locked v3 baselines on Nifty 250
TL25_BASELINE = {"w_p": 0.40, "w_d": 0.20, "w_m": 0.40, "dd_stop": 0.20}
OM25_BASELINE = {"bull_uc": 0.5, "bull_cr": 0.5}


def _config_id(strategy, p):
    if strategy == "tl25_v3":
        return (f"P{p['w_p']:.2f}_D{p['w_d']:.2f}_M{p['w_m']:.2f}"
                f"_S{int(p['dd_stop']*100)}")
    return f"UC{p['bull_uc']:.1f}_CR{p['bull_cr']:.1f}"


def _filter_dates(dates, start, end):
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    return dates[(dates >= s) & (dates <= e)]


def _build_score_and_engine(strategy, params, ctx):
    if strategy == "tl25_v3":
        sf = make_tl25_score(
            ctx["tl25_panels"],
            w_persistence=params["w_p"],
            w_drawdown=params["w_d"],
            w_momentum=params["w_m"],
        )
        engine = dict(
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
        return sf, engine
    elif strategy == "om25_v3":
        sf = make_om25_tilt_score(
            ctx["returns_uni"], ctx["regime_panel"],
            bull_w_uc=params["bull_uc"], bull_w_cr=params["bull_cr"],
            bear_w_uc=OM25_LOCKED["bear_w_uc"],
            bear_w_cr=OM25_LOCKED["bear_w_cr"],
            return_filter=OM25_LOCKED["return_filter"],
            lookback=OM25_LOCKED["lookback"],
            min_obs=OM25_LOCKED["min_obs"],
        )
        engine = dict(
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
        return sf, engine
    raise ValueError(strategy)


def run_one(strategy, params, ctx, start, end):
    sf, engine = _build_score_and_engine(strategy, params, ctx)
    # Cadence is fixed: biweekly entry, weekly exit/DD/rank checks
    entry_all = biweekly_fridays(ctx["calendar"])
    entry_dates = _filter_dates(entry_all, start, end)
    weekly_filt = _filter_dates(ctx["weekly_fri"], start, end)
    if len(entry_dates) == 0:
        return None
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=sf, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        regime_panel=None, bear_exposure=0.0,
        initial_capital=1_000_000,
        **engine,
    )
    return res


def _metrics(res, start, end):
    m = period_metrics(res["equity"], "x", start, end)
    cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct")
    calmar = (cagr / abs(dd)) if (cagr is not None and dd not in (None, 0)
                                   and not pd.isna(dd) and abs(dd) > 1e-6) else None
    return dict(cagr_pct=cagr, sharpe=m.get("sharpe"), vol_pct=m.get("vol_pct"),
                max_dd_pct=dd,
                calmar=round(calmar, 3) if calmar is not None else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=ROOT / "tasks/calmar_study")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print("[load] price panels from nse500_data_merged ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    weekly_fri = fridays(calendar)

    print(f"[load] universe {UNIVERSE} ...")
    symbols = load_universe(UNIVERSE_FILE)
    cols = [s for s in close_panel.columns if s in symbols]
    close_uni = close_panel[cols]
    returns_uni = close_uni.pct_change()

    print("[panels] building TL25 panels + OM25 regime ...")
    tl25_panels = build_tl25_panels(
        close_uni,
        dma_short=TL25_LOCKED["dma_short"], dma_long=TL25_LOCKED["dma_long"],
        dma_persist_ref=TL25_LOCKED["dma_persist_ref"],
        persistence_window=TL25_LOCKED["persistence_window"],
        drawdown_window=TL25_LOCKED["drawdown_window"],
        drawdown_concavity=TL25_LOCKED["drawdown_concavity"],
        momentum_window=TL25_LOCKED["momentum_window"],
    )
    regime_panel = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    print(f"  setup done in {time.time()-t0:.1f}s — {len(cols)} symbols matched")

    ctx = dict(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned, sma_200=sma_200, atr_20=atr_20,
        weekly_fri=weekly_fri, regime_panel=regime_panel,
        tl25_panels=tl25_panels, returns_uni=returns_uni,
    )

    # === IS sweep ===
    is_results = {}
    for strategy, grid, baseline in [
        ("tl25_v3", TL25_GRID, TL25_BASELINE),
        ("om25_v3", OM25_GRID, OM25_BASELINE),
    ]:
        print(f"\n[IS] {strategy} — {len(grid)} combos, "
              f"{IS_START} → {IS_END} (Nifty 250, biweekly+weekly cadence)")
        rows = []
        t_is = time.time()
        for p in grid:
            res = run_one(strategy, p, ctx, IS_START, IS_END)
            if res is None or res["equity"].empty:
                continue
            m = _metrics(res, IS_START, IS_END)
            rows.append({
                "config_id": _config_id(strategy, p),
                "is_locked": _config_id(strategy, p) == _config_id(strategy, baseline),
                **{k: p[k] for k in p},
                "n_trades": len(res["trades"]),
                "is_cagr_pct": m["cagr_pct"], "is_sharpe": m["sharpe"],
                "is_vol_pct": m["vol_pct"], "is_max_dd_pct": m["max_dd_pct"],
                "is_calmar": m["calmar"],
            })
        df = pd.DataFrame(rows).sort_values("is_calmar", ascending=False).reset_index(drop=True)
        df.to_csv(args.output / f"is_sweep_{strategy}.csv", index=False)
        is_results[strategy] = df
        print(f"  done in {time.time()-t_is:.1f}s")

        cols_show = ["config_id", "is_locked", "is_calmar", "is_sharpe",
                     "is_cagr_pct", "is_max_dd_pct", "n_trades"]
        print(f"  All {len(df)} combos ranked by IS Calmar:")
        print(df[cols_show].to_string(index=False))

    # === Pick + OOS ===
    oos_rows = []
    for strategy, baseline in [("tl25_v3", TL25_BASELINE),
                                ("om25_v3", OM25_BASELINE)]:
        df = is_results[strategy]
        # min-trade floor
        elig = df[df["n_trades"] >= 40].copy() if len(df[df["n_trades"] >= 40]) else df

        calmar_pick = elig.sort_values("is_calmar", ascending=False).iloc[0]
        sharpe_pick = elig.sort_values("is_sharpe", ascending=False).iloc[0]

        def _params_by_id(cid):
            grid = TL25_GRID if strategy == "tl25_v3" else OM25_GRID
            for p in grid:
                if _config_id(strategy, p) == cid:
                    return p
            return None

        roles = []
        roles.append(("calmar_pick", _params_by_id(calmar_pick["config_id"])))
        if sharpe_pick["config_id"] != calmar_pick["config_id"]:
            roles.append(("sharpe_pick", _params_by_id(sharpe_pick["config_id"])))
        else:
            roles.append(("sharpe_pick", _params_by_id(sharpe_pick["config_id"])))
            print(f"  Note: Calmar-pick == Sharpe-pick for {strategy}: "
                  f"{calmar_pick['config_id']}")
        baseline_id = _config_id(strategy, baseline)
        if baseline_id not in (calmar_pick["config_id"], sharpe_pick["config_id"]):
            roles.append(("baseline", baseline))
        else:
            roles.append(("baseline", baseline))

        # Run OOS — dedupe identical configs
        seen = {}
        print(f"\n[OOS] {strategy} — running OOS {OOS_START} → {OOS_END}")
        for tag, params in roles:
            cid = _config_id(strategy, params)
            if cid in seen:
                # Copy seen results, just retag
                src = seen[cid]
                oos_rows.append({**src, "role": tag})
                continue
            res = run_one(strategy, params, ctx, OOS_START, OOS_END)
            if res is None or res["equity"].empty:
                continue
            m = _metrics(res, OOS_START, OOS_END)
            is_row = df[df["config_id"] == cid].iloc[0]
            row = {
                "role": tag, "strategy": strategy, "config_id": cid,
                "n_trades": len(res["trades"]),
                "is_calmar": is_row["is_calmar"], "is_sharpe": is_row["is_sharpe"],
                "is_cagr_pct": is_row["is_cagr_pct"],
                "is_max_dd_pct": is_row["is_max_dd_pct"],
                "oos_cagr_pct": m["cagr_pct"], "oos_sharpe": m["sharpe"],
                "oos_max_dd_pct": m["max_dd_pct"], "oos_calmar": m["calmar"],
                "oos_vol_pct": m["vol_pct"],
            }
            seen[cid] = row
            oos_rows.append(row)

    oos_df = pd.DataFrame(oos_rows)
    oos_df.to_csv(args.output / "oos_picks.csv", index=False)

    print(f"\n{'=' * 100}")
    print(f"OOS COMPARISON — Nifty 250, biweekly entry + weekly checks")
    print(f"  IS anchored: {IS_START} → {IS_END}    OOS: {OOS_START} → {OOS_END}")
    print(f"{'=' * 100}")
    show = ["strategy", "role", "config_id",
            "is_calmar", "is_sharpe", "is_max_dd_pct",
            "oos_calmar", "oos_sharpe", "oos_cagr_pct", "oos_max_dd_pct"]
    print(oos_df[show].to_string(index=False))

    print(f"\n[wrote] {args.output}/is_sweep_tl25_v3.csv")
    print(f"[wrote] {args.output}/is_sweep_om25_v3.csv")
    print(f"[wrote] {args.output}/oos_picks.csv")


if __name__ == "__main__":
    main()
