"""Section 1 — daily market-structure state variables, point-in-time.

No strategy returns enter this file. Every variable is a property of the
market's cross-section on day T computed from bars through T only.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

ROOT = "/Users/navdeep/kite-lab"
PANELS = os.path.join(ROOT, "data/master/prices/adjusted_pr")
OUT = os.path.join(ROOT, "tasks/regime_first_2026/data")
SEED = 20260913


def pit_universe() -> pd.DataFrame:
    u = pd.read_parquet(
        os.path.join(ROOT, "tasks/breakout_calls_2026/data/pit_universe.parquet"),
        columns=["date", "symbol", "adv", "eligible"],
    )
    u = u[u.eligible & u.adv.notna()].drop_duplicates(["symbol", "date"])
    u["r"] = u.groupby("date").adv.rank(ascending=False, method="first")
    return u.loc[u.r <= 500, ["date", "symbol"]].reset_index(drop=True)


def close_panel(syms, calendar) -> pd.DataFrame:
    cols = {}
    for i, s in enumerate(syms, 1):
        f = os.path.join(PANELS, f"{s}.csv")
        if not os.path.exists(f):
            continue
        d = pd.read_csv(f, usecols=["date", "close"], parse_dates=["date"])
        d = d.dropna(subset=["close"]).drop_duplicates("date").set_index("date").close
        cols[s] = d.sort_index()
        if i % 250 == 0:
            print(f"  panel {i}/{len(syms)}", flush=True)
    px = pd.DataFrame(cols).reindex(calendar)
    return px


def expanding_z(s: pd.Series, minp: int = 250) -> pd.Series:
    m = s.expanding(min_periods=minp).mean()
    sd = s.expanding(min_periods=minp).std()
    return (s - m) / sd.replace(0.0, np.nan)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    bench = pd.read_csv(os.path.join(ROOT, "data/master/benchmarks/NIFTY_500.csv"),
                        parse_dates=["date"]).drop_duplicates("date").set_index("date").sort_index()
    breadth = pd.read_parquet(os.path.join(ROOT, "tasks/trend_screen_2026/data/breadth.parquet"))
    signals = pd.read_parquet(os.path.join(ROOT, "tasks/regime_allocation_2026/data/signals.parquet"))

    cal = breadth.index  # the breadth calendar is the universe's own trading calendar
    idx = bench.close.reindex(cal).ffill()

    uni = pit_universe()
    uni = uni[uni.date.isin(cal)]
    syms = sorted(uni.symbol.unique())
    print(f"universe names: {len(syms)}", flush=True)
    px = close_panel(syms, cal)
    px = px[[c for c in px.columns if c in set(syms)]]
    print(f"panel: {px.shape}", flush=True)

    # membership mask, aligned to the panel
    mask = pd.DataFrame(False, index=cal, columns=px.columns)
    m = uni[uni.symbol.isin(px.columns)]
    mask.values[
        pd.Index(cal).get_indexer(m.date.values),
        px.columns.get_indexer(m.symbol.values),
    ] = True

    ret1 = px.pct_change()
    ret21 = px.pct_change(21)
    ret63 = px.pct_change(63)
    s200 = px.rolling(200).mean()
    s200_up = (s200 > s200.shift(21))
    s200_up = s200_up.where(s200.notna() & s200.shift(21).notna())

    V = pd.DataFrame(index=cal)

    # --- breadth (level and direction) --------------------------------------
    V["pct_above_200"] = breadth["pct_above_200"]
    V["net_highs"] = breadth["net_highs"]
    V["pct_leading"] = signals["pct_leading"].reindex(cal)
    V["pct_above_200_chg"] = breadth["pct_above_200_chg"]
    V["net_highs_chg"] = breadth["net_highs_chg"]

    # --- breadth drawdown ----------------------------------------------------
    b_hi = V["pct_above_200"].rolling(252, min_periods=252).max()
    V["breadth_dd"] = V["pct_above_200"] / b_hi - 1.0

    # --- divergence ----------------------------------------------------------
    i_hi = idx.rolling(252, min_periods=252).max()
    V["idx_dd"] = idx / i_hi - 1.0
    V["divergence"] = V["idx_dd"] - V["breadth_dd"]

    # --- dispersion: cross-sectional sd of trailing 21-session returns --------
    r21 = ret21.where(mask)
    V["dispersion"] = r21.std(axis=1, ddof=1)
    V["n_universe"] = mask.sum(axis=1)

    # --- volatility ----------------------------------------------------------
    ir = idx.pct_change()
    V["vol21"] = ir.rolling(21, min_periods=21).std() * np.sqrt(252)
    V["vol_ratio"] = V["vol21"] / V["vol21"].rolling(252, min_periods=252).median()

    # --- trend quality: share whose 200-day is above its level 21 ago ---------
    tq = s200_up.where(mask)
    V["trend_quality"] = tq.sum(axis=1) / tq.notna().sum(axis=1).replace(0, np.nan)

    # --- participation skew ---------------------------------------------------
    r63 = ret63.where(mask)
    def _skew(row: pd.Series) -> float:
        v = row.dropna().values
        if len(v) < 50:
            return np.nan
        k = max(1, int(round(len(v) * 0.10)))
        top = np.sort(v)[-k:].sum()
        tot = v.sum()
        if abs(tot) < 1e-9:
            return np.nan
        return float(np.clip(top / tot, -5.0, 5.0))
    V["part_skew"] = r63.apply(_skew, axis=1)

    # --- correlation: rolling-63 mean pairwise corr, 100-name yearly subsample -
    rng = np.random.default_rng(SEED)
    corr = pd.Series(np.nan, index=cal)
    years = sorted({d.year for d in cal})
    sub_by_year = {}
    for y in years:
        days = [d for d in cal if d.year == y]
        if not days:
            continue
        elig = mask.loc[days].all(axis=0)
        pool = [c for c in px.columns if elig.get(c, False)]
        # require a full year of returns available for the window
        pool = [c for c in pool if ret1.loc[days, c].notna().mean() > 0.95]
        if len(pool) < 30:
            pool = [c for c in px.columns if mask.loc[days, c].any() and ret1.loc[days, c].notna().mean() > 0.95]
        if len(pool) == 0:
            continue
        k = min(100, len(pool))
        sub_by_year[y] = list(rng.choice(pool, size=k, replace=False))

    pos = {d: i for i, d in enumerate(cal)}
    for y, sub in sub_by_year.items():
        R = ret1[sub].values
        days = [d for d in cal if d.year == y]
        for d in days:
            i = pos[d]
            if i < 63:
                continue
            W = R[i - 62: i + 1]
            keep = ~np.isnan(W).any(axis=0)
            W = W[:, keep]
            if W.shape[1] < 20:
                continue
            Ws = W - W.mean(axis=0)
            sd = Ws.std(axis=0, ddof=1)
            ok = sd > 0
            Ws, sd = Ws[:, ok], sd[ok]
            if Ws.shape[1] < 20:
                continue
            C = (Ws.T @ Ws) / (Ws.shape[0] - 1) / np.outer(sd, sd)
            n = C.shape[0]
            corr.iloc[i] = (C.sum() - n) / (n * (n - 1))
        print(f"  corr {y} done ({len(sub)} names)", flush=True)
    V["correlation"] = corr

    # --- expanding z-scores ---------------------------------------------------
    zcols = ["pct_above_200", "net_highs", "pct_leading", "breadth_dd", "divergence",
             "dispersion", "correlation", "vol21", "vol_ratio", "trend_quality",
             "part_skew", "idx_dd"]
    for c in zcols:
        V[f"z_{c}"] = expanding_z(V[c])

    V["index_close"] = idx
    V = V.loc[V.index >= "2005-02-17"]
    V.to_parquet(os.path.join(OUT, "state_vars.parquet"))
    print(V.notna().sum())
    print("written", os.path.join(OUT, "state_vars.parquet"), V.shape, flush=True)


if __name__ == "__main__":
    main()
