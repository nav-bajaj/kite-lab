"""§2 — the three trigger tapes, and the trade behind each call.

T1/T2/T3 are fixed definitions. Nothing here is swept: the comparison is the
result, so tuning any of the three would destroy it.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "tasks/trend_screen_2026/lib")
sys.path.insert(0, "tasks/breakout_calls_2026/lib")
sys.path.insert(0, "tasks/trigger_calls_2026/lib")
from exits import load_panel, simulate  # noqa: E402

DAILY = "tasks/trigger_calls_2026/data/daily.parquet"
LE = ("LEADING", "EXTENDED")
TOPN = 20

REF_CFG = dict(stop_mode="fixed", stop_pct=0.99, trail="ma150",
               partial_r=None, timestop=None, atr_mult=3.0, exec_ohlc4=True)


def load_daily() -> pd.DataFrame:
    d = pd.read_parquet(DAILY)
    return d.sort_values(["symbol", "date"], ignore_index=True)


def triggers(d: pd.DataFrame) -> pd.DataFrame:
    """All three trigger dates in one long frame: symbol, date, kind, rk."""
    d = d.copy()
    d["in_le"] = d["state"].isin(LE)
    d["prev_le"] = d["prev_state"].isin(LE)
    d["top"] = d["in_le"] & (d["rk"] <= TOPN)

    # T1 — the session the state is entered, if it is top-20 that session.
    # One call per episode: an episode that starts outside the top 20 never
    # fires, it does not get a second look.
    t1 = d[d["in_le"] & ~d["prev_le"] & d["top"]]

    # T2 — first session inside the top 20 within a run of top-20 sessions.
    prev_top = d.groupby("symbol")["top"].shift(1).fillna(False)
    t2 = d[d["top"] & ~prev_top]

    # T3 — the control: each name's last eligible session of each month.
    me = (d.groupby(["symbol", d["date"].dt.year, d["date"].dt.month])["date"]
          .transform("max"))
    t3 = d[(d["date"] == me) & d["top"]]

    out = []
    for kind, t in (("T1", t1), ("T2", t2), ("T3", t3)):
        out.append(pd.DataFrame(dict(
            symbol=t["symbol"].to_numpy(), trigger_date=t["date"].to_numpy(),
            kind=kind, rk=t["rk"].to_numpy(),
            state_at_trigger=t["state"].to_numpy(), adv=t["adv"].to_numpy())))
    return pd.concat(out, ignore_index=True)


def trade_all(trig: pd.DataFrame, cfg: dict = REF_CFG) -> pd.DataFrame:
    """One trade per distinct (symbol, trigger_date). Panels are loaded and
    dropped one name at a time — 1,768 panels do not co-exist in memory."""
    keys = trig[["symbol", "trigger_date"]].drop_duplicates()
    rows = []
    for sym, g in keys.groupby("symbol", sort=False):
        p = load_panel(sym)
        if p is None:
            continue
        n = len(p["c"])
        for td in g["trigger_date"]:
            i = p["pos"].get(pd.Timestamp(td))
            if i is None or i + 1 >= n:
                continue
            e = i + 1
            entry = (p["o"][e] + p["h"][e] + p["l"][e] + p["c"][e]) / 4 * 1.002
            if not np.isfinite(entry) or entry <= 0:
                continue
            out = simulate(p, e, entry, entry * 0.01, cfg)
            if out is None:
                continue
            ret, r, hold, reason = out
            rows.append(dict(symbol=sym, trigger_date=pd.Timestamp(td),
                             entry_date=p["dates"][e], entry=entry,
                             exit_date=p["dates"][min(e + hold, n - 1)],
                             exit_px=entry * (1 + ret), ret=ret, hold=hold,
                             reason=reason))
    return pd.DataFrame(rows)


def dedupe(t: pd.DataFrame) -> pd.DataFrame:
    """One position per name at a time. A trigger that fires while the name is
    still held is not a second call."""
    t = t.sort_values(["symbol", "trigger_date"])
    keep, last = [], {}
    for r in t.itertuples():
        if r.symbol in last and r.entry_date < last[r.symbol]:
            continue
        keep.append(r.Index)
        last[r.symbol] = r.exit_date
    return t.loc[keep].sort_values("trigger_date")
