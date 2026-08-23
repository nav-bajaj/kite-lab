"""Pure functions for corporate-action cliff detection and repair.

No I/O here — everything takes DataFrames/Series and returns plain
data, so the guard, the scanner, and the repair tool share one tested
implementation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Known corporate-action price ratios: bonus a:b -> b/(a+b); split to
# face value f from F -> f/F. Inverses cover raw-vs-adjusted flip-flops
# in an oscillating file.
_BASE_RATIOS = {
    "bonus_1:1_or_split_1:2": 1 / 2,
    "bonus_1:2": 2 / 3,
    "bonus_2:1": 1 / 3,
    "bonus_1:3": 3 / 4,
    "bonus_3:1": 1 / 4,
    "bonus_2:3": 3 / 5,
    "split_1:5": 1 / 5,
    "split_1:10": 1 / 10,
    "split_2:5": 2 / 5,
}
KNOWN_RATIOS = dict(_BASE_RATIOS)
KNOWN_RATIOS.update({f"undo_{k}": 1 / v for k, v in _BASE_RATIOS.items()})

CLIFF_THRESHOLD = 0.28        # |1-day move| beyond this is a cliff
RATIO_TOLERANCE = 0.035       # snap tolerance to a known CA ratio


def detect_cliffs(close: pd.Series, threshold: float = CLIFF_THRESHOLD) -> pd.DataFrame:
    """Adjacent-session moves beyond ±threshold.

    close: Series indexed by date. Returns DataFrame[date, ratio, move_pct].
    """
    r = close.astype(float).pct_change()
    hits = r[r.abs() > threshold].dropna()
    return pd.DataFrame({
        "date": hits.index,
        "ratio": (1 + hits).to_numpy(),
        "move_pct": (hits * 100).round(1).to_numpy(),
    })


def classify_ratio(ratio: float, tolerance: float = RATIO_TOLERANCE) -> str | None:
    """Name of the closest known CA ratio within tolerance, else None.

    Tolerance is relative, so a same-day market move of a few percent on
    top of the CA step still classifies.
    """
    best, best_err = None, tolerance
    for name, known in KNOWN_RATIOS.items():
        err = abs(ratio / known - 1)
        if err < best_err:
            best, best_err = name, err
    return best


def classify_cliffs(cliffs: pd.DataFrame) -> pd.DataFrame:
    """Add a `label` column: known-ratio name or 'unclassified'.

    Unclassified cliffs are real crashes/rallies or demergers (arbitrary
    ratios) — they need eyes, not automation.
    """
    out = cliffs.copy()
    out["label"] = [classify_ratio(x) or "unclassified" for x in out["ratio"]]
    return out


def seam_ratio(old: pd.Series, new: pd.Series, min_overlap: int = 5) -> float | None:
    """Median new/old close ratio over shared dates (re-base factor for
    pre-seam history). None if overlap is too thin or the ratio is not
    stable (mixed regimes → repair must not proceed blindly)."""
    shared = old.index.intersection(new.index)
    if len(shared) < min_overlap:
        return None
    ratios = (new.loc[shared] / old.loc[shared]).dropna()
    if ratios.empty:
        return None
    med = float(ratios.median())
    if not np.isfinite(med) or med <= 0:
        return None
    spread = float((ratios / med).sub(1).abs().max())
    if spread > 0.02:          # overlap disagrees with itself → unsafe
        return None
    return med


def definitive_ca_mask(cliffs: pd.DataFrame, window_days: int = 25) -> pd.Series:
    """True where a classified cliff is DEFINITIVELY a corporate action,
    not a large real move that happens to sit near a known ratio.

    Two sufficient conditions:
      - magnitude: |move| >= 40% (no real NSE session does this outside
        catastrophes, which don't snap to clean ratios), or
      - flip-flop: a reciprocal classified cliff within `window_days`
        (the raw/adjusted oscillation signature of the overlap-refetch
        bug).

    Isolated moves in the ±28-40% band (e.g. the 2017-10-25 PSU-recap
    rally, IDEA's March-2020 AGR swings) stay False — verify those
    against a fresh Kite fetch before touching them.
    """
    if cliffs.empty:
        return pd.Series(dtype=bool)
    labeled = cliffs["label"] != "unclassified" if "label" in cliffs else \
        pd.Series(True, index=cliffs.index)
    big = cliffs["move_pct"].abs() >= 40.0
    dates = pd.to_datetime(cliffs["date"])
    flip = pd.Series(False, index=cliffs.index)
    for i in cliffs.index:
        for j in cliffs.index:
            if i == j:
                continue
            if abs((dates[i] - dates[j]).days) > window_days:
                continue
            if abs(cliffs.loc[i, "ratio"] * cliffs.loc[j, "ratio"] - 1) < 0.10:
                flip[i] = True
                break
    return labeled & (big | flip)


def file_is_clean(close: pd.Series, threshold: float = CLIFF_THRESHOLD,
                  allow_unclassified: bool = True) -> bool:
    """True when the series has no CA-signature cliffs. Unclassified
    cliffs (real crashes) are allowed by default — they are data."""
    cliffs = classify_cliffs(detect_cliffs(close, threshold))
    if cliffs.empty:
        return True
    if allow_unclassified:
        return bool((cliffs["label"] == "unclassified").all())
    return False
