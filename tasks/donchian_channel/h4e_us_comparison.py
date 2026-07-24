"""H4e — the Phase 5c breakout-call rules on US large caps, vs India.

Universe: S&P 500 union Nasdaq 100 (current snapshot, 516 symbols),
prices from yfinance (adjusted; EODHD sub lapsed -- disclosed).
Rules identical to Phase 5c: fresh 20-day-high cross, top-quartile
momentum, cap 50 with rank priority, exits momq / momq+20% trail,
lookbacks 126d / 252d, 20bps each way, 2010-06-01..2026-05-08.
Benchmark SPY. Reuses simulate()/slot_curve() from h4c_combo_grid so
the engines are byte-identical.

Run:
    python tasks/donchian_channel/h4e_us_comparison.py
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
    load_ohlc_panels, donchian_upper, breakout_cross,
)
from tasks.donchian_channel.h4c_combo_grid import (  # noqa: E402
    build_score_rank, simulate, slot_curve, curve_metrics, group_stats,
    CAP, START, END,
)

INDIA_RUN = ROOT / "tasks/donchian_channel/runs/h4c_20260722_193236/report.json"


def weekly(pv):
    return pv.resample("W-FRI").last().dropna()


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/donchian_channel/runs" / f"h4e_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[h4e] loading US panels")
    uni = pd.read_csv(ROOT / "data/static/us_equities_universe.csv")
    symbols = sorted(uni["Symbol"].dropna().astype(str).unique())
    panels = load_ohlc_panels(prices_dir=ROOT / "us_equities_data",
                              symbols=symbols)
    high, low = panels["high"], panels["low"]
    close, trade = panels["close"], panels["trade"]
    print(f"  panel {close.shape}, {close.index.min().date()} .. {close.index.max().date()}")

    cross = breakout_cross(close, donchian_upper(high, 20)).fillna(False)

    arms = {}
    for lb in (126, 252):
        rank = build_score_rank(close, lb)
        for exit_name, use_ts in (("momq", False), ("momq_ts20", True)):
            arm = f"us_lb{lb}_{exit_name}"
            print(f"  simulating {arm}")
            calls, counts, skipped = simulate(close, trade, cross, rank,
                                              use_ts20=use_ts)
            calls.to_csv(out_dir / f"calls_{arm}.csv", index=False)
            pv, cnt = slot_curve(calls, close)
            arms[arm] = {"universe": "us", "lookback": lb, "exit": exit_name,
                         **group_stats(calls), **curve_metrics(pv),
                         "mean_active": round(float(counts.mean()), 1),
                         "pct_days_full": round(float((counts >= CAP).mean()) * 100, 1),
                         "skipped": int(skipped),
                         "_pv": pv, "_calls": calls}

    summary = pd.DataFrame({k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                            for k, v in arms.items()}).T
    summary.index.name = "arm"
    summary.to_csv(out_dir / "summary.csv")
    print("\n=== H4e US grid (cap 50) ===")
    print(summary.to_string())

    winner = max(arms, key=lambda a: (arms[a]["sharpe"] or -9,
                                      arms[a]["calmar"] or -9))
    print(f"\n[US winner by 50-slot Sharpe] {winner}")
    w = arms[winner]
    calls, pv = w["_calls"], w["_pv"]
    closed = calls[calls.status == "closed"]

    spy = pd.read_csv(ROOT / "data/benchmarks/spy.csv",
                      parse_dates=["date"]).set_index("date")["close"].ffill()
    spy = spy.loc[(spy.index >= START) & (spy.index <= END)]
    spy = spy / spy.iloc[0]

    india = json.loads(INDIA_RUN.read_text())

    # overlay: weekly, both markets indexed to 1 at common start
    us_wk, spy_wk = weekly(pv), weekly(spy)
    in_dates = pd.to_datetime(india["equity"]["dates"])
    in_pv = pd.Series(india["equity"]["pv"], index=in_dates)
    in_bn = pd.Series(india["equity"]["bench"], index=in_dates)
    grid = sorted(set(us_wk.index) | set(in_pv.index))
    overlay = pd.DataFrame(index=pd.DatetimeIndex(grid))
    overlay["india"] = in_pv.reindex(overlay.index).ffill()
    overlay["nifty"] = in_bn.reindex(overlay.index).ffill()
    overlay["us"] = us_wk.reindex(overlay.index).ffill()
    overlay["spy"] = spy_wk.reindex(overlay.index).ffill()
    overlay = overlay.dropna()

    # monthly correlation between the two winner portfolios
    mo = overlay[["india", "us"]].resample("ME").last().pct_change().dropna()
    rho = float(mo["india"].corr(mo["us"]))
    print(f"[corr] monthly winner-vs-winner correlation: {rho:.2f}")

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
                   "mean_all": round(float(g.pnl_pct.mean()) * 100, 2),
                   "port_ret": round(float(yret), 1)})

    hb = []
    for lo_b, hi_b, lab in [(0, 21, "<1m"), (21, 63, "1-3m"), (63, 126, "3-6m"),
                            (126, 252, "6-12m"), (252, 9999, ">12m")]:
        g = closed[(closed.hold_td >= lo_b) & (closed.hold_td < hi_b)]
        if len(g):
            hb.append({"bucket": lab, "n": int(len(g)),
                       "win": round(float((g.pnl_pct > 0).mean()) * 100, 1),
                       "mean": round(float(g.pnl_pct.mean()) * 100, 2)})

    years_span = (pv.index[-1] - pv.index[0]).days / 365.25
    report = {
        "winner": winner, "monthly_corr": round(rho, 2),
        "us_grid": {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")}
                    for k, v in arms.items()},
        "headline": {**group_stats(calls), **curve_metrics(pv),
                     "calls_per_year": round(len(closed) / years_span, 1),
                     "mean_active": w["mean_active"],
                     "total_mult": round(float(pv.iloc[-1]), 1),
                     "spy_mult": round(float(spy.iloc[-1]), 1),
                     "spy_cagr": round((float(spy.iloc[-1]) ** (1 / years_span) - 1) * 100, 1)},
        "overlay": {"dates": [str(d.date()) for d in overlay.index],
                    "india": [round(float(v), 4) for v in overlay["india"]],
                    "us": [round(float(v), 4) for v in overlay["us"]],
                    "nifty": [round(float(v), 4) for v in overlay["nifty"]],
                    "spy": [round(float(v), 4) for v in overlay["spy"]]},
        "monthly": mm, "yearly": yt, "hold_buckets": hb,
        "top_winners": [{"symbol": r.symbol,
                         "entry": str(pd.Timestamp(r.entry_date).date()),
                         "exit": str(pd.Timestamp(r.exit_date).date()),
                         "pnl": round(r.pnl_pct * 100, 1),
                         "hold_td": int(r.hold_td)}
                        for r in closed.nlargest(8, "pnl_pct").itertuples()],
    }
    (out_dir / "report_us.json").write_text(json.dumps(report))
    print(f"[wrote] {out_dir.relative_to(ROOT)}/report_us.json")


if __name__ == "__main__":
    main()
