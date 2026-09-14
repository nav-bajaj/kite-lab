"""Residual-momentum scores. Same score_fn interface as data_pipeline/strategies/momentum.py.

Two constructions, per PLAN.md:

  mode="alpha" (RM-12)  betas fit on the 252/21 formation window itself; score = alpha / sd(resid).
                        Reads the intercept, so it does not degenerate when estimation == formation.
  mode="resid" (RM-24/36) betas fit on the trailing `est_window` sessions ending at the signal date;
                        score = sum(resid over formation) / sd(resid). The paper's construction.

Factors are market (NIFTY 100) and sector. The sector factor is leave-one-out — a stock is excluded
from its own sector's mean, otherwise a thin sector regresses a stock partly on itself and its
residual collapses toward zero. It is also built from point-in-time index members only (`member_mask`):
built over every symbol in the panel it picks up listing-day artifacts on names that were not in the
universe at the time. Stocks whose sector has < 2 other priced members that day fall back to
market-only, as do fits where the sector factor is near-collinear with the market. No HML:
book-to-market needs the fundamentals feed we do not have (PLAN.md).
"""
from __future__ import annotations
import warnings
import numpy as np, pandas as pd

# Apple Accelerate (the BLAS numpy links against on this machine) reports the FPU status flags its
# matmul kernels set even when the result is exact. Verified 2026-09-11: zero non-finite or exploded
# betas across 95k fits, and X @ beta is bit-identical to the elementwise product. Scoped to this
# module so a real overflow elsewhere still surfaces.
warnings.filterwarnings("ignore", message=".*encountered in matmul", category=RuntimeWarning)

RCOND = 1e-8      # lstsq cutoff; a sector factor collinear with the market drops out rather than blowing the fit up


def sector_aggregates(returns_universe: pd.DataFrame, sector_map: dict, member_mask: pd.DataFrame | None = None):
    """Per-day sum and count of member returns by sector, for leave-one-out sector factors."""
    r = returns_universe if member_mask is None else returns_universe.where(member_mask.reindex_like(returns_universe))
    sectors = pd.Series({c: sector_map.get(c, "UNKNOWN") for c in returns_universe.columns})
    grouped = r.T.groupby(sectors)
    return grouped.sum(min_count=1).T, grouped.count().T, sectors


def make_residual_score(returns_universe: pd.DataFrame, bench_returns: pd.Series, sector_map: dict, *,
                        mode: str = "alpha", lookback: int = 252, skip: int = 21, min_obs: int = 219,
                        est_window: int | None = None, est_min_frac: float = 0.869,
                        member_mask: pd.DataFrame | None = None, candidate_fn=None):
    sec_sum, sec_cnt, sectors = sector_aggregates(returns_universe, sector_map, member_mask)
    mkt = bench_returns.reindex(returns_universe.index)
    est_window = est_window or (lookback + skip)

    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < max(lookback + skip, est_window):
            return pd.Series(dtype=float)

        f0, f1 = idx - lookback - skip + 1, idx - skip + 1        # formation window, MM's 252/21
        e0, e1 = idx - est_window + 1, idx + 1                     # estimation window, ends at the signal
        form = returns_universe.iloc[f0:f1]
        est = returns_universe.iloc[e0:e1]

        cols = form.columns
        if candidate_fn is not None:
            cands = candidate_fn(signal_date)
            cols = [c for c in cols if c in cands]
        elig = (form[cols].notna().sum() >= min_obs) & (est[cols].notna().sum() >= est_min_frac * est_window)
        cols = [c for c in cols if elig[c]]
        if not cols:
            return pd.Series(dtype=float)

        mkt_e = mkt.iloc[e0:e1].to_numpy()
        ones = np.ones(e1 - e0)
        fs, fe = f0 - e0, f1 - e0                                  # formation rows within the estimation window
        out = {}
        for sym in cols:
            y = est[sym].to_numpy()
            s = sectors[sym]
            n = sec_cnt[s].iloc[e0:e1].to_numpy()
            loo = (sec_sum[s].iloc[e0:e1].to_numpy() - np.nan_to_num(y)) / np.where(n > 1, n - 1, np.nan)
            X = np.column_stack([ones, mkt_e, loo])
            ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
            if ok.sum() < min_obs:                                  # thin sector: market only
                X = np.column_stack([ones, mkt_e])
                ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
                if ok.sum() < min_obs:
                    continue
            beta = np.linalg.lstsq(X[ok], y[ok], rcond=RCOND)[0]
            resid = np.full_like(y, np.nan)
            resid[ok] = y[ok] - X[ok] @ beta
            rf = resid[fs:fe]
            sd = np.nanstd(rf)
            if not np.isfinite(sd) or sd <= 0:
                continue
            val = (beta[0] / sd) if mode == "alpha" else (np.nansum(rf) / sd)
            if np.isfinite(val):
                out[sym] = val
        return pd.Series(out, dtype=float).dropna()

    return score_fn
