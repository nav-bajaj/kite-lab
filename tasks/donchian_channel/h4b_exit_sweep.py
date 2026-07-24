"""H4b — exit-rule sweep for the breakout-call list (founder iteration).

Fixed: entry = fresh cross above prior 20-day high AND top-quartile L6-style
momentum, uncapped, one call per symbol at a time, next-day OHLC/4 entry
(+20bps) / exit (-20bps), P&L net of slippage.

Exit grid (pre-registered in TASKS.md Phase 5b):
  don10 / don20 / don55   close < prior N-day low
  mid20                   close < 20-day channel midline (prior window)
  pct10_peak / pct15_peak close < (1 - x) * peak close since entry
  atr4_peak               close < peak * (1 - 4 * atr20_pct(signal date))
  time40                  40 trading days after entry, unconditional
  momq                    momentum pct-rank < 0.50
  don10_or_momq           first of don10 / momq

Run:
    python tasks/donchian_channel/h4b_exit_sweep.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.donchian_channel.channel_panels import (  # noqa: E402
    load_ohlc_panels, load_universe_symbols, donchian_upper, donchian_lower,
    breakout_cross,
)

SLIPPAGE = 0.002
QUARTILE = 0.75
START = pd.Timestamp("2010-06-01")
END = pd.Timestamp("2026-05-08")
ENTRY_N = 20

EXIT_RULES = ("don10", "don20", "don55", "mid20", "pct10_peak", "pct15_peak",
              "atr4_peak", "time40", "momq", "don10_or_momq")


def simulate(rule: str, ctx: dict) -> pd.DataFrame:
    close, trade = ctx["close"], ctx["trade"]
    cross, mom_rank = ctx["cross"], ctx["mom_rank"]
    don_low = ctx["don_lows"]
    mid20, atr_pct = ctx["mid20"], ctx["atr_pct"]
    cal = close.index
    col_ix = {s: j for j, s in enumerate(close.columns)}
    start_i = cal.get_loc(cal[cal >= START][0])
    end_i = cal.get_loc(cal[cal <= END][-1])

    active: dict[str, dict] = {}
    calls = []

    def exit_hit(sym, pos, i, d) -> bool:
        c = close.iat[i, col_ix[sym]]
        if pd.isna(c):
            return False
        if rule.startswith("don"):
            n = int(rule.split("_")[0][3:])
            lo = don_low[n].iat[i, col_ix[sym]]
            hit = (not pd.isna(lo)) and c < lo
            if rule == "don10_or_momq":
                r = mom_rank.iat[i, col_ix[sym]]
                hit = hit or ((not pd.isna(r)) and r < 0.50)
            return hit
        if rule == "mid20":
            m = mid20.iat[i, col_ix[sym]]
            return (not pd.isna(m)) and c < m
        if rule in ("pct10_peak", "pct15_peak"):
            x = 0.10 if rule == "pct10_peak" else 0.15
            return c < pos["peak"] * (1 - x)
        if rule == "atr4_peak":
            a = atr_pct.iat[i, col_ix[sym]]
            a = 0.02 if pd.isna(a) else a
            return c < pos["peak"] * (1 - 4 * a)
        if rule == "time40":
            return (i - pos["entry_i"]) >= 40
        if rule == "momq":
            r = mom_rank.iat[i, col_ix[sym]]
            return (not pd.isna(r)) and r < 0.50
        raise ValueError(rule)

    for i in range(start_i, end_i + 1):
        d = cal[i]
        # update peaks on signal-date closes (backward-looking)
        for sym, pos in active.items():
            c = close.iat[i, col_ix[sym]]
            if not pd.isna(c) and c > pos["peak"]:
                pos["peak"] = c
        # exits
        for sym in [s for s, p in list(active.items()) if exit_hit(s, p, i, d)]:
            if i + 1 > end_i:
                continue
            px = trade.iat[i + 1, col_ix[sym]]
            if pd.isna(px) or px <= 0:
                continue
            pos = active.pop(sym)
            eff = px * (1 - SLIPPAGE)
            calls.append({**{k: pos[k] for k in ("symbol", "signal_date",
                                                 "entry_date", "entry_px")},
                          "exit_signal": d, "exit_date": cal[i + 1],
                          "pnl_pct": eff / pos["entry_px"] - 1.0,
                          "hold_td": i + 1 - pos["entry_i"],
                          "status": "closed"})
        # entries
        row = cross.iloc[i]
        for sym in row.index[row.values]:
            if sym in active or i + 1 > end_i:
                continue
            r = mom_rank.iat[i, col_ix[sym]]
            if pd.isna(r) or r < QUARTILE:
                continue
            px = trade.iat[i + 1, col_ix[sym]]
            if pd.isna(px) or px <= 0:
                continue
            active[sym] = {"symbol": sym, "signal_date": d,
                           "entry_date": cal[i + 1], "entry_i": i + 1,
                           "entry_px": px * (1 + SLIPPAGE),
                           "peak": close.iat[i, col_ix[sym]]}

    last = cal[end_i]
    for sym, pos in active.items():
        c = close.iat[end_i, col_ix[sym]]
        calls.append({**{k: pos[k] for k in ("symbol", "signal_date",
                                             "entry_date", "entry_px")},
                      "exit_signal": None, "exit_date": last,
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls)


def signal_portfolio(calls: pd.DataFrame, close: pd.DataFrame) -> dict:
    """Daily equal-weight across active calls (signal-quality aggregate;
    ignores daily-rebalance frictions -- per-call stats stay the headline)."""
    cal = close.loc[(close.index >= START) & (close.index <= END)].index
    rets = close.pct_change()
    tot = pd.Series(0.0, index=cal)
    cnt = pd.Series(0, index=cal, dtype=int)
    for _, c in calls.iterrows():
        sl = rets.loc[c["entry_date"]:c["exit_date"], c["symbol"]].reindex(cal).dropna()
        if len(sl) <= 1:
            continue
        sl = sl.iloc[1:]
        tot.loc[sl.index] += sl
        cnt.loc[sl.index] += 1
    port = (tot / cnt.replace(0, np.nan)).fillna(0.0)
    pv = (1 + port).cumprod()
    years = (pv.index[-1] - pv.index[0]).days / 365.25
    cagr = pv.iloc[-1] ** (1 / years) - 1
    vol = port.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"sig_cagr_pct": round(cagr * 100, 2),
            "sig_sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "sig_max_dd_pct": round(dd * 100, 2),
            "mean_active": round(float(cnt.mean()), 1)}


def stats(calls: pd.DataFrame) -> dict:
    closed = calls[calls["status"] == "closed"]
    p = closed["pnl_pct"]
    yrs = pd.to_datetime(closed["signal_date"]).dt.year
    yearly_mean = closed.groupby(yrs)["pnl_pct"].mean()
    return {
        "n_closed": int(len(closed)),
        "n_open": int((calls["status"] == "open").sum()),
        "calls_per_year": round(len(closed) / 15.9, 1),
        "win_rate_pct": round(float((p > 0).mean()) * 100, 1),
        "mean_pnl_pct": round(float(p.mean()) * 100, 2),
        "median_pnl_pct": round(float(p.median()) * 100, 2),
        "p5_pnl_pct": round(float(p.quantile(.05)) * 100, 2),
        "p95_pnl_pct": round(float(p.quantile(.95)) * 100, 2),
        "tail_ratio": round(float(p.quantile(.95) / abs(p.quantile(.05))), 2),
        "median_hold_td": float(closed["hold_td"].median()),
        "pct_years_positive": round(float((yearly_mean > 0).mean()) * 100, 0),
        "worst_year_mean_pct": round(float(yearly_mean.min()) * 100, 2),
    }


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/donchian_channel/runs" / f"h4b_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[h4b] loading panels")
    panels = load_ohlc_panels(symbols=load_universe_symbols())
    high, low, close, trade = (panels["high"], panels["low"],
                               panels["close"], panels["trade"])
    up20 = donchian_upper(high, ENTRY_N)
    ctx = {
        "close": close, "trade": trade,
        "cross": breakout_cross(close, up20).fillna(False),
        "mom_rank": ((close / close.shift(126) - 1.0)
                     / (close.pct_change().rolling(126, min_periods=63).std()
                        * math.sqrt(252)).clip(lower=0.05)).rank(axis=1, pct=True),
        "don_lows": {n: donchian_lower(low, n) for n in (10, 20, 55)},
        "mid20": (up20 + donchian_lower(low, 20)) / 2.0,
        "atr_pct": close.pct_change().rolling(20).std(),
    }

    rows = {}
    yearly = {}
    for rule in EXIT_RULES:
        print(f"  simulating exit={rule}")
        calls = simulate(rule, ctx)
        calls.to_csv(out_dir / f"calls_{rule}.csv", index=False)
        rows[rule] = {**stats(calls), **signal_portfolio(calls, close)}
        closed = calls[calls["status"] == "closed"].copy()
        closed["year"] = pd.to_datetime(closed["signal_date"]).dt.year
        yearly[rule] = (closed.groupby("year")["pnl_pct"].mean() * 100).round(2)

    summary = pd.DataFrame(rows).T
    summary.index.name = "exit_rule"
    summary.to_csv(out_dir / "summary.csv")
    print("\n=== H4b exit sweep (entry: 20d breakout, top-quartile mom, uncapped) ===")
    print(summary.to_string())

    ytab = pd.DataFrame(yearly)
    ytab.to_csv(out_dir / "yearly_mean_pnl.csv")
    print("\n=== Yearly mean P&L per call (pct) ===")
    print(ytab.to_string())

    (out_dir / "config.json").write_text(json.dumps({
        "entry": "fresh cross above prior 20d high, mom pct-rank >= 0.75, uncapped",
        "exits": EXIT_RULES, "slippage": SLIPPAGE,
        "study": [str(START.date()), str(END.date())],
    }, indent=2))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
