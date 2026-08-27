"""Hourly dip swing — the dip_vs_breakout_calls dip feed at swing timescale.

Same momentum sleeve (126d vol-scaled rank from the DAILY panel, top
quartile, 1-day lag), entry timer moved to 60-minute bars, swing exits
(tight trail / time stop) instead of the slow momentum-decay exit alone.

Hourly files in nse500_data_hourly/ are RAW (apply_corporate_actions.py
heals only the daily dir), so step 1 aligns every day's hourly OHLC to
the healed daily close via a per-day factor — that catches demergers
(VEDL, TRIVENI in-window) and any Kite-adjusted splits in one pass.

Window: 2025-10-15 -> 2026-08-21 (all the hourly history there is,
~215 sessions). A daily dip25_ts20 benchmark arm runs on the SAME
window so the comparison is like-for-like, not vs 16-year numbers.

Run:  .venv/bin/python tasks/hourly_dip_swing/experiment.py
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

from tasks.donchian_channel.channel_panels import load_ohlc_panels  # noqa: E402
from tasks.donchian_channel.h4c_combo_grid import build_score_rank  # noqa: E402
from tasks.dip_vs_breakout_calls.experiment import (  # noqa: E402
    simulate as simulate_daily, slot_curve as slot_curve_daily,
    group_stats, cadence,
)

OUT_DIR = Path(__file__).resolve().parent
HOURLY_DIR = ROOT / "nse500_data_hourly"
SLIPPAGE = 0.002
QUARTILE = 0.75
EXIT_RANK = 0.35
BARS_PER_DAY = 7
START = pd.Timestamp("2025-10-15")
END = pd.Timestamp("2026-08-21 23:59:59")
HEAL_TOL = 0.03


def load_hourly_panels(symbols):
    frames = {}
    for sym in symbols:
        p = HOURLY_DIR / f"{sym}_60minute.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, parse_dates=["date"])
        df = df.sort_values("date").drop_duplicates("date").set_index("date")
        frames[sym] = df[["open", "high", "low", "close"]]
    syms = sorted(frames)
    idx = pd.DatetimeIndex(sorted(set().union(*[f.index for f in frames.values()])))
    panels = {c: pd.DataFrame({s: frames[s][c] for s in syms}, index=idx)
              for c in ["open", "high", "low", "close"]}
    return panels


def heal_hourly(panels, daily_close):
    """Align each day's hourly OHLC to the healed daily close.

    factor = daily_close / last-hourly-close-of-day; applied to the whole
    day where it deviates > HEAL_TOL (official NSE close is a 30-min VWAP,
    so sub-1% mismatch vs the 15:15 bar is normal and left alone).
    """
    hclose = panels["close"]
    dates = pd.DatetimeIndex(hclose.index.date)
    day_last = hclose.groupby(dates).last()
    dclose = daily_close.reindex(index=day_last.index, columns=day_last.columns)
    factor = (dclose / day_last).where(lambda f: (f - 1.0).abs() > HEAL_TOL, 1.0)
    factor = factor.fillna(1.0)
    heal_log = factor.where(factor != 1.0).stack()
    fac_bars = factor.reindex(dates).to_numpy()
    for c in panels:
        panels[c] = panels[c] * fac_bars
    return panels, heal_log


def hourly_rank_matrix(daily_rank, hourly_index, columns):
    lagged = daily_rank.shift(1)
    dates = pd.DatetimeIndex(hourly_index.date)
    return lagged.reindex(index=dates, columns=columns).to_numpy()


def simulate_hourly(close, trade, sig, rank_v, *, cap, trail, time_bars=None):
    cal = close.index
    cl_v, tr_v, sig_v = close.to_numpy(), trade.to_numpy(), sig.to_numpy()
    cols = close.columns
    end_i = len(cal) - 1
    active, calls, n_skipped = {}, [], 0
    counts = np.zeros(end_i + 1)

    for i in range(end_i + 1):
        for j, pos in active.items():
            c = cl_v[i, j]
            if not np.isnan(c) and c > pos["peak"]:
                pos["peak"] = c
        exits = []
        for j, pos in active.items():
            c = cl_v[i, j]
            if np.isnan(c):
                continue
            r = rank_v[i, j]
            hit, reason = False, None
            if not np.isnan(r) and r < EXIT_RANK:
                hit, reason = True, "momq"
            if not hit and c < pos["peak"] * (1 - trail):
                hit, reason = True, "trail"
            if not hit and time_bars is not None and i - pos["entry_i"] >= time_bars:
                hit, reason = True, "time"
            if hit:
                exits.append((j, reason))
        for j, reason in exits:
            if i + 1 > end_i:
                continue
            px = tr_v[i + 1, j]
            if np.isnan(px) or px <= 0:
                continue
            pos = active.pop(j)
            calls.append({"symbol": cols[j], "signal_ts": pos["signal_ts"],
                          "entry_ts": pos["entry_ts"], "exit_ts": cal[i + 1],
                          "reason": reason,
                          "pnl_pct": px * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                          "hold_bars": i + 1 - pos["entry_i"], "status": "closed"})
        cand_j = np.where(sig_v[i])[0]
        cands = [(j, rank_v[i, j]) for j in cand_j
                 if j not in active and not np.isnan(rank_v[i, j])
                 and rank_v[i, j] >= QUARTILE]
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
            active[j] = {"signal_ts": cal[i], "entry_ts": cal[i + 1],
                         "entry_i": i + 1, "entry_px": px * (1 + SLIPPAGE),
                         "peak": cl_v[i, j]}
        counts[i] = len(active)

    for j, pos in active.items():
        c = cl_v[end_i, j]
        if np.isnan(c):
            continue
        calls.append({"symbol": cols[j], "signal_ts": pos["signal_ts"],
                      "entry_ts": pos["entry_ts"], "exit_ts": cal[end_i],
                      "reason": "open",
                      "pnl_pct": c * (1 - SLIPPAGE) / pos["entry_px"] - 1.0,
                      "hold_bars": end_i - pos["entry_i"], "status": "open"})
    return pd.DataFrame(calls), pd.Series(counts, index=cal), n_skipped


def slot_curve_hourly(calls, close, slots):
    rets = close.pct_change()
    tot = pd.Series(0.0, index=close.index)
    for _, c in calls.iterrows():
        sl = rets.loc[c["entry_ts"]:c["exit_ts"], c["symbol"]].dropna()
        if len(sl) <= 1:
            continue
        tot.loc[sl.index[1:]] += sl.iloc[1:]
    return (1 + tot / slots).cumprod()


def curve_metrics_hourly(pv):
    rets = pv.pct_change().dropna()
    years = (pv.index[-1] - pv.index[0]).days / 365.25
    cagr = pv.iloc[-1] ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252 * BARS_PER_DAY)
    dd = (pv / pv.cummax() - 1).min()
    return {"window_ret_pct": round((pv.iloc[-1] - 1) * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "max_dd_pct": round(dd * 100, 2)}


def hourly_stats(calls, counts, cap, skipped):
    closed = calls[calls.status == "closed"]
    p = closed.pnl_pct
    op = calls[calls.status == "open"]
    years = (END - START).days / 365.25
    e = pd.to_datetime(closed["entry_ts"])
    wk = e.groupby(e.dt.to_period("W")).size()
    wk = wk.reindex(pd.period_range(START, END, freq="W"), fill_value=0)
    return {"calls_per_year": round(len(closed) / years, 1),
            "new_per_week": round(float(wk.mean()), 2),
            "pct_weeks_with_call": round(float((wk > 0).mean()) * 100, 1),
            "n_closed": int(len(closed)), "n_open": int(len(op)),
            "win_rate_pct": round(float((p > 0).mean()) * 100, 1) if len(closed) else None,
            "mean_pnl_pct": round(float(p.mean()) * 100, 2) if len(closed) else None,
            "median_pnl_pct": round(float(p.median()) * 100, 2) if len(closed) else None,
            "p5_pnl_pct": round(float(p.quantile(.05)) * 100, 1) if len(closed) else None,
            "p95_pnl_pct": round(float(p.quantile(.95)) * 100, 1) if len(closed) else None,
            "median_hold_sessions": round(float(closed.hold_bars.median()) / BARS_PER_DAY, 1) if len(closed) else None,
            "open_mean_pnl_pct": round(float(op.pnl_pct.mean()) * 100, 1) if len(op) else None,
            "exit_mix": dict(closed.reason.value_counts()) if len(closed) else {},
            "mean_active": round(float(counts.mean()), 1),
            "pct_bars_full": round(float((counts >= cap).mean()) * 100, 1),
            "skipped": int(skipped)}


def main():
    print("[hds] loading daily panels (merged, healed)")
    panels_d = load_ohlc_panels()
    close_d, trade_d = panels_d["close"], panels_d["trade"]
    rank_d = build_score_rank(close_d, 126)

    hourly_syms = sorted(p.name.replace("_60minute.csv", "")
                         for p in HOURLY_DIR.glob("*_60minute.csv"))
    syms = [s for s in hourly_syms if s in close_d.columns]
    print(f"[hds] {len(hourly_syms)} hourly files, {len(syms)} with daily coverage")

    print("[hds] loading + healing hourly panels")
    panels_h = load_hourly_panels(syms)
    hcols = panels_h["close"].columns
    panels_h, heal_log = heal_hourly(panels_h, close_d[hcols])
    heal_log.rename("factor").to_csv(OUT_DIR / "heal_log.csv")
    n_days = heal_log.groupby(level=1).size() if len(heal_log) else pd.Series(dtype=int)
    print(f"[hds] healed {len(heal_log)} symbol-days across "
          f"{len(n_days)} symbols: {dict(n_days)}")

    hclose = panels_h["close"]
    htrade = (panels_h["open"] + panels_h["high"]
              + panels_h["low"] + panels_h["close"]) / 4.0

    # post-heal verification: large hourly moves that DISAGREE with the
    # daily panel's same-day move are heal failures (Kite switches the
    # intraday feed to post-split prices mid-day, so per-day healing
    # leaves a fake cliff inside the transition day). Real crashes agree
    # with daily and are kept (e.g. TARIL -21% on 2025-11-10).
    dates = pd.DatetimeIndex(hclose.index.date)
    day_first_open = panels_h["open"].groupby(dates).first()
    day_last_close = hclose.groupby(dates).last()
    dmove = close_d[hcols].pct_change(fill_method=None).reindex(day_last_close.index)
    hgap = day_first_open / day_last_close.shift(1) - 1.0
    bar_ret = hclose.pct_change(fill_method=None)
    first_bar = pd.Series(dates != np.roll(dates, 1), index=hclose.index)
    first_bar.iloc[0] = True
    worst_intra = bar_ret.mask(first_bar, np.nan).abs().groupby(dates).max()
    gap_conflict = ((hgap.abs() > 0.25) & ((hgap - dmove).abs() > 0.15)).any()
    intra_conflict = ((worst_intra > 0.25) & (dmove.abs() < 0.15)).any()
    confirmed = set(gap_conflict[gap_conflict].index) | set(
        intra_conflict[intra_conflict].index)
    print(f"[hds] artifact symbols excluded ({len(confirmed)}): {sorted(confirmed)}")
    keep = [s for s in hcols if s not in confirmed]
    hclose, htrade = hclose[keep], htrade[keep]
    hcols = hclose.columns

    rank_v = hourly_rank_matrix(rank_d[hcols], hclose.index, hcols)

    # regime context: equal-weight buy & hold of the kept universe
    ew = (1 + hclose.pct_change(fill_method=None).mean(axis=1)).cumprod()
    print(f"[hds] context: EW universe window return "
          f"{round((ew.iloc[-1] - 1) * 100, 2)}%, "
          f"maxDD {round(((ew / ew.cummax() - 1).min()) * 100, 2)}%")

    arms = [
        # name, dip lookback bars, dip threshold, trail, time stop bars
        ("h_1d3_ts8",      7, 0.03, 0.08, None),
        ("h_1d3_ts8_t70",  7, 0.03, 0.08, 70),
        ("h_1d3_ts12",     7, 0.03, 0.12, None),
        ("h_2d3_ts8",     14, 0.03, 0.08, None),
        ("h_2d5_ts8",     14, 0.05, 0.08, None),
        ("h_2d5_ts8_t70", 14, 0.05, 0.08, 70),
        ("h_2d5_ts12",    14, 0.05, 0.12, None),
        ("h_3d5_ts12",    21, 0.05, 0.12, None),
        # diagnostic: hourly entry + the daily study's wide 20% trail —
        # isolates entry-granularity effect from the swing-exit effect
        ("h_2d5_ts20",    14, 0.05, 0.20, None),
        ("h_3d5_ts20",    21, 0.05, 0.20, None),
    ]
    rows = {}
    for name, lb, thr, trail, tmax in arms:
        print(f"[hds] simulating {name}")
        dip = ((hclose / hclose.shift(lb) - 1.0) < -thr).fillna(False)
        calls, counts, skipped = simulate_hourly(
            hclose, htrade, dip, rank_v, cap=25, trail=trail, time_bars=tmax)
        calls.to_csv(OUT_DIR / f"calls_{name}.csv", index=False)
        pv = slot_curve_hourly(calls, hclose, 25)
        rows[name] = {**hourly_stats(calls, counts, 25, skipped),
                      **curve_metrics_hourly(pv)}

    # ---- benchmark: daily dip25_ts20 on the same window + universe ----
    print("[hds] benchmark: daily dip25_ts20 on the same window")
    close_b, trade_b = close_d[list(hcols)], trade_d[list(hcols)]
    rank_b = build_score_rank(close_b, 126)
    ret5 = close_b / close_b.shift(5) - 1.0
    dip_d = (ret5 < -0.05).fillna(False)
    calls_d, counts_d, skipped_d = simulate_daily(
        close_b, trade_b, dip_d, rank_b, cap=25,
        end=pd.Timestamp("2026-08-21"), use_ts20=True, start=START)
    calls_d.to_csv(OUT_DIR / "calls_daily_dip25_ts20.csv", index=False)
    pv_d = slot_curve_daily(calls_d, close_b, 25, pd.Timestamp("2026-08-21"),
                            start=START)
    rets = pv_d.pct_change().dropna()
    years = (pv_d.index[-1] - pv_d.index[0]).days / 365.25
    cagr = pv_d.iloc[-1] ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv_d / pv_d.cummax() - 1).min()
    bench = {**group_stats(calls_d),
             "window_ret_pct": round((pv_d.iloc[-1] - 1) * 100, 2),
             "cagr_pct": round(cagr * 100, 2),
             "sharpe": round((cagr - 0.05) / vol, 3),
             "max_dd_pct": round(dd * 100, 2),
             "calls_per_year": round(
                 len(calls_d[calls_d.status == "closed"]) / years, 1),
             "mean_active": round(float(counts_d.mean()), 1)}
    rows["daily_dip25_ts20"] = bench

    df = pd.DataFrame(rows).T
    df.index.name = "arm"
    df.to_csv(OUT_DIR / "summary.csv")
    (OUT_DIR / "report.json").write_text(json.dumps(rows, indent=2, default=str))
    pd.set_option("display.width", 300)
    show = ["calls_per_year", "pct_weeks_with_call", "n_closed", "n_open",
            "win_rate_pct", "mean_pnl_pct", "median_pnl_pct", "p5_pnl_pct",
            "p95_pnl_pct", "median_hold_sessions", "window_ret_pct",
            "cagr_pct", "sharpe", "max_dd_pct", "mean_active"]
    print("\n=== hourly dip swing vs daily dip25_ts20, same 10-month window ===")
    print(df[[c for c in show if c in df.columns]].to_string())


if __name__ == "__main__":
    main()
