"""Drawdown-optimization pass: trail ladder + index regime gate + N250.

Phase A - trail ladder on the dip arms: trail in {10, 15, 20}% x sleeve
in {3m, 6m}, gate off/on. Phase B - gate-on versions of the three
breakout winners from Addendum 3. Phase C - the board winner re-run on
the Nifty 250 universe.

Regime gate: NIFTY 50 close > its 200DMA (merged historical + live
files; the only index with full 2010 coverage). Applied to NEW entries
only - open positions exit on their own rules. First ~4 months of the
window have no 200DMA (index history starts 2010-01) and are left
ungated.

Engine: faithful port of the dip_vs_breakout_calls simulate() with the
trail width parametric (peak on close from signal day, exit next day
fill at OHLC/4 +/- 20bps, momentum-decay exit rank < 0.35, cap 25,
rank-priority slots). No rank blending per founder instruction.

Run:  .venv/bin/python tasks/hourly_dip_swing/dd_optimization.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols, donchian_upper, breakout_cross,
)
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402
from tasks.dip_vs_breakout_calls.experiment import (  # noqa: E402
    slot_curve, curve_metrics, group_stats, cadence, yearly,
    CLIFF_SYMBOLS, TAIL_START, SLIPPAGE, QUARTILE, EXIT_RANK, START,
)

OUT_DIR = Path(__file__).resolve().parent
END = pd.Timestamp("2026-08-21")
N250_CSV = ROOT / "data/static/nifty250_universe.csv"


def load_regime_gate(calendar):
    hist = pd.read_csv(ROOT / "indices_data_historical/NIFTY_50.csv",
                       parse_dates=["date"])
    live = pd.read_csv(ROOT / "indices_data/NIFTY_50.csv",
                       parse_dates=["date"])
    idx = (pd.concat([hist, live]).drop_duplicates("date")
           .sort_values("date").set_index("date")["close"])
    sma = idx.rolling(200).mean()
    gate = (idx > sma)
    # pre-200DMA warmup (2010-01..2010-10): leave ungated
    gate[sma.isna()] = True
    return gate.reindex(calendar).ffill().fillna(True)


def simulate_trail(close, trade, sig, mom_rank, *, cap, end, trail,
                   start=None):
    """dip_vs_breakout_calls.simulate with parametric trail width.

    trail=None reproduces use_ts20=False; trail=0.20 reproduces
    use_ts20=True.
    """
    cal = close.index
    cl_v, tr_v = close.to_numpy(), trade.to_numpy()
    rk_v, sig_v = mom_rank.to_numpy(), sig.to_numpy()
    cols = close.columns
    start_i = int(np.searchsorted(cal, start if start is not None else START))
    end_i = int(np.searchsorted(cal, end, side="right")) - 1
    active, calls, n_skipped = {}, [], 0
    counts = np.zeros(end_i + 1 - start_i)

    for i in range(start_i, end_i + 1):
        for j, pos in active.items():
            c = cl_v[i, j]
            if not np.isnan(c) and c > pos["peak"]:
                pos["peak"] = c
        exits = []
        for j, pos in active.items():
            c = cl_v[i, j]
            if np.isnan(c):
                continue
            r = rk_v[i, j]
            hit = (not np.isnan(r)) and r < EXIT_RANK
            reason = "momq"
            if trail is not None and not hit and c < pos["peak"] * (1 - trail):
                hit, reason = True, "trail"
            if hit:
                exits.append((j, reason))
        for j, reason in exits:
            if i + 1 > end_i:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            pos = active.pop(j)
            calls.append({"symbol": cols[j], "signal_date": pos["signal_date"],
                          "entry_date": pos["entry_date"], "exit_date": cal[i + 1],
                          "reason": reason,
                          "pnl_pct": px * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                          "hold_td": i + 1 - pos["entry_i"], "status": "closed"})
        cand_j = np.where(sig_v[i])[0]
        cands = [(j, rk_v[i, j]) for j in cand_j
                 if j not in active and not np.isnan(rk_v[i, j])
                 and rk_v[i, j] >= QUARTILE]
        cands.sort(key=lambda t: -t[1])
        for j, r in cands:
            if len(active) >= cap:
                n_skipped += sum(1 for jj, _ in cands if jj not in active)
                break
            if i + 1 > end_i:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            active[j] = {"signal_date": cal[i], "entry_date": cal[i + 1],
                         "entry_i": i + 1, "entry_px": px * (1 + SLIPPAGE),
                         "peak": cl_v[i, j]}
        counts[i - start_i] = len(active)

    for j, pos in active.items():
        c = cl_v[end_i, j]
        calls.append({"symbol": cols[j], "signal_date": pos["signal_date"],
                      "entry_date": pos["entry_date"], "exit_date": cal[end_i],
                      "reason": "open",
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls), pd.Series(counts, index=cal[start_i:end_i + 1]), n_skipped


def run_arm(name, close, trade, sig, rank, trail, rows, yearlies):
    print(f"[ddo] simulating {name}")
    calls, counts, skipped = simulate_trail(close, trade, sig, rank,
                                            cap=25, end=END, trail=trail)
    calls.to_csv(OUT_DIR / f"calls_ddo_{name}.csv", index=False)
    pv = slot_curve(calls, close, 25, END)
    tail = pv.loc[pv.index >= TAIL_START]
    tail = tail / tail.iloc[0]
    m = curve_metrics(pv)
    rows[name] = {**cadence(calls, END), **group_stats(calls), **m,
                  **{f"tail_{k}": v for k, v in curve_metrics(tail).items()},
                  "mean_active": round(float(counts.mean()), 1),
                  "skipped": skipped}
    yearlies[name] = yearly(calls, pv)
    return rows[name]


def main():
    print("[ddo] loading panels (nse500 merged)")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    keep = [c for c in panels["close"].columns if c not in CLIFF_SYMBOLS]
    close, trade, high = (panels["close"][keep], panels["trade"][keep],
                          panels["high"][keep])
    gate = load_regime_gate(close.index)
    print(f"[ddo] regime gate: risk-on {round(float(gate.mean()) * 100, 1)}% of days")

    dip = ((close / close.shift(5) - 1.0) < -0.05).fillna(False)
    dip_gated = dip.mul(gate, axis=0)
    ranks = {"3m": build_score_rank(close, 63),
             "6m": build_score_rank(close, 126)}

    rows, yearlies = {}, {}

    # Phase A: trail ladder x sleeve x gate on the dip entry
    for lb_name, rank in ranks.items():
        for trail in (0.10, 0.15, 0.20):
            t = int(trail * 100)
            run_arm(f"dip_{lb_name}_ts{t}", close, trade, dip, rank,
                    trail, rows, yearlies)
            run_arm(f"dip_{lb_name}_ts{t}_gate", close, trade, dip_gated,
                    rank, trail, rows, yearlies)

    # Phase B: gate on the breakout winners from Addendum 3
    rank3 = ranks["3m"]
    for ch, trail, tag in [(10, None, "bo10_3m_xr"),
                           (20, 0.20, "bo20_3m_ts20"),
                           (50, 0.20, "bo50_3m_ts20")]:
        cross = breakout_cross(close, donchian_upper(high, ch)).fillna(False)
        run_arm(f"{tag}_gate", close, trade, cross.mul(gate, axis=0),
                rank3, trail, rows, yearlies)

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df["calmar"] = (df["cagr_pct"] / df["max_dd_pct"].abs()).round(3)
    df.to_csv(OUT_DIR / "summary_dd_optimization.csv")
    (OUT_DIR / "report_dd_optimization.json").write_text(
        json.dumps({"arms": rows, "yearly": yearlies}, indent=2, default=str))
    pd.set_option("display.width", 300)
    show = ["calls_per_year", "n_closed", "win_rate_pct", "median_pnl_pct",
            "median_hold_td", "cagr_pct", "sharpe", "max_dd_pct", "calmar",
            "tail_cagr_pct", "tail_sharpe", "tail_max_dd_pct", "mean_active"]
    print("\n=== drawdown optimization: trail ladder + regime gate ===")
    print(df[show].to_string())


if __name__ == "__main__":
    main()
