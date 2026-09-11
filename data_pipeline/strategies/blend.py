"""Rank blend of two score functions (OM25 v4: 50% vol-adjusted momentum + 50% capture ratio)."""
from __future__ import annotations
import pandas as pd


def make_blend_score(score_a, score_b, w_a: float = 0.5):
    """Percentile-rank blend: w_a * rank(score_a) + (1 - w_a) * rank(score_b) over the names both scores rank."""
    def score_fn(signal_date, **_):
        a = score_a(signal_date); b = score_b(signal_date); i = a.index.intersection(b.index)
        if len(i) == 0:
            return pd.Series(dtype=float)
        return w_a * a[i].rank(pct=True) + (1 - w_a) * b[i].rank(pct=True)
    return score_fn
