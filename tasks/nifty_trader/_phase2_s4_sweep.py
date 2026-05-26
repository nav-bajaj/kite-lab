"""Parameter sweep on the S4 design: long-bias VIX tilt + breadth-deterioration short.

Goal: see if any parameter combo materially improves Sharpe / Calmar over the
B&H benchmark, in BOTH IS and OOS windows (robustness check)."""
from __future__ import annotations

from pathlib import Path

import itertools
import numpy as np
import pandas as pd

from backtest import BacktestConfig, run_backtest
from breadth_signals import build_or_load as load_breadth
from macro_signals import build_or_load as load_macro

INDICES_DIR = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
IS_START = pd.Timestamp("2010-01-04")
IS_END = pd.Timestamp("2018-12-31")
OOS_START = pd.Timestamp("2019-01-01")
OOS_END = pd.Timestamp("2026-05-12")


def load_nifty() -> pd.Series:
    df = pd.read_csv(INDICES_DIR / "NIFTY_50.csv", parse_dates=["date"])
    return df.set_index("date")["close"].sort_index()


def make_s4_signal(breadth_drop_20d_pp: float, vix_rise_10d: float,
                    breadth_floor: float, short_size: float, base_long: float):
    """Returns a signal function for given parameters."""
    def signal(nifty, panel):
        p = panel.reindex(nifty.index).ffill()
        # Default position: continuous VIX tilt
        z = p["vix_zscore_252d"].fillna(0)
        pos = (base_long + 0.3 * np.tanh(z / 1.5)).clip(0, 1)

        # Short overlay
        pct200 = p["pct_above_200dma"]
        pct200_roc = pct200 - pct200.shift(20)
        vix_z_roc = p["vix_zscore_252d"] - p["vix_zscore_252d"].shift(10)

        short_mask = (
            (pct200_roc < -breadth_drop_20d_pp) &
            (vix_z_roc > vix_rise_10d) &
            (pct200 < breadth_floor)
        )
        pos[short_mask] = short_size
        return pos

    return signal


def main() -> None:
    nifty = load_nifty()
    panel = pd.concat([load_breadth(), load_macro()], axis=1)

    grid = {
        "breadth_drop_20d_pp": [0.10, 0.15, 0.20],
        "vix_rise_10d":        [0.3, 0.5, 0.7],
        "breadth_floor":       [0.40, 0.50, 0.60],
        "short_size":          [-0.2, -0.3, -0.5],
        "base_long":           [0.7, 0.8, 0.9],
    }

    full = nifty.loc["2010-01-04":"2026-05-12"]
    is_n = nifty.loc[IS_START:IS_END]
    oos_n = nifty.loc[OOS_START:OOS_END]

    cfg_zero = BacktestConfig(explicit_cost_bps_per_rt=0, roll_cost_bps_per_month=0,
                                apply_roll_cost=False, name="zero")
    cfg_full = BacktestConfig(name="full cost")

    rows = []
    for combo in itertools.product(*grid.values()):
        params = dict(zip(grid.keys(), combo))
        sig = make_s4_signal(**params)

        # IS / OOS / Full with costs
        is_r = run_backtest(is_n, sig, panel, cfg_full)
        oos_r = run_backtest(oos_n, sig, panel, cfg_full)
        full_r = run_backtest(full, sig, panel, cfg_full)

        rows.append({
            **params,
            "full_cagr": full_r.cagr * 100,
            "full_sharpe": full_r.sharpe,
            "full_dd": full_r.max_drawdown * 100,
            "full_calmar": full_r.calmar,
            "is_sharpe": is_r.sharpe,
            "oos_sharpe": oos_r.sharpe,
            "is_dd": is_r.max_drawdown * 100,
            "oos_dd": oos_r.max_drawdown * 100,
            "is_cagr": is_r.cagr * 100,
            "oos_cagr": oos_r.cagr * 100,
            "n_trades": full_r.n_trades,
            "min_sharpe": min(is_r.sharpe, oos_r.sharpe),
        })

    df = pd.DataFrame(rows).sort_values("min_sharpe", ascending=False)

    # Print best by min(IS,OOS) sharpe
    print(f"\nGrid size: {len(df)} combinations\n")
    print(f"=== TOP 10 by min(IS, OOS) Sharpe ===")
    cols = ["breadth_drop_20d_pp", "vix_rise_10d", "breadth_floor", "short_size", "base_long",
             "is_sharpe", "oos_sharpe", "full_sharpe", "full_cagr", "full_dd", "full_calmar", "n_trades"]
    print(df[cols].head(10).round(3).to_string(index=False))

    # B&H benchmarks
    bh_full = run_backtest(full, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    bh_is = run_backtest(is_n, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    bh_oos = run_backtest(oos_n, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg_full)
    print(f"\n=== B&H benchmarks (with costs) ===")
    print(f"  Full:   CAGR {bh_full.cagr*100:.2f}%  Sharpe {bh_full.sharpe:.2f}  DD {bh_full.max_drawdown*100:.2f}%")
    print(f"  IS:     CAGR {bh_is.cagr*100:.2f}%  Sharpe {bh_is.sharpe:.2f}  DD {bh_is.max_drawdown*100:.2f}%")
    print(f"  OOS:    CAGR {bh_oos.cagr*100:.2f}%  Sharpe {bh_oos.sharpe:.2f}  DD {bh_oos.max_drawdown*100:.2f}%")

    # How many configs beat B&H Sharpe in BOTH IS and OOS?
    is_thr = bh_is.sharpe
    oos_thr = bh_oos.sharpe
    beat_both = df[(df["is_sharpe"] > is_thr) & (df["oos_sharpe"] > oos_thr)]
    print(f"\n=== Configs beating B&H Sharpe in BOTH IS AND OOS (with costs) ===")
    print(f"  {len(beat_both)} / {len(df)} ({len(beat_both)/len(df)*100:.1f}%)")
    if len(beat_both) > 0:
        print(beat_both[cols].head(10).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
