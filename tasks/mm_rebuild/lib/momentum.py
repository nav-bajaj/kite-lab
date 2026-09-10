"""Price-momentum scores for the MM rebuild. Same score_fn interface as the OM25 capture score."""
from __future__ import annotations
import numpy as np, pandas as pd


def make_momentum_score(returns_universe: pd.DataFrame, *, kind: str = "abs", lookback: int = 126, min_obs: int = 110,
                        skip: int = 0, vol_floor: float = 0.05, positive_only: bool = False, candidate_fn=None, cr_quantile: float = 0.0,
                        volume_panel: pd.DataFrame | None = None, vol_kick: str = "none", vol_k: float = 0.0,
                        core_mask: pd.DataFrame | None = None, universe_cap: int = 0, turnover_floor: float = 0.0):
    """Universe hypotheses (Wright review, 2026-09-10): `universe_cap` = N keeps the core members (Nifty 250, `core_mask`) plus the
    (N - core count) most liquid others by mean rupee turnover over the window — a point-in-time 'top N' proxy. `turnover_floor` = rupees
    per day: median turnover over the window must reach it. Both use turnover up to the signal date's close only."""
    """Extra kinds (founder 2026-09-10): 'blend' = mean percentile rank of vol-adjusted momentum at 63 / 126 / 252 sessions (skip applied);
    'slope' = annualised exponential-regression slope x R^2 over the window (Clenow); 'high52' = close / window high, i.e. proximity to the high.
    Volume kicker: score percentile + vol_k x volume percentile, where 'surge' = mean rupee turnover over the last 21 sessions / over the window,
    'level' = mean rupee turnover over the window."""
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
        if (universe_cap or turnover_floor) and volume_panel is not None:
            tw = volume_panel.iloc[idx - lookback - skip + 1: idx - skip + 1].reindex(columns=window.columns)
            if turnover_floor:
                elig &= (tw.median() >= turnover_floor).values
            if universe_cap and core_mask is not None:
                core = core_mask.loc[signal_date].reindex(window.columns).fillna(False).values & elig.values
                k = max(0, universe_cap - int(core.sum()))
                others = tw.mean().where(elig.values & ~core).nlargest(k).index
                elig &= (core | window.columns.isin(others))
        if cr_quantile > 0:   # founder 2026-09-10: momentum ranked only within the top share of names by capture ratio over the same window
            we = window.loc[:, elig.values]; market = we.mean(axis=1); up, dn = market > 0, market < 0
            mu_up, mu_dn = market[up].mean(), market[dn].mean()
            if mu_up > 0 and mu_dn < 0:
                uc = we[up].mean() / mu_up; dc = we[dn].mean() / mu_dn
                cr = (uc / dc.where(dc > 0)).fillna(uc).dropna()
                keep = cr[cr >= cr.quantile(1 - cr_quantile)].index
                elig &= window.columns.isin(keep)
        w = window.loc[:, elig.values]
        if w.shape[1] == 0:
            return pd.Series(dtype=float)
        mom = (1 + w.fillna(0)).prod() - 1
        if kind == "voladj":
            vol = (w.std() * np.sqrt(252)).clip(lower=vol_floor)
            score = mom / vol
        elif kind == "blend":
            parts = []
            for L in (63, 126, 252):
                if idx < L + skip: continue
                wl = returns_universe.iloc[idx - L - skip + 1: idx - skip + 1][w.columns]
                ml = (1 + wl.fillna(0)).prod() - 1; vl = (wl.std() * np.sqrt(252)).clip(lower=vol_floor)
                parts.append((ml / vl).rank(pct=True))
            score = pd.concat(parts, axis=1).mean(axis=1)
        elif kind == "slope":
            lp = np.log((1 + w.fillna(0)).cumprod()); x = np.arange(len(lp)); xm = x - x.mean()
            beta = (lp.sub(lp.mean())).mul(xm, axis=0).sum() / (xm ** 2).sum()
            resid = lp.sub(lp.mean()) - np.outer(xm, beta); r2 = 1 - (resid ** 2).sum() / (lp.sub(lp.mean()) ** 2).sum().replace(0, np.nan)
            score = (np.exp(beta * 252) - 1) * r2
        elif kind == "high52":
            lvl = (1 + w.fillna(0)).cumprod(); score = lvl.iloc[-1] / lvl.max()
        else:
            score = mom
        if positive_only:
            score = score[mom > 0]
        score = score.dropna()
        if vol_kick != "none" and volume_panel is not None and vol_k > 0:
            vw = volume_panel.iloc[idx - lookback - skip + 1: idx - skip + 1].reindex(columns=score.index)
            v = (vw.tail(21).mean() / vw.mean()) if vol_kick == "surge" else vw.mean()
            score = score.rank(pct=True) + vol_k * v.rank(pct=True)
        return score.dropna()
    return score_fn
