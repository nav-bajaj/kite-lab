"""Regime-allocation harness — one candidate in, one row out.

Extends `tasks/trend_screen_2026/lib/run_isos.py`. Everything the trend screen
settled (universe, signal, exit, book) is held fixed; only the regime layer
moves.

Conventions that matter and are easy to get wrong:

* `order="tight"` makes `build_book` fully deterministic — the rng is only
  consumed on `order="random"`. Three seeds therefore return three identical
  books, so a single seed is run and the "3 seeds" of §1 is satisfied by
  construction rather than by burning 3x the compute. Verified in §1.
* The exposure-matched control uses the mean weight across ALL tape rows in
  the span, zeros included, so it matches total sizing rather than the
  average size of a taken position.
* The level cut is the signal's own median. For IS/OOS it is the full-span
  median (that is what `trend_screen_2026` §8 used, and reproducing its number
  requires it — it is a mild look-ahead and is labelled as one). For the
  walk-forward it is recomputed on the fit window only.
"""
from __future__ import annotations

import os
import pickle
import sys

import numpy as np
import pandas as pd

REPO = "/Users/navdeep/kite-lab"
sys.path.insert(0, f"{REPO}/tasks/breakout_calls_2026/lib")
sys.path.insert(0, f"{REPO}/tasks/trend_screen_2026/lib")

from book import build_book, era_sharpe  # noqa: E402,F401
from exits import load_panel  # noqa: E402

TREND = f"{REPO}/tasks/trend_screen_2026"
BREAK = f"{REPO}/tasks/breakout_calls_2026"
TASK = f"{REPO}/tasks/regime_allocation_2026"
CACHE = f"{TASK}/data"

PHASES = ["EXPANSION", "RECOVERY", "TOPPING", "CONTRACTION"]
SIGNALS = ["pct_above_200", "pct_leading", "net_highs", "pct_above_50", "composite"]
WINDOWS = [21, 42, 63, 126]
SHAPES = ["D1_four_bucket", "D2_two_bucket", "D3_continuous"]
END = "2026-09-09"


# --------------------------------------------------------------- data loading

def load_tape(which: str = "trend") -> pd.DataFrame:
    if which == "trend":
        tr = pd.read_csv(f"{TREND}/data/calls_full_range.csv",
                         parse_dates=["entry_date", "exit_date"])
        tr["exit_px"] = tr.entry * (1 + tr.ret)
        tr["stop"] = tr.entry * 0.01
        tr["final_depth"] = tr.rnk
        pit = pd.read_parquet(f"{BREAK}/data/pit_universe.parquet",
                              columns=["date", "symbol", "adv"]
                              ).drop_duplicates(["symbol", "date"])
        tr = tr.merge(pit, left_on=["symbol", "entry_date"],
                      right_on=["symbol", "date"], how="left")
        tr["adv"] = tr.adv.fillna(tr.adv.median())
        tr = tr.drop(columns=["date"])
    else:
        tr = pd.read_csv(f"{BREAK}/data/book_trades.csv",
                         parse_dates=["entry_date", "exit_date"])
    return tr.sort_values("entry_date").reset_index(drop=True)


def load_panels(tr: pd.DataFrame, tag: str = "trend") -> dict:
    f = f"{CACHE}/panels_{tag}.pkl"
    if os.path.exists(f):
        with open(f, "rb") as fh:
            # Local cache this module wrote itself, never an external file.
            return pickle.load(fh)  # noqa: S301
    pan = {}
    for s in sorted(tr.symbol.unique()):
        p = load_panel(s)
        if p is not None:
            pan[s] = {"close": pd.Series(p["c"], index=p["dates"])}
    with open(f, "wb") as fh:
        pickle.dump(pan, fh, protocol=4)
    return pan


def sessions() -> pd.DatetimeIndex:
    bench = pd.read_csv(f"{REPO}/data/master/benchmarks/NIFTY_500.csv",
                        parse_dates=["date"])
    return pd.DatetimeIndex(sorted(bench.date.unique()))


def cal(lo: str, hi: str = END) -> pd.DatetimeIndex:
    f = sessions()
    return f[(f >= lo) & (f <= hi)]


# -------------------------------------------------------------- regime signals

def _pct_leading() -> pd.Series:
    f = pd.read_parquet(f"{TREND}/data/features_t500_ranked.parquet",
                        columns=["date", "symbol", "state"])
    s = f.groupby("date").state.apply(lambda x: x.isin(["LEADING", "EXTENDED"]).mean())
    s.index = pd.DatetimeIndex(s.index)
    return s.sort_index()


def raw_signals() -> pd.DataFrame:
    """Daily level for each of A1-A5, on the sessions calendar."""
    f = f"{CACHE}/signals.parquet"
    if os.path.exists(f):
        return pd.read_parquet(f)
    b = pd.read_parquet(f"{TREND}/data/breadth.parquet")
    idx = b.index
    out = pd.DataFrame(index=idx)
    out["pct_above_200"] = b.pct_above_200
    out["net_highs"] = b.net_highs
    out["pct_leading"] = _pct_leading().reindex(idx).ffill()
    p50 = f"{CACHE}/pct_above_50.parquet"
    have50 = os.path.exists(p50)
    out["pct_above_50"] = (pd.read_parquet(p50).pct_above_50.reindex(idx)
                           if have50 else np.nan)
    # A5 composite: mean of the three cross-sectionally comparable levels,
    # each mapped to its own expanding percentile so they share a scale.
    parts = []
    for c in ("pct_above_200", "pct_leading", "net_highs"):
        parts.append(out[c].expanding(min_periods=250).rank(pct=True))
    out["composite"] = pd.concat(parts, axis=1).mean(axis=1)
    if have50:
        out.to_parquet(f)
    return out


def regime_series(signal: str, window: int, shape: str,
                  sig: pd.DataFrame | None = None,
                  level_cut: float | None = None,
                  fit_index: pd.DatetimeIndex | None = None,
                  lo_q: float = 0.20, hi_q: float = 0.80,
                  top_weight: float = 0.5,
                  hysteresis: int = 0) -> pd.Series:
    """date -> allocation weight in [0, 1].

    D1 four buckets: level (vs median) x direction (chg over `window`), weights
        {EXPANSION 1, RECOVERY 1, TOPPING `top_weight`, CONTRACTION 0}.
    D2 two buckets: direction only, rising -> 1, falling -> 0.
    D3 continuous: clip((chg - lo) / (hi - lo), 0, 1), lo/hi as quantiles of
        the chg distribution on `fit_index` (default: the whole span).
    """
    if sig is None:
        sig = raw_signals()
    lvl = sig[signal].astype(float)
    chg = lvl - lvl.shift(window)
    fi = lvl.index if fit_index is None else lvl.index.intersection(fit_index)

    if shape == "D1_four_bucket":
        if level_cut is None:
            level_cut = lvl.loc[fi].median()
        high, rising = lvl >= level_cut, chg > 0
        w = pd.Series(np.nan, index=lvl.index, dtype=float)
        w[high & rising] = 1.0                 # EXPANSION
        w[~high & rising] = 1.0                # RECOVERY
        w[high & ~rising] = top_weight         # TOPPING
        w[~high & ~rising] = 0.0               # CONTRACTION
    elif shape == "D2_two_bucket":
        w = (chg > 0).astype(float)
    elif shape == "D3_continuous":
        c = chg.loc[fi].dropna()
        lo, hi = c.quantile(lo_q), c.quantile(hi_q)
        w = ((chg - lo) / (hi - lo)).clip(0.0, 1.0) if hi > lo else chg * 0 + 1.0
    else:
        raise ValueError(shape)

    w[chg.isna()] = np.nan
    w = w.ffill()
    if hysteresis > 0:
        w = _hysteresis(w, hysteresis)
    return w.dropna()


def _hysteresis(w: pd.Series, n: int) -> pd.Series:
    """A new weight is only adopted after it has persisted `n` sessions."""
    v = w.to_numpy(float)
    out = np.empty_like(v)
    cur = v[0]
    run_val, run_len = v[0], 0
    for i, x in enumerate(v):
        if x == run_val:
            run_len += 1
        else:
            run_val, run_len = x, 1
        if run_len >= n:
            cur = run_val
        out[i] = cur
    return pd.Series(out, index=w.index)


def phase_labels(signal: str, window: int, sig: pd.DataFrame,
                 level_cut: float | None = None) -> pd.Series:
    lvl = sig[signal].astype(float)
    chg = lvl - lvl.shift(window)
    if level_cut is None:
        level_cut = lvl.median()
    high, rising = lvl >= level_cut, chg > 0
    ph = pd.Series(np.nan, index=lvl.index, dtype=object)
    ph[high & rising] = "EXPANSION"
    ph[high & ~rising] = "TOPPING"
    ph[~high & rising] = "RECOVERY"
    ph[~high & ~rising] = "CONTRACTION"
    return ph


# ------------------------------------------------------------------ evaluation

def _stats(r: dict) -> dict:
    return dict(cagr=r["cagr"], maxdd=r["maxdd"], sharpe=r["sharpe"],
                taken=r["taken"], expo=r["exposure"], end=r["end"])


def run_book(tr: pd.DataFrame, pan: dict, calendar: pd.DatetimeIndex,
             wt: pd.Series | float, slots: int = 25, capital: float = 1e7,
             force_exit: pd.Series | None = None, seed: int = 0) -> dict:
    t = tr.copy()
    if isinstance(wt, pd.Series):
        t["wt"] = t.entry_date.map(wt).fillna(1.0)
    else:
        t["wt"] = float(wt)
    kw = {}
    if force_exit is not None:
        kw["force_exit"] = force_exit
    return build_book(t, pan, calendar, slots=slots, risk_pct=1.0,
                      capital=capital, seed=seed, order="tight", **kw)


def changes_per_year(w: pd.Series, calendar: pd.DatetimeIndex) -> float:
    s = w.reindex(calendar).ffill().dropna()
    if len(s) < 2:
        return np.nan
    n = int((s.diff().fillna(0) != 0).sum())
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    return n / yrs if yrs > 0 else np.nan


def time_in_cash(w: pd.Series, calendar: pd.DatetimeIndex) -> float:
    s = w.reindex(calendar).ffill().dropna()
    return float((s <= 0).mean())


def evaluate(w: pd.Series, tr: pd.DataFrame, pan: dict,
             calendar: pd.DatetimeIndex, slots: int = 25,
             control_cache: dict | None = None) -> dict:
    """One candidate: the rule and its own exposure-matched control."""
    sub = tr[(tr.entry_date >= calendar[0]) & (tr.entry_date <= calendar[-1])]
    wts = sub.entry_date.map(w).fillna(1.0)
    mean_w = float(wts.mean())
    r = _stats(run_book(sub, pan, calendar, w, slots=slots))
    key = (round(mean_w, 3), slots, calendar[0], calendar[-1])
    if control_cache is not None and key in control_cache:
        c = control_cache[key]
    else:
        c = _stats(run_book(sub, pan, calendar, mean_w, slots=slots))
        if control_cache is not None:
            control_cache[key] = c
    return dict(mean_w=mean_w,
                cagr=r["cagr"], maxdd=r["maxdd"], sharpe=r["sharpe"],
                taken=r["taken"], expo=r["expo"],
                c_cagr=c["cagr"], c_maxdd=c["maxdd"], c_sharpe=c["sharpe"],
                c_expo=c["expo"],
                edge=r["sharpe"] - c["sharpe"],
                chg_yr=changes_per_year(w, calendar),
                cash=time_in_cash(w, calendar))


# --------------------------------------------------------------- walk-forward

def _chain(segments: list[pd.Series]) -> pd.Series:
    """Glue yearly equity segments so each starts where the last one ended."""
    out, mult = [], 1.0
    for s in segments:
        seg = s / s.iloc[0] * mult
        out.append(seg)
        mult = float(seg.iloc[-1])
    eq = pd.concat(out)
    return eq[~eq.index.duplicated(keep="last")]


def chained_stats(eq: pd.Series) -> dict:
    dd = 1 - eq / eq.cummax()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    rets = eq.pct_change().dropna()
    vol = rets.std() * np.sqrt(252)
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
    return dict(cagr=cagr, maxdd=float(dd.max()),
                sharpe=(cagr - 0.05) / vol if vol > 0 else np.nan)


def walk_forward(grid_fn, cells, tr, pan, sig, slots=25,
                 y0=2014, y1=2026, fit_years=8, mode="rule"):
    """`grid_fn(cell, fit_index) -> pd.Series` gives the weight series.

    For year Y the fit window is [Y-8, Y-1] entry dates; the cell with the best
    fit-window Sharpe is applied to year Y. `mode` is "rule" (weights from the
    chosen cell), "always" (wt = 1) or "control" (wt = the chosen cell's mean
    weight over the fit window, i.e. the exposure-matched walk).
    """
    segs, picks = [], []
    for Y in range(y0, y1 + 1):
        fit_cal = cal(f"{Y - fit_years}-01-01", f"{Y - 1}-12-31")
        app_cal = cal(f"{Y}-01-01", f"{min(Y, 2026)}-12-31")
        if len(app_cal) < 5:
            continue
        fit_tr = tr[(tr.entry_date >= fit_cal[0]) & (tr.entry_date <= fit_cal[-1])]
        best, best_s, best_w = None, -9e9, None
        if mode == "always":
            best, best_w = "always_on", 1.0
        else:
            for cell in cells:
                w = grid_fn(cell, fit_cal)
                r = run_book(fit_tr, pan, fit_cal, w, slots=slots)
                if np.isfinite(r["sharpe"]) and r["sharpe"] > best_s:
                    best, best_s, best_w = cell, r["sharpe"], w
        app_tr = tr[(tr.entry_date >= app_cal[0]) & (tr.entry_date <= app_cal[-1])]
        if mode == "control":
            mw = float(fit_tr.entry_date.map(best_w).fillna(1.0).mean())
            use = mw
        elif mode == "always":
            use = 1.0
        else:
            use = best_w
        r = run_book(app_tr, pan, app_cal, use, slots=slots)
        segs.append(r["equity"])
        picks.append(dict(year=Y, cell=str(best), fit_sharpe=best_s,
                          year_ret=float(r["equity"].iloc[-1] / r["equity"].iloc[0] - 1),
                          taken=r["taken"], expo=r["exposure"],
                          mean_w=(float(np.mean(use)) if not isinstance(use, pd.Series)
                                  else float(app_tr.entry_date.map(use).fillna(1.0).mean()))))
    eq = _chain(segs)
    st = chained_stats(eq)
    return dict(equity=eq, picks=pd.DataFrame(picks), **st)


# ------------------------------------------------------------------ deflation

def gumbel_expected_max(n: int, sd: float) -> float:
    """E[max] of n iid standard-normal draws scaled by `sd`, Gumbel form."""
    if n < 2:
        return 0.0
    g = 0.5772156649
    q = np.sqrt(2 * np.log(n))
    e = q - (np.log(np.log(n)) + np.log(4 * np.pi)) / (2 * q) + g / q
    return float(e * sd)


PARAM_COUNT = {"D1_four_bucket": 4, "D2_two_bucket": 2, "D3_continuous": 4}
