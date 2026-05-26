"""Phase 3 — panic-bounce strategy backtest + parameter sweep + robustness."""
from __future__ import annotations

from pathlib import Path

import itertools
import numpy as np
import pandas as pd

from backtest import BacktestConfig, run_backtest
from breadth_signals import build_or_load as load_breadth
from macro_signals import build_or_load as load_macro
from panic_bounce import PanicConfig, run_panic_bounce

INDICES_DIR = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
IS_START = pd.Timestamp("2010-01-04")
IS_END = pd.Timestamp("2018-12-31")
OOS_START = pd.Timestamp("2019-01-01")
OOS_END = pd.Timestamp("2026-05-12")


def load_nifty() -> pd.Series:
    return pd.read_csv(INDICES_DIR / "NIFTY_50.csv", parse_dates=["date"]).set_index("date")["close"].sort_index()


def feature_panel() -> pd.DataFrame:
    return pd.concat([load_breadth(), load_macro()], axis=1)


def make_signal_fn(cfg: PanicConfig):
    def fn(nifty, panel):
        return run_panic_bounce(nifty, panel, cfg)
    return fn


def evaluate(nifty, panel, panic_cfg: PanicConfig, bt_cfg: BacktestConfig, label: str):
    res = run_backtest(nifty, make_signal_fn(panic_cfg), panel, bt_cfg)
    tip = res.time_in_position
    pos = res.position
    enters = (pos.shift(1).fillna(0) == 0) & (pos != 0)
    n_trades = int(enters.sum())
    nz = int((pos != 0).sum())
    avg_hold = nz / n_trades if n_trades > 0 else 0
    return {
        "label": label,
        "cagr": res.cagr * 100,
        "sharpe": res.sharpe,
        "max_dd": res.max_drawdown * 100,
        "calmar": res.calmar,
        "tlong": tip["long"] * 100,
        "tflat": tip["flat"] * 100,
        "n_trades": n_trades,
        "avg_hold": avg_hold,
        "final_pv": res.equity.iloc[-1],
    }


def print_rows(rows, header):
    print(f"\n=== {header} ===")
    print(f"  {'label':<22} {'CAGR':>8} {'Sharpe':>8} {'MaxDD':>8} {'Calmar':>8} "
          f"{'Time-long':>10} {'Trades':>8} {'AvgHold':>9} {'FinalPV':>10}")
    for r in rows:
        print(f"  {r['label']:<22} {r['cagr']:>7.2f}% {r['sharpe']:>8.2f} {r['max_dd']:>7.2f}% "
              f"{r['calmar']:>8.2f} {r['tlong']:>9.1f}% {r['n_trades']:>8} {r['avg_hold']:>8.1f}d "
              f"₹{r['final_pv']/1e6:>7.2f}M")


def main():
    nifty = load_nifty()
    panel = feature_panel()
    full = nifty.loc["2010-01-04":"2026-05-12"]
    is_n = nifty.loc[IS_START:IS_END]
    oos_n = nifty.loc[OOS_START:OOS_END]

    cfg_full = BacktestConfig(name="5bp+10bp/mo")

    # ---------- Baseline run ----------
    base = PanicConfig()
    print(f"Baseline panic-bounce config:")
    print(f"  Trigger: {base.drop_window}-day return < {base.drop_threshold*100:.0f}%")
    print(f"    AND VIX > {base.vix_threshold}")
    print(f"  Entry confirm: {base.entry_confirm_required}")
    print(f"  Hold: {base.hold_days} days max, trailing stop on {base.trailing_stop_lookback}d low")
    print(f"  Cooldown: {base.cooldown_days} days")

    rows_full = [evaluate(full, panel, base, cfg_full, "Panic baseline FULL")]
    rows_is = [evaluate(is_n, panel, base, cfg_full, "Panic IS")]
    rows_oos = [evaluate(oos_n, panel, base, cfg_full, "Panic OOS")]

    # B&H comparators
    for window_label, nf, target_list in [("Full", full, rows_full), ("IS", is_n, rows_is), ("OOS", oos_n, rows_oos)]:
        bh = run_backtest(nf, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
        tip = bh.time_in_position
        target_list.append({
            "label": f"Nifty B&H {window_label}", "cagr": bh.cagr*100, "sharpe": bh.sharpe,
            "max_dd": bh.max_drawdown*100, "calmar": bh.calmar,
            "tlong": tip["long"]*100, "tflat": tip["flat"]*100,
            "n_trades": 1, "avg_hold": 0, "final_pv": bh.equity.iloc[-1],
        })

    print_rows(rows_full, "Full window 2010-2026, with costs")
    print_rows(rows_is, "IS 2010-2018, with costs")
    print_rows(rows_oos, "OOS 2019-2026, with costs")

    # ---------- Parameter sweep ----------
    print(f"\n\n=== Parameter sweep ===")
    grid = {
        "drop_window":      [5, 10, 15, 20],
        "drop_threshold":   [-0.03, -0.05, -0.07, -0.10],
        "vix_threshold":    [18, 20, 22, 25, 30],
        "hold_days":        [10, 15, 20, 25, 30],
        "use_trailing_stop": [True, False],
    }
    rows = []
    for combo in itertools.product(*grid.values()):
        params = dict(zip(grid.keys(), combo))
        cfg = PanicConfig(**params)
        r_is  = evaluate(is_n,  panel, cfg, cfg_full, "IS")
        r_oos = evaluate(oos_n, panel, cfg, cfg_full, "OOS")
        r_full = evaluate(full, panel, cfg, cfg_full, "Full")
        rows.append({
            **params,
            "is_sharpe": r_is["sharpe"], "oos_sharpe": r_oos["sharpe"],
            "full_sharpe": r_full["sharpe"], "full_cagr": r_full["cagr"],
            "full_dd": r_full["max_dd"], "full_calmar": r_full["calmar"],
            "full_trades": r_full["n_trades"], "full_avg_hold": r_full["avg_hold"],
            "min_sharpe": min(r_is["sharpe"], r_oos["sharpe"]),
            "is_trades": r_is["n_trades"], "oos_trades": r_oos["n_trades"],
        })

    df = pd.DataFrame(rows).sort_values("min_sharpe", ascending=False)
    cols = list(grid.keys()) + ["is_sharpe", "oos_sharpe", "full_sharpe", "full_cagr", "full_dd",
                                "full_calmar", "full_trades", "full_avg_hold"]
    print(f"Grid: {len(df)} combos")
    print(f"\nTop 15 by min(IS,OOS) Sharpe:")
    print(df[cols].head(15).round(3).to_string(index=False))

    # B&H Sharpes
    bh_is = run_backtest(is_n, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    bh_oos = run_backtest(oos_n, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    bh_full = run_backtest(full, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    print(f"\nB&H Sharpe: IS {bh_is.sharpe:.2f}, OOS {bh_oos.sharpe:.2f}, Full {bh_full.sharpe:.2f}")

    # How many beat B&H both in/out?
    beat = df[(df["is_sharpe"] > bh_is.sharpe) & (df["oos_sharpe"] > bh_oos.sharpe)]
    print(f"Configs beating B&H Sharpe BOTH IS+OOS: {len(beat)} / {len(df)} ({len(beat)/len(df)*100:.1f}%)")
    if len(beat) > 0:
        print(beat[cols].head(10).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
