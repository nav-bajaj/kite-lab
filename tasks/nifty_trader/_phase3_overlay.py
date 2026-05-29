"""Phase 3 — panic-bounce as an OVERLAY on long Nifty (uses futures leverage).

Hypothesis: the panic-bounce trade has strong per-day edge but fires too rarely
to be a standalone strategy (only ~5-15% time-in-market). Layered on top of a
long Nifty baseline, the overlay captures the panic-bounce alpha PLUS the
structural drift.

Position: 1.0 (always long) + add_size during panic signal → net 1.0 or 2.0

This adds leverage. Nifty futures naturally provide it — ₹25L capital can back
~₹150L notional (6x). 2x exposure is conservative.

Roll costs and explicit trade costs apply to the FULL notional (including the
overlay portion). Slippage applies on overlay entries/exits.
"""
from __future__ import annotations

from pathlib import Path

import itertools
import pandas as pd
import numpy as np

from backtest import BacktestConfig, run_backtest
from breadth_signals import build_or_load as load_breadth
from macro_signals import build_or_load as load_macro
from panic_bounce import PanicConfig, run_panic_bounce

INDICES_DIR = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
IS_START = pd.Timestamp("2010-01-04")
IS_END = pd.Timestamp("2018-12-31")
OOS_START = pd.Timestamp("2019-01-01")
OOS_END = pd.Timestamp("2026-05-12")


def load_nifty():
    return pd.read_csv(INDICES_DIR / "NIFTY_50.csv", parse_dates=["date"]).set_index("date")["close"].sort_index()


def feature_panel():
    return pd.concat([load_breadth(), load_macro()], axis=1)


def overlay_signal_fn(panic_cfg: PanicConfig, add_size: float = 1.0):
    def fn(nifty, panel):
        panic = run_panic_bounce(nifty, panel, panic_cfg)
        # Baseline 1.0 + overlay (panic positions are already 1.0 or 0 from panic_bounce)
        # Scale panic by add_size, add to baseline 1.0
        baseline = pd.Series(1.0, index=nifty.index)
        return baseline + (panic / panic_cfg.long_size) * add_size if panic_cfg.long_size > 0 else baseline
    return fn


def bh_fn(nifty, panel):
    return pd.Series(1.0, index=nifty.index)


def evaluate(nifty, panel, sig_fn, bt_cfg, label):
    res = run_backtest(nifty, sig_fn, panel, bt_cfg)
    tip = res.time_in_position
    pos = res.position
    # Count "overlay-on" days (position > 1.0)
    overlay_on = (pos > 1.0).sum()
    # Trade entries: 1.0 → 2.0 transitions
    enters = (pos.shift(1).fillna(1.0) == 1.0) & (pos > 1.0)
    n_entries = int(enters.sum())
    return {
        "label": label, "cagr": res.cagr*100, "sharpe": res.sharpe,
        "max_dd": res.max_drawdown*100, "calmar": res.calmar,
        "overlay_on_pct": overlay_on / len(pos) * 100, "n_entries": n_entries,
        "final_pv": res.equity.iloc[-1],
    }


def print_rows(rows, header):
    print(f"\n=== {header} ===")
    print(f"  {'label':<28} {'CAGR':>8} {'Sharpe':>8} {'MaxDD':>8} {'Calmar':>8} "
          f"{'Overlay%':>10} {'Entries':>9} {'FinalPV':>12}")
    for r in rows:
        print(f"  {r['label']:<28} {r['cagr']:>7.2f}% {r['sharpe']:>8.2f} {r['max_dd']:>7.2f}% "
              f"{r['calmar']:>8.2f} {r['overlay_on_pct']:>9.1f}% {r['n_entries']:>9} "
              f"₹{r['final_pv']/1e6:>9.2f}M")


def main():
    nifty = load_nifty()
    panel = feature_panel()
    full = nifty.loc["2010-01-04":"2026-05-12"]
    is_n = nifty.loc[IS_START:IS_END]
    oos_n = nifty.loc[OOS_START:OOS_END]

    cfg_full = BacktestConfig(name="5bp+10bp/mo", long_cap=2.0)

    # Best panic config from earlier sweep
    base_panic = PanicConfig(
        drop_window=15, drop_threshold=-0.03, vix_threshold=25.0,
        hold_days=15, use_trailing_stop=True, cooldown_days=5,
    )

    # Compare baselines
    rows_full = []
    rows_full.append(evaluate(full, panel, bh_fn, cfg_full, "Pure long Nifty B&H"))
    for add in [0.5, 1.0, 1.5]:
        rows_full.append(evaluate(full, panel,
                                    overlay_signal_fn(base_panic, add),
                                    cfg_full, f"B&H + panic +{add}"))

    print_rows(rows_full, "Full window — overlay variants (with costs)")

    # IS / OOS split
    rows_is = [evaluate(is_n, panel, bh_fn, cfg_full, "B&H IS")]
    rows_oos = [evaluate(oos_n, panel, bh_fn, cfg_full, "B&H OOS")]
    for add in [0.5, 1.0, 1.5]:
        rows_is.append(evaluate(is_n, panel, overlay_signal_fn(base_panic, add), cfg_full,
                                 f"B&H + panic +{add} IS"))
        rows_oos.append(evaluate(oos_n, panel, overlay_signal_fn(base_panic, add), cfg_full,
                                  f"B&H + panic +{add} OOS"))
    print_rows(rows_is, "IS 2010-2018")
    print_rows(rows_oos, "OOS 2019-2026")

    # Sweep on overlay params
    print(f"\n\n=== Sweep: panic config + overlay size ===")
    grid = {
        "drop_window":     [10, 15, 20],
        "drop_threshold":  [-0.03, -0.05, -0.07],
        "vix_threshold":   [20, 22, 25],
        "hold_days":       [10, 15, 20],
        "add_size":        [0.5, 1.0],
    }
    rows = []
    for combo in itertools.product(*grid.values()):
        params = dict(zip(grid.keys(), combo))
        add = params.pop("add_size")
        panic = PanicConfig(**params, use_trailing_stop=True)
        sig = overlay_signal_fn(panic, add)
        r_is = evaluate(is_n, panel, sig, cfg_full, "")
        r_oos = evaluate(oos_n, panel, sig, cfg_full, "")
        r_full = evaluate(full, panel, sig, cfg_full, "")
        rows.append({
            **params, "add_size": add,
            "is_sharpe": r_is["sharpe"], "oos_sharpe": r_oos["sharpe"],
            "full_sharpe": r_full["sharpe"], "full_cagr": r_full["cagr"],
            "full_dd": r_full["max_dd"], "full_calmar": r_full["calmar"],
            "entries": r_full["n_entries"], "overlay_pct": r_full["overlay_on_pct"],
            "min_sharpe": min(r_is["sharpe"], r_oos["sharpe"]),
        })

    df = pd.DataFrame(rows).sort_values("min_sharpe", ascending=False)
    cols = list(grid.keys()) + ["is_sharpe","oos_sharpe","full_sharpe","full_cagr","full_dd",
                                "full_calmar","entries","overlay_pct"]
    print(f"\nGrid: {len(df)}\nTop 15 by min(IS,OOS) Sharpe:")
    print(df[cols].head(15).round(3).to_string(index=False))

    bh_is = run_backtest(is_n, bh_fn, panel, cfg_full)
    bh_oos = run_backtest(oos_n, bh_fn, panel, cfg_full)
    print(f"\nB&H Sharpe (with costs): IS {bh_is.sharpe:.2f}, OOS {bh_oos.sharpe:.2f}")

    beat = df[(df["is_sharpe"] > bh_is.sharpe) & (df["oos_sharpe"] > bh_oos.sharpe)]
    print(f"Configs beating B&H Sharpe BOTH IS+OOS: {len(beat)}/{len(df)} ({len(beat)/len(df)*100:.1f}%)")
    if len(beat) > 0:
        print(beat[cols].head(10).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
