"""Position sizing and count hooks for scripts/_clean_engine.run_strategy (size_weights, top_n_fn)."""
from __future__ import annotations
import numpy as np
import pandas as pd


def make_inverse_vol_weights(returns: pd.DataFrame, window: int = 63, max_weight: float = 0.10, bear_only=None):
    """size_weights hook: weights proportional to 1 / realised vol over `window` sessions ending at the signal date,
    capped at max_weight and renormalised. The entry executes the next session, so sizing never sees the entry day.
    bear_only: optional bool Series (True = bull); when given, returns None (equal weight) in bull."""
    ivol = 1.0 / returns.rolling(window, min_periods=int(window * 0.8)).std().replace(0, np.nan)
    def size_weights(signal_date, symbols):
        if signal_date is None or signal_date not in ivol.index:
            return None
        if bear_only is not None and bool(bear_only.get(signal_date, True)):
            return None
        v = ivol.loc[signal_date].reindex(symbols).dropna()
        if v.empty:
            return None
        w = v / v.sum()
        for _ in range(5):
            over = w > max_weight
            if not over.any():
                break
            w[over] = max_weight; rest = w[~over]
            w[~over] = rest / rest.sum() * (1 - max_weight * over.sum()) if rest.sum() > 0 else rest
        return w.to_dict()
    return size_weights


def make_bear_top_n(regime: pd.Series, top_n: int, bear_n: int):
    """top_n_fn hook: `top_n` names in bull, at most `bear_n` in bear; `regime` is the lagged bool series (True = bull)."""
    def top_n_fn(signal_date):
        return top_n if signal_date is None or bool(regime.get(signal_date, True)) else bear_n
    return top_n_fn


def truncate_in_bear(score_fn, regime: pd.Series, keep: int):
    """Wrap a score fn so that in bear only the top `keep` names are returned (exit rank = keep, with the engine's buffer inside it)."""
    def wrapped(signal_date, **_):
        sc = score_fn(signal_date)
        return sc if bool(regime.get(signal_date, True)) else sc.nlargest(keep)
    return wrapped
