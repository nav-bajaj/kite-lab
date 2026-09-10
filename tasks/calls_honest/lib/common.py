"""Shared loaders and statistics for the honest re-run of the two call strategies.

Everything reads the master store through the OM25 harness (tasks/om25_rebuild/lib/run.py):
price-return close/trade panels, point-in-time membership, NIFTY 100 benchmark. Nothing under
~/Documents or data/static is touched.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
REPO = TASK.parents[1]
RUNS = TASK / "runs"
OM_LIB = REPO / "tasks/om25_rebuild/lib"
sys.path.insert(0, str(OM_LIB))
_spec = importlib.util.spec_from_file_location("om25_run", OM_LIB / "run.py")
om = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(om)   # by path: several harness files are named run.py
import windows as W  # noqa: E402  (tasks/om25_rebuild/lib/windows.py)
from regime import membership_mask  # noqa: E402

SLIPPAGE = 0.002
RF = 0.05
MIDSMALL = REPO / "tasks/om25_rebuild/runs/midsmall400_synthetic.csv"
WINDOWS = {"IS 2010-15": ("2010-01-01", "2015-12-31"), "OOS 2016-26": ("2016-01-01", "2099-12-31"),
           "2016-19": ("2016-01-01", "2019-12-31"), "2020-22": ("2020-01-01", "2022-12-31"), "2023-26": ("2023-01-01", "2099-12-31"),
           "Wright Oct-20 to Aug-26": ("2020-10-01", "2026-08-31")}
LEGS = [("bull Apr-20 to Oct-21", "2020-04-30", "2021-10-31"), ("bear Oct-21 to Jun-22", "2021-10-31", "2022-06-30"),
        ("bull Jun-22 to Sep-24", "2022-06-30", "2024-09-30"), ("bear Sep-24 to Feb-25", "2024-09-30", "2025-02-28"),
        ("bull Feb-25 to Aug-26", "2025-02-28", "2026-08-31")]
MM_BASE = {"nse500": dict(cagr=21.7, sharpe=0.78, maxdd=-34.0, subs=(0.57, 1.51, 0.37), wright=(21.1, 0.74, -34.0), capture=(1.09, 1.37), legs=(158, -5, 143, -29, 9), trades=175),
           "nifty250": dict(cagr=19.7, sharpe=0.73, maxdd=-38.0, subs=(0.49, 1.12, 0.65), wright=(26.2, 1.03, -30.0), capture=(1.09, 1.11), legs=(106, 1, 124, -25, 38), trades=84)}

_cache: dict = {}


def panels():
    return om.panels()


def universe(name: str):
    """(all-ever symbols present in the panel, membership_fn, candidate_fn, Date x Symbol member mask)."""
    if name not in _cache:
        syms, mfn, cfn = om.resolve_universe(om.MEMBERSHIP[name], om.MEMBERSHIP[name])
        close = panels()["close"]
        cols = [s for s in close.columns if s in syms]
        mask = membership_mask(om.MEMBERSHIP[name], close[cols])
        _cache[name] = (cols, mfn, cfn, mask)
    return _cache[name]


def midsmall_monthly() -> pd.Series:
    ms = pd.read_csv(MIDSMALL, parse_dates=["date"]).set_index("date")["close"]
    return ms.resample("M").last().pct_change().dropna()


def capture(p: pd.Series, b: pd.Series, a=None, z=None):
    """Compound mean monthly return in the index's up / down months, portfolio over index (mm_rebuild §7)."""
    if a:
        p = p[(p.index >= a) & (p.index <= z)]
    i = p.index.intersection(b.index); p, b = p[i], b[i]; up, dn = b > 0, b < 0
    cm = lambda s, m: (1 + s[m]).prod() ** (1 / m.sum()) - 1
    return cm(p, up) / cm(b, up), cm(p, dn) / cm(b, dn), float((p[up] > b[up]).mean()), float((p[dn] > b[dn]).mean())


def legs(m: pd.Series) -> dict:
    return {lab: 100 * ((1 + m[(m.index > a) & (m.index <= z)]).prod() - 1) for lab, a, z in LEGS}


def equity_stats(eq: pd.Series) -> dict:
    end = str(eq.index[-1].date())
    out = {}
    for k, (a, b) in WINDOWS.items():
        out[k] = W.stats(eq, a, min(b, end) if b > end else b, rf=RF)
    m = eq.resample("M").last().pct_change().dropna(); bm = midsmall_monthly()
    out["capture_wright"] = capture(m, bm, "2020-10-31", "2026-08-31")
    out["capture_long"] = capture(m, bm)
    out["legs"] = legs(m)
    out["legs_index"] = legs(bm)
    out["years"] = {int(y): 100 * ((1 + g).prod() - 1) for y, g in m.groupby(m.index.year)}
    return out


def trade_stats(tr: pd.DataFrame, months: float, cal: pd.DatetimeIndex) -> dict:
    """tr: one row per call with entry_date, exit_date, pnl (net of slippage both ways), reason, status."""
    closed = tr[tr["status"] == "closed"].copy()
    p = closed["pnl"]
    win = p > 0
    hd = (pd.to_datetime(closed["exit_date"]) - pd.to_datetime(closed["entry_date"])).dt.days
    pos = pd.Series(np.arange(len(cal)), index=cal)
    td = pos.reindex(pd.to_datetime(closed["exit_date"])).to_numpy() - pos.reindex(pd.to_datetime(closed["entry_date"])).to_numpy()
    stop = closed["reason"].isin(["stop", "ts20"])
    return dict(n_calls=int(len(tr)), n_closed=int(len(closed)), n_open=int((tr["status"] == "open").sum()),
                calls_per_month=len(tr) / months, win_rate=float(win.mean()) if len(p) else np.nan,
                avg_win=float(p[win].mean()) if win.any() else np.nan, avg_loss=float(p[~win].mean()) if (~win).any() else np.nan,
                expectancy=float(p.mean()) if len(p) else np.nan, median_pnl=float(p.median()) if len(p) else np.nan,
                p5=float(p.quantile(.05)) if len(p) else np.nan, p95=float(p.quantile(.95)) if len(p) else np.nan,
                pct_gt_50=float((p > 0.5).mean()) if len(p) else np.nan,
                median_hold_cd=float(hd.median()) if len(hd) else np.nan, mean_hold_cd=float(hd.mean()) if len(hd) else np.nan,
                median_hold_td=float(np.nanmedian(td)) if len(td) else np.nan, mean_hold_td=float(np.nanmean(td)) if len(td) else np.nan,
                pct_stop=float(stop.mean()) if len(closed) else np.nan, pct_rule=float((~stop).mean()) if len(closed) else np.nan,
                open_mean_pnl=float(tr.loc[tr["status"] == "open", "pnl"].mean()) if (tr["status"] == "open").any() else np.nan)


def trade_stats_by_year(tr: pd.DataFrame, cal: pd.DatetimeIndex, years: dict) -> pd.DataFrame:
    rows = []
    e = pd.to_datetime(tr["entry_date"])
    for y, g in tr.groupby(e.dt.year):
        s = trade_stats(g, 12.0, cal)
        rows.append(dict(year=int(y), calls=s["n_calls"], win_rate=s["win_rate"], avg_win=s["avg_win"], avg_loss=s["avg_loss"],
                         expectancy=s["expectancy"], median_hold_cd=s["median_hold_cd"], pct_stop=s["pct_stop"], port_ret=years.get(int(y), np.nan)))
    return pd.DataFrame(rows)


def fmt(st):
    return W.fmt(st)


def save_run(name: str, equity: pd.DataFrame, calls: pd.DataFrame, extra: dict | None = None):
    out = RUNS / name; out.mkdir(parents=True, exist_ok=True)
    equity.to_csv(out / "equity.csv", index=False); calls.to_csv(out / "calls.csv", index=False)
    for k, v in (extra or {}).items():
        v.to_csv(out / f"{k}.csv", index=False)
    return out


def load_equity(name: str) -> pd.Series:
    return W.equity(RUNS / name)
