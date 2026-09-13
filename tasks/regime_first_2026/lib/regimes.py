"""Sections 2-4 — candidate taxonomies, the R1-R3 gates, real-time identifiability.

Nothing here reads a strategy's returns. Every measurement is a property of the
state series itself or of the index's own turning points.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture

ROOT = "/Users/navdeep/kite-lab"
DATA = os.path.join(ROOT, "tasks/regime_first_2026/data")
SEED = 20260913
FIT_END = "2015-12-31"
START = "2006-01-01"

ALL_VARS = ["z_pct_above_200", "z_net_highs", "z_pct_leading", "z_breadth_dd",
            "z_divergence", "z_dispersion", "z_correlation", "z_vol21",
            "z_vol_ratio", "z_trend_quality", "z_part_skew"]
BREADTH_VARS = ["z_pct_above_200", "z_net_highs", "z_pct_leading",
                "z_breadth_dd", "z_divergence"]


# --------------------------------------------------------------------------
# reference turning points — 15% zigzag on the NIFTY 500 close, re-derived
# --------------------------------------------------------------------------
def zigzag(close: pd.Series, pct: float = 0.15) -> pd.DataFrame:
    c = close.dropna()
    v, dates = c.values, c.index
    piv = []
    d = 0
    hi = lo = v[0]
    hi_i = lo_i = 0
    for i in range(1, len(v)):
        x = v[i]
        if d >= 0 and x > hi:
            hi, hi_i = x, i
        if d <= 0 and x < lo:
            lo, lo_i = x, i
        if d != -1 and x <= hi * (1 - pct):
            piv.append((dates[hi_i], "peak"))
            d, lo, lo_i = -1, x, i
        elif d != 1 and x >= lo * (1 + pct):
            piv.append((dates[lo_i], "trough"))
            d, hi, hi_i = 1, x, i
    out = pd.DataFrame(piv, columns=["date", "kind"])
    # The first pivot is anchored on the arbitrary first bar of the slice: no
    # completed 15% swing precedes it, so it is not a reference turning point.
    return out.iloc[1:].reset_index(drop=True)


# --------------------------------------------------------------------------
# rule candidates
# --------------------------------------------------------------------------
def hysteresis(s: pd.Series, enter: float, exit_: float) -> pd.Series:
    out = pd.Series(np.nan, index=s.index, dtype=object)
    st = None
    for i, x in enumerate(s.values):
        if np.isnan(x):
            continue
        if st is None:
            if x > enter:
                st = "RISK_ON"
            elif x < exit_:
                st = "RISK_OFF"
            else:
                continue
        elif st == "RISK_ON" and x < exit_:
            st = "RISK_OFF"
        elif st == "RISK_OFF" and x > enter:
            st = "RISK_ON"
        out.iloc[i] = st
    return out


def c3_asymmetric(V: pd.DataFrame) -> pd.Series:
    """Exit on divergence at a high; re-enter on C1's enter rule."""
    pa, idd, bdd = V.pct_above_200.values, V.idx_dd.values, V.breadth_dd.values
    out = pd.Series(np.nan, index=V.index, dtype=object)
    st = None
    for i in range(len(V)):
        if np.isnan(pa[i]):
            continue
        if st is None:
            if pa[i] > 0.60:
                st = "RISK_ON"
            elif pa[i] < 0.40:
                st = "RISK_OFF"
            else:
                continue
        elif st == "RISK_ON":
            if (not np.isnan(idd[i])) and (not np.isnan(bdd[i])) \
                    and idd[i] >= -0.01 and bdd[i] < -0.20:
                st = "RISK_OFF"
            elif pa[i] < 0.40:
                st = "RISK_OFF"
        elif st == "RISK_OFF" and pa[i] > 0.60:
            st = "RISK_ON"
        out.iloc[i] = st
    return out


# --------------------------------------------------------------------------
# fitted candidates
# --------------------------------------------------------------------------
def majority_vote(lab: pd.Series, win: int = 21) -> pd.Series:
    """Trailing (causal) 21-session majority vote. Centred voting would peek."""
    vals = lab.values
    out = np.array(vals, dtype=object)
    for i in range(len(vals)):
        lo = max(0, i - win + 1)
        w = [x for x in vals[lo:i + 1] if x is not None and not (isinstance(x, float) and np.isnan(x))]
        if not w:
            out[i] = np.nan
            continue
        u, ct = np.unique(np.array(w, dtype=object).astype(str), return_counts=True)
        out[i] = u[np.argmax(ct)]
    return pd.Series(out, index=lab.index)


def fit_model(kind: str, X: np.ndarray, k: int):
    if kind == "kmeans":
        return KMeans(n_clusters=k, n_init=20, random_state=SEED).fit(X)
    return GaussianMixture(n_components=k, covariance_type="full", n_init=10,
                           random_state=SEED, reg_covar=1e-4).fit(X)


def centroids(model, X, lab, k):
    if hasattr(model, "cluster_centers_"):
        return model.cluster_centers_
    return model.means_


def fitted_labels(V: pd.DataFrame, cols, kind: str, k: int,
                  fit_slice=(START, FIT_END), smooth: int = 21) -> pd.Series:
    F = V[cols].dropna()
    F = F[F.index >= START]
    tr = F.loc[fit_slice[0]:fit_slice[1]]
    m = fit_model(kind, tr.values, k)
    raw = pd.Series([f"S{int(x)}" for x in m.predict(F.values)], index=F.index)
    lab = majority_vote(raw, smooth) if smooth else raw
    return lab.reindex(V.index)


# --------------------------------------------------------------------------
# run statistics and gates
# --------------------------------------------------------------------------
def runs(lab: pd.Series) -> pd.DataFrame:
    s = lab.dropna()
    if s.empty:
        return pd.DataFrame(columns=["state", "start", "end", "n"])
    grp = (s != s.shift()).cumsum()
    r = s.groupby(grp).agg(state="first", n="size")
    r["start"] = s.groupby(grp).apply(lambda x: x.index[0])
    r["end"] = s.groupby(grp).apply(lambda x: x.index[-1])
    return r.reset_index(drop=True)


def persistence(lab: pd.Series) -> dict:
    r = runs(lab)
    s = lab.dropna()
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return {
        "n_states": s.nunique(),
        "n_runs": len(r),
        "median_run": float(r.n.median()),
        "share_le5": float((r.n <= 5).mean()),
        "flips_yr": (len(r) - 1) / yrs,
        "time_in_state": (s.value_counts(normalize=True).round(3).to_dict()),
        "first": s.index[0], "last": s.index[-1],
    }


def risk_map(lab: pd.Series, V: pd.DataFrame) -> dict:
    """Classify each state risk-on / risk-off by its own breadth level, using
    the 2006-2015 fit window only. A market-structure property, not a return."""
    w = lab.loc[START:FIT_END].dropna()
    pa = V.pct_above_200.reindex(w.index)
    cut = pa.median()
    means = pa.groupby(w).mean()
    return {st: ("RISK_ON" if m >= cut else "RISK_OFF") for st, m in means.items()}


def detection_lag(lab: pd.Series, tps: pd.DataFrame, rmap: dict) -> dict:
    s = lab.dropna()
    idx = s.index
    post = s.map(rmap)
    tp = tps[(tps.date >= idx[0]) & (tps.date <= idx[-1])].reset_index(drop=True)
    res = {"peak": [], "trough": []}
    cens = {"peak": 0, "trough": 0}
    for j, row in tp.iterrows():
        want = "RISK_OFF" if row.kind == "peak" else "RISK_ON"
        t = idx.searchsorted(row.date)
        if t >= len(idx):
            continue
        nxt = len(idx)
        for j2 in range(j + 1, len(tp)):
            if tp.kind.iloc[j2] != row.kind:
                nxt = idx.searchsorted(tp.date.iloc[j2])
                break
        v = post.values
        if v[t] == want:
            i = t
            while i > 0 and v[i - 1] == want:
                i -= 1
            res[row.kind].append(-(t - i))
        else:
            i = t
            while i < nxt and v[i] != want:
                i += 1
            if i >= nxt:
                cens[row.kind] += 1
            else:
                res[row.kind].append(i - t)
    return {
        "peaks": res["peak"], "troughs": res["trough"],
        "lag_peaks": float(np.median(res["peak"])) if res["peak"] else np.nan,
        "lag_troughs": float(np.median(res["trough"])) if res["trough"] else np.nan,
        "cens_peaks": cens["peak"], "cens_troughs": cens["trough"],
        "n_peaks": len(tp[tp.kind == "peak"]), "n_troughs": len(tp[tp.kind == "trough"]),
    }


# --------------------------------------------------------------------------
# real-time identifiability (§4)
# --------------------------------------------------------------------------
def align(ref_cent: np.ndarray, cent: np.ndarray) -> dict:
    d = ((ref_cent[:, None, :] - cent[None, :, :]) ** 2).sum(-1)
    r, c = linear_sum_assignment(d)
    return {int(cc): int(rr) for rr, cc in zip(r, c)}


def realtime_labels(V: pd.DataFrame, cols, kind: str, k: int, smooth: int = 21):
    """Expanding refit: at each year end fit on everything to date, decode the
    next year. Reference (retrospective) fit uses the whole span."""
    F = V[cols].dropna()
    F = F[F.index >= START]
    ref_m = fit_model(kind, F.values, k)
    ref_raw = pd.Series(ref_m.predict(F.values), index=F.index)
    ref_c = centroids(ref_m, F.values, ref_raw, k)

    rt = pd.Series(np.nan, index=F.index)
    years = sorted({d.year for d in F.index})
    for y in years:
        if y <= 2010:
            continue  # need a minimum history before the first decode
        tr = F[F.index < f"{y}-01-01"]
        if len(tr) < 750:
            continue
        m = fit_model(kind, tr.values, k)
        cur = F[(F.index >= f"{y}-01-01") & (F.index < f"{y + 1}-01-01")]
        if cur.empty:
            continue
        mp = align(ref_c, centroids(m, tr.values, None, k))
        rt.loc[cur.index] = [mp[int(x)] for x in m.predict(cur.values)]
    ref_lab = ref_raw.map(lambda x: f"S{int(x)}")
    rt_lab = rt.dropna().map(lambda x: f"S{int(x)}")
    if smooth:
        ref_lab = majority_vote(ref_lab, smooth)
        rt_lab = majority_vote(rt_lab, smooth)
    return ref_lab.reindex(V.index), rt_lab.reindex(V.index)


def agreement(ref: pd.Series, rt: pd.Series) -> dict:
    both = pd.concat([ref, rt], axis=1).dropna()
    both.columns = ["ref", "rt"]
    if both.empty:
        return {"agree": np.nan, "n": 0, "catchup": np.nan}
    ag = float((both.ref == both.rt).mean())
    r = runs(both.ref)
    lags = []
    for _, row in r.iterrows():
        seg = both.loc[row.start:row.end]
        hit = np.where((seg.rt == row.state).values)[0]
        lags.append(int(hit[0]) if len(hit) else int(len(seg)))
    return {"agree": ag, "n": len(both), "catchup": float(np.median(lags)) if lags else np.nan}
