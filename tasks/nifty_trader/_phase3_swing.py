"""Phase 3 — test the swing-trading framework.

Baseline config: VIX/breadth bias + 5-day breakout entry + 5-day trailing stop +
10-day time stop. Then a parameter sweep on the key knobs.
"""
from __future__ import annotations

from pathlib import Path

import itertools
import numpy as np
import pandas as pd

from backtest import BacktestConfig, run_backtest
from breadth_signals import build_or_load as load_breadth
from macro_signals import build_or_load as load_macro
from swing_strategy import SwingConfig, run_swing

INDICES_DIR = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
IS_START = pd.Timestamp("2010-01-04")
IS_END = pd.Timestamp("2018-12-31")
OOS_START = pd.Timestamp("2019-01-01")
OOS_END = pd.Timestamp("2026-05-12")


def load_nifty() -> pd.Series:
    df = pd.read_csv(INDICES_DIR / "NIFTY_50.csv", parse_dates=["date"])
    return df.set_index("date")["close"].sort_index()


def feature_panel() -> pd.DataFrame:
    return pd.concat([load_breadth(), load_macro()], axis=1)


def make_signal_fn(cfg: SwingConfig):
    def fn(nifty, panel):
        return run_swing(nifty, panel, cfg)
    return fn


def evaluate(nifty, panel, swing_cfg: SwingConfig, bt_cfg: BacktestConfig, label: str):
    res = run_backtest(nifty, make_signal_fn(swing_cfg), panel, bt_cfg)
    tip = res.time_in_position
    # Count trade events: signal switches from 0→nonzero
    pos = res.position
    enters = (pos.shift(1).fillna(0) == 0) & (pos != 0)
    trades_count = int(enters.sum())
    avg_hold = None
    if trades_count > 0:
        # crude avg-hold: total nonzero days / trade count
        nonzero_days = int((pos != 0).sum())
        avg_hold = nonzero_days / trades_count
    return {
        "label": label,
        "cagr": res.cagr * 100,
        "sharpe": res.sharpe,
        "max_dd": res.max_drawdown * 100,
        "calmar": res.calmar,
        "tlong": tip["long"] * 100,
        "tflat": tip["flat"] * 100,
        "tshort": tip["short"] * 100,
        "n_trade_entries": trades_count,
        "avg_hold_days": avg_hold,
    }


def print_rows(rows, header):
    print(f"\n=== {header} ===")
    print(f"  {'label':<22} {'CAGR':>8} {'Sharpe':>8} {'MaxDD':>8} {'Calmar':>8} "
          f"{'TimeL':>7} {'TimeF':>7} {'TimeS':>7} {'Trades':>8} {'AvgHold':>8}")
    for r in rows:
        ah = f"{r['avg_hold_days']:.1f}" if r['avg_hold_days'] else "—"
        print(f"  {r['label']:<22} {r['cagr']:>7.2f}% {r['sharpe']:>8.2f} {r['max_dd']:>7.2f}% "
              f"{r['calmar']:>8.2f} {r['tlong']:>6.1f}% {r['tflat']:>6.1f}% {r['tshort']:>6.1f}% "
              f"{r['n_trade_entries']:>8} {ah:>8}")


def main():
    nifty = load_nifty()
    panel = feature_panel()
    full = nifty.loc["2010-01-04":"2026-05-12"]
    is_n = nifty.loc[IS_START:IS_END]
    oos_n = nifty.loc[OOS_START:OOS_END]

    cfg_full = BacktestConfig(name="5bp+10bp/mo")

    # Single baseline first
    base = SwingConfig()
    print(f"\nBaseline swing config:")
    print(f"  Bias: pct200>{base.bias_pct200_long} or <{base.bias_pct200_short}, vix_z floor")
    print(f"  Entry: breakout above/below trailing {base.entry_lookback}d high/low")
    print(f"  Exit: trailing {base.exit_lookback}d stop, time stop {base.time_stop_days}d")

    rows_full = [
        evaluate(full, panel, base, cfg_full, "Swing baseline"),
    ]
    # B&H
    bh_res = run_backtest(full, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    rows_full.append({
        "label": "Nifty B&H", "cagr": bh_res.cagr*100, "sharpe": bh_res.sharpe,
        "max_dd": bh_res.max_drawdown*100, "calmar": bh_res.calmar,
        "tlong": 100, "tflat": 0, "tshort": 0,
        "n_trade_entries": 1, "avg_hold_days": None,
    })
    print_rows(rows_full, "Full window 2010-2026, with costs")

    # IS / OOS
    is_rows = [evaluate(is_n, panel, base, cfg_full, "Swing IS")]
    bh_is = run_backtest(is_n, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    is_rows.append({"label":"Nifty B&H IS","cagr":bh_is.cagr*100,"sharpe":bh_is.sharpe,
                    "max_dd":bh_is.max_drawdown*100,"calmar":bh_is.calmar,
                    "tlong":100,"tflat":0,"tshort":0,"n_trade_entries":1,"avg_hold_days":None})
    print_rows(is_rows, "IS 2010-2018, with costs")

    oos_rows = [evaluate(oos_n, panel, base, cfg_full, "Swing OOS")]
    bh_oos = run_backtest(oos_n, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    oos_rows.append({"label":"Nifty B&H OOS","cagr":bh_oos.cagr*100,"sharpe":bh_oos.sharpe,
                     "max_dd":bh_oos.max_drawdown*100,"calmar":bh_oos.calmar,
                     "tlong":100,"tflat":0,"tshort":0,"n_trade_entries":1,"avg_hold_days":None})
    print_rows(oos_rows, "OOS 2019-2026, with costs")

    # Parameter sweep
    print(f"\n\n=== Parameter sweep (full window, with costs) ===")
    grid = {
        "entry_lookback":   [3, 5, 7, 10, 15],
        "exit_lookback":    [3, 5, 7, 10],
        "time_stop_days":   [7, 10, 15, 20],
        "bias_pct200_long": [0.50, 0.55, 0.60, 0.70],
    }
    rows = []
    for combo in itertools.product(*grid.values()):
        params = dict(zip(grid.keys(), combo))
        cfg = SwingConfig(**params)
        r_is = evaluate(is_n, panel, cfg, cfg_full, "IS")
        r_oos = evaluate(oos_n, panel, cfg, cfg_full, "OOS")
        r_full = evaluate(full, panel, cfg, cfg_full, "Full")
        rows.append({
            **params,
            "is_sharpe": r_is["sharpe"], "oos_sharpe": r_oos["sharpe"],
            "full_sharpe": r_full["sharpe"], "full_cagr": r_full["cagr"],
            "full_dd": r_full["max_dd"], "full_calmar": r_full["calmar"],
            "trades": r_full["n_trade_entries"], "avg_hold": r_full["avg_hold_days"],
            "min_sharpe": min(r_is["sharpe"], r_oos["sharpe"]),
        })

    df = pd.DataFrame(rows).sort_values("min_sharpe", ascending=False)
    cols = list(grid.keys()) + ["is_sharpe","oos_sharpe","full_sharpe","full_cagr","full_dd","full_calmar","trades","avg_hold"]
    print(f"\nGrid size: {len(df)}\n")
    print("TOP 15 by min(IS, OOS) Sharpe:")
    print(df[cols].head(15).round(3).to_string(index=False))

    # B&H benchmarks again
    print(f"\nB&H Sharpe: IS {bh_is.sharpe:.2f}, OOS {bh_oos.sharpe:.2f}, Full {bh_res.sharpe:.2f}")

    # Count combos that beat B&H in BOTH IS and OOS
    beat = df[(df["is_sharpe"] > bh_is.sharpe) & (df["oos_sharpe"] > bh_oos.sharpe)]
    print(f"\nConfigs beating B&H Sharpe in BOTH IS+OOS: {len(beat)} / {len(df)} ({len(beat)/len(df)*100:.1f}%)")
    if len(beat) > 0:
        print(beat[cols].head(10).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
