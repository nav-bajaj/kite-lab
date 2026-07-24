"""Stress-regime reversal calls — pre-registered experiment (see PLAN.md).

Run:
    python tasks/stress_reversal_calls/stress_reversal_experiment.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols,
)
from tasks.donchian_channel.h4c_combo_grid import curve_metrics  # noqa: E402
from tasks.donchian_channel.h4f_us_marketfit import group_stats  # noqa: E402

START = pd.Timestamp("2011-01-01")
END = pd.Timestamp("2026-05-08")
TAIL_START = pd.Timestamp("2023-07-01")
SLIPPAGE = 0.002
CAP = 50
TRIGGER = 70.0
PERSIST_MIN = 0.60
DD_LO, DD_HI = 0.15, 0.40


def rolling_pctile(s: pd.Series, window=252, min_periods=120) -> pd.Series:
    return s.rolling(window, min_periods=min_periods).apply(
        lambda w: float((w <= w[-1]).mean()), raw=True)


def build_stress(close: pd.DataFrame) -> pd.Series:
    vix = pd.read_csv(ROOT / "indices_data_historical/INDIA_VIX.csv",
                      parse_dates=["date"]).set_index("date")["close"].ffill()
    n50 = pd.read_csv(ROOT / "indices_data_historical/NIFTY_50.csv",
                      parse_dates=["date"]).set_index("date")["close"].ffill()
    cal = close.index
    vix_p = rolling_pctile(vix).reindex(cal).ffill()
    dd = 1.0 - n50 / n50.rolling(252, min_periods=120).max()
    dd_p = rolling_pctile(dd).reindex(cal).ffill()
    below200 = 1.0 - (close > close.rolling(200, min_periods=200).mean()) \
        .sum(axis=1).astype(float) / close.notna().sum(axis=1)
    b_p = rolling_pctile(below200)
    disp = close.pct_change().std(axis=1)
    d_p = rolling_pctile(disp)
    score = 100 * (0.35 * vix_p + 0.25 * dd_p + 0.20 * b_p + 0.20 * d_p)
    return score.dropna()


def simulate(close, trade, stress, persist, dd, sma50, *, exit_mode: str):
    cal = close.index
    col = {s: j for j, s in enumerate(close.columns)}
    start_i = cal.get_loc(cal[cal >= START][0])
    end_i = cal.get_loc(cal[cal <= END][-1])
    active, calls = {}, []
    for i in range(start_i, end_i + 1):
        d = cal[i]
        # exits
        exits = []
        for sym, pos in active.items():
            held = i - pos["entry_i"]
            c = close.iat[i, col[sym]]
            if exit_mode == "time60":
                hit = held >= 60
            elif exit_mode == "time120":
                hit = held >= 120
            else:  # rec50
                s50 = sma50.iat[i, col[sym]]
                hit = held >= 120 or ((not pd.isna(c)) and (not pd.isna(s50))
                                      and c > s50 and held >= 10)
            if hit:
                exits.append(sym)
        for sym in exits:
            if i + 1 > end_i:
                continue
            px = trade.iat[i + 1, col[sym]]
            if pd.isna(px) or px <= 0:
                continue
            pos = active.pop(sym)
            calls.append({"symbol": sym, "entry_date": pos["entry_date"],
                          "signal_date": pos["signal_date"],
                          "exit_date": cal[i + 1],
                          "pnl_pct": px * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                          "hold_td": i + 1 - pos["entry_i"], "status": "closed"})
        # entries only on trigger days
        if d in stress.index and stress.loc[d] >= TRIGGER:
            pr = persist.iloc[i]
            dr = dd.iloc[i]
            elig = [(s, pr[s]) for s in close.columns
                    if s not in active and not pd.isna(pr[s])
                    and pr[s] >= PERSIST_MIN and not pd.isna(dr[s])
                    and DD_LO <= dr[s] <= DD_HI]
            elig.sort(key=lambda t: -t[1])
            for sym, _ in elig:
                if len(active) >= CAP or i + 1 > end_i:
                    break
                px = trade.iat[i + 1, col[sym]]
                if pd.isna(px) or px <= 0:
                    continue
                active[sym] = {"entry_date": cal[i + 1], "entry_i": i + 1,
                               "signal_date": d,
                               "entry_px": px * (1 + SLIPPAGE)}
    last = cal[end_i]
    for sym, pos in active.items():
        c = close.iat[end_i, col[sym]]
        calls.append({"symbol": sym, "entry_date": pos["entry_date"],
                      "signal_date": pos["signal_date"], "exit_date": last,
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls)


def slot_curve(calls, close, slots=CAP):
    cal = close.loc[(close.index >= START) & (close.index <= END)].index
    rets = close.pct_change()
    tot = pd.Series(0.0, index=cal)
    for _, c in calls.iterrows():
        sl = rets.loc[c["entry_date"]:c["exit_date"], c["symbol"]].reindex(cal).dropna()
        if len(sl) > 1:
            tot.loc[sl.index[1:]] += sl.iloc[1:]
    return (1 + tot / slots).cumprod()


def main():
    out = ROOT / "tasks/stress_reversal_calls" / \
        f"runs_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
    out.mkdir(parents=True, exist_ok=True)
    print("[stress] loading panels")
    p = load_ohlc_panels(symbols=load_universe_symbols())
    close, trade = p["close"], p["trade"]
    stress = build_stress(close)
    trig = stress[stress >= TRIGGER]
    runs = (trig.index.to_series().diff().dt.days > 7).cumsum()
    print(f"  trigger days: {len(trig)} in ~{runs.nunique()} episodes; "
          f"years: {sorted(set(trig.index.year))}")

    sma200 = close.rolling(200, min_periods=200).mean()
    persist = (close > sma200).rolling(252, min_periods=200).mean()
    dd = 1.0 - close / close.rolling(252, min_periods=200).max()
    sma50 = close.rolling(50, min_periods=50).mean()

    fwd = {k: close.shift(-k) / close - 1.0 for k in (20, 60, 120)}
    base_all = {k: float(f.loc[(f.index >= START) & (f.index <= END)]
                         .stack().mean()) for k, f in fwd.items()}

    for mode in ("time60", "time120", "rec50"):
        calls = simulate(close, trade, stress, persist, dd, sma50,
                         exit_mode=mode)
        calls.to_csv(out / f"calls_{mode}.csv", index=False)
        pv = slot_curve(calls, close)
        tail = pv.loc[pv.index >= TAIL_START]
        tail = tail / tail.iloc[0]
        g = group_stats(calls)
        cm = curve_metrics(pv)
        tm = curve_metrics(tail)
        yrs = (END - START).days / 365.25
        print(f"\n=== exit={mode} ===")
        print(f"  {g}")
        print(f"  calls/yr={g['n_closed']/yrs:.1f}  full={cm}  tail={tm}")
        # validity dry run on signal dates
        sig = calls.dropna(subset=["signal_date"])
        for k in (20, 60, 120):
            f = fwd[k]
            vals, base_same = [], []
            for _, c in sig.iterrows():
                dt, s = c["signal_date"], c["symbol"]
                if dt in f.index and s in f.columns and not pd.isna(f.loc[dt, s]):
                    vals.append(f.loc[dt, s])
                    base_same.append(float(f.loc[dt].mean()))
            v, b = np.array(vals), np.array(base_same)
            print(f"  fwd{k}d: call={v.mean()*100:+.2f}%  same-date univ="
                  f"{b.mean()*100:+.2f}%  sel_excess={(v.mean()-b.mean())*100:+.2f}pp  "
                  f"timing_excess={(b.mean()-base_all[k])*100:+.2f}pp  "
                  f"dir_lift={((v>0).mean()-(b>0).mean())*100:+.1f}pp  n={len(v)}")
    print(f"\n[wrote] {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
