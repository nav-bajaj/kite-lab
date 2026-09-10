"""Price-momentum scores for the MM rebuild. Same score_fn interface as the OM25 capture score."""
from __future__ import annotations
import numpy as np, pandas as pd


def make_momentum_score(returns_universe: pd.DataFrame, *, kind: str = "abs", lookback: int = 126, min_obs: int = 110,
                        skip: int = 0, vol_floor: float = 0.05, positive_only: bool = False, candidate_fn=None):
    """kind='abs': trailing return over the window. kind='voladj': that return / annualised daily vol, vol floored (L6 v2's form).
    skip: sessions excluded at the end of the window (the classic 12-1 skips ~21). Eligibility: >= min_obs returns in the window."""
    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback + skip:
            return pd.Series(dtype=float)
        window = returns_universe.iloc[idx - lookback - skip + 1: idx - skip + 1]
        if candidate_fn is not None:
            cands = candidate_fn(signal_date)
            window = window[[c for c in window.columns if c in cands]]
        elig = window.notna().sum() >= min_obs
        w = window.loc[:, elig.values]
        if w.shape[1] == 0:
            return pd.Series(dtype=float)
        mom = (1 + w.fillna(0)).prod() - 1
        if kind == "voladj":
            vol = (w.std() * np.sqrt(252)).clip(lower=vol_floor)
            score = mom / vol
        else:
            score = mom
        if positive_only:
            score = score[mom > 0]
        return score.dropna()
    return score_fn
