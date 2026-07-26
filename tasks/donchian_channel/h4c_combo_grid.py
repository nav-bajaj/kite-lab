"""H4c — productization grid for the breakout-call list.

Fixed: entry = fresh cross above prior 20-day high AND top-quartile
momentum (within universe), CAP 50 active calls (momentum-rank priority),
next-day OHLC/4 +/- 20bps, P&L net of slippage, one call per symbol.

Grid (pre-registered, TASKS.md Phase 5c):
  universe   nse500 | n250
  lookback   126 | 252   (score = ret_N / max(ann vol_N, 0.05))
  exit       momq (rank < 0.5) | momq_or_ts20 (momq OR close < 0.80*peak)

Winner rule: highest 50-slot portfolio Sharpe, tie-break Calmar.
Emits summary.csv, per-arm calls CSVs, and report.json for the winner
(equity, monthly matrix, yearly table, open positions, hold buckets).

Run:
    python tasks/donchian_channel/h4c_combo_grid.py
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
    load_ohlc_panels, load_universe_symbols, donchian_upper, breakout_cross,
)

SLIPPAGE = 0.002
QUARTILE = 0.75
CAP = 50
START = pd.Timestamp("2010-06-01")
END = pd.Timestamp("2026-05-08")


def build_score_rank(close: pd.DataFrame, lb: int) -> pd.DataFrame:
    mom = close / close.shift(lb) - 1.0
    vol = (close.pct_change().rolling(lb, min_periods=lb // 2).std()
           * math.sqrt(252)).clip(lower=0.05)
    return (mom / vol).rank(axis=1, pct=True)


def simulate(close, trade, cross, mom_rank, *, use_ts20: bool):
    cal = close.index
    col = {s: j for j, s in enumerate(close.columns)}
    start_i = cal.get_loc(cal[cal >= START][0])
    end_i = cal.get_loc(cal[cal <= END][-1])
    active, calls, n_skipped = {}, [], 0
    counts = {}

    for i in range(start_i, end_i + 1):
        d = cal[i]
        for sym, pos in active.items():
            c = close.iat[i, col[sym]]
            if not pd.isna(c) and c > pos["peak"]:
                pos["peak"] = c
        # exits: momq always; ts20 optionally
        exits = []
        for sym, pos in active.items():
            c = close.iat[i, col[sym]]
            if pd.isna(c):
                continue
            r = mom_rank.iat[i, col[sym]]
            hit = (not pd.isna(r)) and r < 0.50
            reason = "momq"
            if use_ts20 and not hit and c < pos["peak"] * 0.80:
                hit, reason = True, "ts20"
            if hit:
                exits.append((sym, reason))
        for sym, reason in exits:
            if i + 1 > end_i:
                continue
            px = trade.iat[i + 1, col[sym]]
            if pd.isna(px) or px <= 0:
                continue
            pos = active.pop(sym)
            eff = px * (1 - SLIPPAGE)
            calls.append({**{k: pos[k] for k in ("symbol", "signal_date",
                                                 "entry_date", "entry_px")},
                          "exit_date": cal[i + 1], "reason": reason,
                          "pnl_pct": eff / pos["entry_px"] - 1.0,
                          "hold_td": i + 1 - pos["entry_i"],
                          "status": "closed"})
        # entries, momentum-rank priority into <=50 slots
        row = cross.iloc[i]
        cands = []
        for sym in row.index[row.values]:
            if sym in active:
                continue
            r = mom_rank.iat[i, col[sym]]
            if pd.isna(r) or r < QUARTILE:
                continue
            cands.append((sym, r))
        cands.sort(key=lambda t: -t[1])
        for sym, r in cands:
            if len(active) >= CAP:
                n_skipped += sum(1 for s, _ in cands if s not in active)
                break
            if i + 1 > end_i:
                continue
            px = trade.iat[i + 1, col[sym]]
            if pd.isna(px) or px <= 0:
                continue
            active[sym] = {"symbol": sym, "signal_date": d,
                           "entry_date": cal[i + 1], "entry_i": i + 1,
                           "entry_px": px * (1 + SLIPPAGE),
                           "peak": close.iat[i, col[sym]]}
        counts[d] = len(active)

    last = cal[end_i]
    for sym, pos in active.items():
        c = close.iat[end_i, col[sym]]
        calls.append({**{k: pos[k] for k in ("symbol", "signal_date",
                                             "entry_date", "entry_px")},
                      "exit_date": last, "reason": "open",
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_td": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls), pd.Series(counts, dtype=float), n_skipped


def slot_curve(calls, close, slots=CAP):
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
    pv = (1 + tot / slots).cumprod()   # idle slots earn 0
    return pv, cnt


def curve_metrics(pv):
    rets = pv.pct_change().dropna()
    years = (pv.index[-1] - pv.index[0]).days / 365.25
    cagr = pv.iloc[-1] ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"cagr_pct": round(cagr * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "max_dd_pct": round(dd * 100, 2),
            "calmar": round(float(cagr / abs(dd)), 3) if dd < 0 else None}


def group_stats(calls):
    closed = calls[calls.status == "closed"]
    p = closed.pnl_pct
    return {"n_closed": int(len(closed)),
            "n_open": int((calls.status == "open").sum()),
            "win_rate_pct": round(float((p > 0).mean()) * 100, 1),
            "mean_pnl_pct": round(float(p.mean()) * 100, 2),
            "median_pnl_pct": round(float(p.median()) * 100, 2),
            "p5_pnl_pct": round(float(p.quantile(.05)) * 100, 1),
            "p95_pnl_pct": round(float(p.quantile(.95)) * 100, 1),
            "median_hold_td": int(closed.hold_td.median()),
            "pct_ts20_exits": round(float((closed.reason == "ts20").mean()) * 100, 1)}


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/donchian_channel/runs" / f"h4c_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[h4c] loading panels")
    nse500 = load_universe_symbols()
    n250 = sorted(pd.read_csv(ROOT / "data/static/nifty250_universe.csv")
                  ["Symbol"].dropna().astype(str).unique())
    panels = load_ohlc_panels(symbols=nse500)

    arms = {}
    for uni_name, uni in (("nse500", nse500), ("n250", n250)):
        cols = [c for c in panels["close"].columns if c in set(uni)]
        close = panels["close"][cols]
        trade = panels["trade"][cols]
        high = panels["high"][cols]
        cross = breakout_cross(close, donchian_upper(high, 20)).fillna(False)
        for lb in (126, 252):
            rank = build_score_rank(close, lb)
            for exit_name, use_ts in (("momq", False), ("momq_ts20", True)):
                arm = f"{uni_name}_lb{lb}_{exit_name}"
                print(f"  simulating {arm}")
                calls, counts, skipped = simulate(close, trade, cross, rank,
                                                  use_ts20=use_ts)
                calls.to_csv(out_dir / f"calls_{arm}.csv", index=False)
                pv, cnt = slot_curve(calls, close)
                arms[arm] = {
                    "universe": uni_name, "lookback": lb, "exit": exit_name,
                    **group_stats(calls), **curve_metrics(pv),
                    "mean_active": round(float(counts.mean()), 1),
                    "pct_days_full": round(float((counts >= CAP).mean()) * 100, 1),
                    "skipped": int(skipped),
                    "_pv": pv, "_calls": calls,
                }

    summary = pd.DataFrame({k: {kk: vv for kk, vv in v.items()
                                if not kk.startswith("_")}
                            for k, v in arms.items()}).T
    summary.index.name = "arm"
    summary.to_csv(out_dir / "summary.csv")
    print("\n=== H4c grid (cap 50) ===")
    print(summary.to_string())

    winner = max(arms, key=lambda a: (arms[a]["sharpe"] or -9,
                                      arms[a]["calmar"] or -9))
    print(f"\n[winner by 50-slot Sharpe] {winner}")

    # ---- winner report data ----
    w = arms[winner]
    calls, pv = w["_calls"], w["_pv"]
    closed = calls[calls.status == "closed"]
    wk = pv.resample("W-FRI").last().dropna()
    dd = (pv / pv.cummax() - 1)
    dwk = dd.resample("W-FRI").min().reindex(wk.index)

    b = pd.read_csv(ROOT / "indices_data_historical/NIFTY_100.csv",
                    parse_dates=["date"]).set_index("date")["close"].ffill()
    b = b.reindex(pd.date_range(wk.index[0], wk.index[-1], freq="D")).ffill()
    bw = b.reindex(wk.index)
    bw = bw / bw.iloc[0]

    mret = pv.resample("ME").last().pct_change()
    mret.iloc[0] = pv.resample("ME").last().iloc[0] - 1
    mm = {}
    for d, v in mret.items():
        mm.setdefault(str(d.year), [None] * 12)[d.month - 1] = round(v * 100, 2)

    yt = []
    for y, g in calls.groupby(pd.to_datetime(calls.signal_date).dt.year):
        gc = g[g.status == "closed"]
        pvy = pv[pv.index.year == y]
        prior = pv[pv.index.year < y]
        yret = (pvy.iloc[-1] / (prior.iloc[-1] if len(prior) else 1) - 1) * 100
        yt.append({"year": int(y), "n": int(len(gc)),
                   "n_open": int((g.status == "open").sum()),
                   "win": round(float((gc.pnl_pct > 0).mean()) * 100, 1) if len(gc) else None,
                   "mean": round(float(gc.pnl_pct.mean()) * 100, 2) if len(gc) else None,
                   "median": round(float(gc.pnl_pct.median()) * 100, 2) if len(gc) else None,
                   "mean_all": round(float(g.pnl_pct.mean()) * 100, 2),
                   "port_ret": round(float(yret), 1)})

    bins = list(range(-60, 201, 10))
    hist, _ = np.histogram((closed.pnl_pct * 100).clip(-59.9, 199.9), bins=bins)

    op = calls[calls.status == "open"].sort_values("entry_date", ascending=False)
    hb = []
    for lo, hi, lab in [(0, 21, "<1m"), (21, 63, "1-3m"), (63, 126, "3-6m"),
                        (126, 252, "6-12m"), (252, 9999, ">12m")]:
        g = closed[(closed.hold_td >= lo) & (closed.hold_td < hi)]
        if len(g):
            hb.append({"bucket": lab, "n": int(len(g)),
                       "win": round(float((g.pnl_pct > 0).mean()) * 100, 1),
                       "mean": round(float(g.pnl_pct.mean()) * 100, 2)})

    years_span = (pv.index[-1] - pv.index[0]).days / 365.25
    report = {
        "winner": winner, "cap": CAP, "asof": str(END.date()),
        "grid": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                 for k, v in arms.items()},
        "headline": {**group_stats(calls), **curve_metrics(pv),
                     "calls_per_year": round(len(closed) / years_span, 1),
                     "mean_active": w["mean_active"],
                     "pct_days_full": w["pct_days_full"],
                     "total_mult": round(float(pv.iloc[-1]), 1),
                     "bench_mult": round(float(bw.iloc[-1]), 1),
                     "bench_cagr": round((float(bw.iloc[-1]) ** (1 / years_span) - 1) * 100, 1),
                     "open_mean_pnl": round(float(op.pnl_pct.mean()) * 100, 1)},
        "equity": {"dates": [str(d.date()) for d in wk.index],
                   "pv": [round(float(v), 4) for v in wk.values],
                   "bench": [round(float(v), 4) for v in bw.values],
                   "dd": [round(float(v) * 100, 2) for v in dwk.values]},
        "monthly": mm, "yearly": yt,
        "hist": {"edges": bins, "counts": [int(x) for x in hist]},
        "open_positions": [{"symbol": r.symbol,
                            "entry": str(pd.Timestamp(r.entry_date).date()),
                            "entry_px": round(r.entry_px, 1),
                            "pnl": round(r.pnl_pct * 100, 1),
                            "hold_td": int(r.hold_td)}
                           for r in op.head(20).itertuples()],
        "top_winners": [{"symbol": r.symbol,
                         "entry": str(pd.Timestamp(r.entry_date).date()),
                         "exit": str(pd.Timestamp(r.exit_date).date()),
                         "pnl": round(r.pnl_pct * 100, 1),
                         "hold_td": int(r.hold_td)}
                        for r in closed.nlargest(8, "pnl_pct").itertuples()],
        "hold_buckets": hb,
    }
    (out_dir / "report.json").write_text(json.dumps(report))
    print(f"[wrote] {out_dir.relative_to(ROOT)}/report.json")


if __name__ == "__main__":
    main()
