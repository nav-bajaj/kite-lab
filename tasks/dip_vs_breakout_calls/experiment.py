"""Dip-entry vs breakout-entry call feeds at tight caps.

Two questions left open by tasks/donchian_channel:
  1. The surviving India config (20d breakout, top-quartile momentum,
     exit at momentum rank < 0.35) was never simulated at a tight cap
     (20-25 concurrent). What do the economics look like there?
  2. H4b showed the breakout is an entry timer for the momentum sleeve.
     Does a dip entry (5-day return < -5%, from meanrev_largecap_study)
     into the same momentum sleeve, with the same slow exit, produce
     better prices / steadier flow?

Engine is a faithful port of the h4c/h4f/h4h simulator (same execution:
signal at close, fill next day at OHLC/4 +/- 20bps, momentum-rank slot
priority, one call per symbol). A regression arm reproduces the h4g
cap-50 xr35 no-stop numbers on the original window/universe before the
study arms run.

Study arms exclude 30 symbols with unadjusted corporate-action cliffs
in nse500_data_merged (one-day close moves < -30%; scan in PLAN.md).

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/experiment.py
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
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
SLIPPAGE = 0.002
QUARTILE = 0.75
EXIT_RANK = 0.35
START = pd.Timestamp("2010-06-01")
END_REG = pd.Timestamp("2026-05-08")     # matches h4c/h4g published runs
END = pd.Timestamp("2026-08-19")
TAIL_START = pd.Timestamp("2023-07-01")

# symbols with 1-day close drops < -30% in nse500_data_merged (mix of
# unadjusted corporate actions and real crashes; excluded wholesale from
# study arms -- see PLAN.md for the list and bias discussion)
CLIFF_SYMBOLS = {
    "ZYDUSLIFE", "IGL", "MINDACORP", "BBTC", "SUZLON", "PIIND",
    "MOTHERSON", "NCC", "ADANIENT", "JSL", "BSOFT", "RPOWER", "IDEA",
    "IIFL", "TATACOMM", "TATACHEM", "YESBANK", "SAMMAANCAP", "M&MFIN",
    "COHANCE", "SPLPETRO", "ZEEL", "ABFRL", "ANGELONE", "ECLERX", "IRB",
    "LICI", "ANANDRATHI", "TRENT", "ZFCVINDIA",
    # upside cliffs (one-day gains > +50%, adjustment errors)
    "BRITANNIA", "NMDC", "SUNDARMFIN",
}


def simulate(close, trade, sig, mom_rank, *, cap, end, use_ts20, start=None):
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
            if use_ts20 and not hit and c < pos["peak"] * 0.80:
                hit, reason = True, "ts20"
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


def slot_curve(calls, close, slots, end, start=None):
    cal = close.loc[(close.index >= (start if start is not None else START))
                    & (close.index <= end)].index
    rets = close.pct_change()
    tot = pd.Series(0.0, index=cal)
    for _, c in calls.iterrows():
        sl = rets.loc[c["entry_date"]:c["exit_date"], c["symbol"]].reindex(cal).dropna()
        if len(sl) <= 1:
            continue
        tot.loc[sl.index[1:]] += sl.iloc[1:]
    return (1 + tot / slots).cumprod()


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
    op = calls[calls.status == "open"]
    return {"n_closed": int(len(closed)), "n_open": int(len(op)),
            "win_rate_pct": round(float((p > 0).mean()) * 100, 1),
            "mean_pnl_pct": round(float(p.mean()) * 100, 2),
            "median_pnl_pct": round(float(p.median()) * 100, 2),
            "p5_pnl_pct": round(float(p.quantile(.05)) * 100, 1),
            "p95_pnl_pct": round(float(p.quantile(.95)) * 100, 1),
            "median_hold_td": int(closed.hold_td.median()),
            "open_mean_pnl_pct": round(float(op.pnl_pct.mean()) * 100, 1) if len(op) else None,
            "pct_ts20_exits": round(float((closed.reason == "ts20").mean()) * 100, 1)}


def cadence(calls, end):
    closed = calls[calls.status == "closed"]
    years = (end - START).days / 365.25
    e = pd.to_datetime(calls["entry_date"])
    wk = e.groupby(e.dt.to_period("W")).size()
    wk = wk.reindex(pd.period_range(START, end, freq="W"), fill_value=0)
    return {"calls_per_year": round((len(closed)) / years, 1),
            "new_per_week": round(float(wk.mean()), 2),
            "pct_weeks_with_call": round(float((wk > 0).mean()) * 100, 1)}


def yearly(calls, pv):
    rows = []
    for y, g in calls.groupby(pd.to_datetime(calls.signal_date).dt.year):
        gc = g[g.status == "closed"]
        pvy = pv[pv.index.year == y]
        prior = pv[pv.index.year < y]
        yret = (pvy.iloc[-1] / (prior.iloc[-1] if len(prior) else 1.0) - 1) * 100
        rows.append({"year": int(y), "n": int(len(g)),
                     "win": round(float((gc.pnl_pct > 0).mean()) * 100, 1) if len(gc) else None,
                     "mean_all": round(float(g.pnl_pct.mean()) * 100, 2),
                     "port_ret": round(float(yret), 1)})
    return rows


def main():
    print("[exp] loading panels")
    full_syms = load_universe_symbols()
    panels = load_ohlc_panels(symbols=full_syms)
    close_f, trade_f, high_f = panels["close"], panels["trade"], panels["high"]
    rank_f = build_score_rank(close_f, 126)
    cross_f = breakout_cross(close_f, donchian_upper(high_f, 20)).fillna(False)

    # ---- regression arm: full universe, original window ----
    print("[exp] regression arm (cap 50, xr35, no stop, END 2026-05-08)")
    calls, counts, _ = simulate(close_f, trade_f, cross_f, rank_f,
                                cap=50, end=END_REG, use_ts20=False)
    pv = slot_curve(calls, close_f, 50, END_REG)
    reg = {**group_stats(calls), **curve_metrics(pv)}
    print(f"  n_closed={reg['n_closed']} (h4g: 1377)  "
          f"cagr={reg['cagr_pct']} (32.64)  sharpe={reg['sharpe']} (1.496)")

    # ---- study arms: cliff symbols excluded, full window ----
    keep = [c for c in close_f.columns if c not in CLIFF_SYMBOLS]
    close, trade, high = close_f[keep], trade_f[keep], high_f[keep]
    rank = build_score_rank(close, 126)
    cross = breakout_cross(close, donchian_upper(high, 20)).fillna(False)
    ret5 = close / close.shift(5) - 1.0
    dip = (ret5 < -0.05).fillna(False)
    s200 = close.rolling(200).mean()
    dip_trend = (dip & (close > s200)).fillna(False)

    arms = [
        ("bo25",        cross,     25, False),
        ("bo25_ts20",   cross,     25, True),
        ("dip25",       dip,       25, False),
        ("dip25_ts20",  dip,       25, True),
        ("dip25_trend", dip_trend, 25, False),
        ("bo50",        cross,     50, False),
        ("dip50_ts20",  dip,       50, True),
    ]
    rows, yearlies = {}, {}
    for name, sig, cap, ts in arms:
        print(f"[exp] simulating {name}")
        calls, counts, skipped = simulate(close, trade, sig, rank,
                                          cap=cap, end=END, use_ts20=ts)
        calls.to_csv(OUT_DIR / f"calls_{name}.csv", index=False)
        pv = slot_curve(calls, close, cap, END)
        tail = pv.loc[pv.index >= TAIL_START]
        tail = tail / tail.iloc[0]
        rows[name] = {**cadence(calls, END), **group_stats(calls),
                      **curve_metrics(pv),
                      **{f"tail_{k}": v for k, v in curve_metrics(tail).items()},
                      "mean_active": round(float(counts.mean()), 1),
                      "pct_days_full": round(float((counts >= cap).mean()) * 100, 1),
                      "skipped": skipped}
        yearlies[name] = yearly(calls, pv)

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.to_csv(OUT_DIR / "summary.csv")
    (OUT_DIR / "report.json").write_text(json.dumps(
        {"regression": reg, "arms": rows, "yearly": yearlies}, indent=2))
    pd.set_option("display.width", 300)
    show = ["calls_per_year", "pct_weeks_with_call", "n_closed", "n_open",
            "win_rate_pct", "mean_pnl_pct", "median_pnl_pct", "p5_pnl_pct",
            "p95_pnl_pct", "median_hold_td", "cagr_pct", "sharpe",
            "max_dd_pct", "tail_cagr_pct", "tail_sharpe", "tail_max_dd_pct",
            "mean_active", "pct_days_full"]
    print("\n=== dip vs breakout, tight caps (xr35) ===")
    print(df[show].to_string())


if __name__ == "__main__":
    main()
