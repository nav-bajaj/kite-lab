"""Public index-returns endpoint for the portfolio Overview page.

Rolling price returns for the four headline NSE size indices
(Nifty 50 / 100 / 250 / 500) over 1M / 6M / 1Y / 3Y / 5Y, so the Overview can
show the portfolio's returns *in context*. Public, read-only market data — no
auth, mirroring the insights router. "Nifty 250" is the NIFTY LargeMidcap 250
(250 names), matching the product's `nifty250` universe.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
from fastapi import APIRouter, Response

from app.insights._freshness import file_signature
from app.insights._paths import indices_dir

router = APIRouter(prefix="/api/indices", tags=["indices"])

# (key, display label, index CSV in indices_dir()).
_INDICES: list[tuple[str, str, str]] = [
    ("nifty50", "Nifty 50", "NIFTY_50.csv"),
    ("nifty100", "Nifty 100", "NIFTY_100.csv"),
    ("nifty250", "Nifty 250", "NIFTY_LARGEMID250.csv"),
    ("nifty500", "Nifty 500", "NIFTY_500.csv"),
]

# Horizon key -> calendar offset back from the latest close.
_HORIZONS: list[tuple[str, pd.DateOffset]] = [
    ("1M", pd.DateOffset(months=1)),
    ("6M", pd.DateOffset(months=6)),
    ("1Y", pd.DateOffset(years=1)),
    ("3Y", pd.DateOffset(years=3)),
    ("5Y", pd.DateOffset(years=5)),
]


def _load_close(filename: str) -> pd.Series:
    return _load_close_cached(filename, file_signature(indices_dir() / filename))


@lru_cache(maxsize=8)
def _load_close_cached(filename: str, signature: float) -> pd.Series:
    df = pd.read_csv(indices_dir() / filename, parse_dates=["date"])
    return df.set_index("date")["close"].sort_index().dropna()


def _rolling_returns(s: pd.Series) -> dict[str, float | None]:
    """Return over each horizon = last close / close on-or-before (last - H) - 1.

    None when there isn't enough history to reach back that far.
    """
    out: dict[str, float | None] = {}
    if s.empty:
        return {k: None for k, _ in _HORIZONS}
    last_date = s.index[-1]
    last_px = float(s.iloc[-1])
    for key, offset in _HORIZONS:
        prior = s.loc[: last_date - offset]
        if prior.empty:
            out[key] = None
            continue
        base = float(prior.iloc[-1])
        out[key] = (last_px / base - 1.0) if base > 0 else None
    return out


@router.get("/returns")
async def index_returns(response: Response) -> dict:
    """Rolling returns for the four headline indices. Public market data."""
    response.headers["Cache-Control"] = "public, max-age=900"
    indices = []
    as_of: pd.Timestamp | None = None
    for key, label, filename in _INDICES:
        try:
            s = _load_close(filename)
        except (FileNotFoundError, KeyError):
            indices.append(
                {
                    "key": key,
                    "label": label,
                    "as_of": None,
                    "data_available": False,
                    "returns": {h: None for h, _ in _HORIZONS},
                }
            )
            continue
        if not s.empty and (as_of is None or s.index[-1] > as_of):
            as_of = s.index[-1]
        indices.append(
            {
                "key": key,
                "label": label,
                "as_of": s.index[-1].date().isoformat() if not s.empty else None,
                "data_available": not s.empty,
                "returns": _rolling_returns(s),
            }
        )
    return {
        "as_of": as_of.date().isoformat() if as_of is not None else None,
        "horizons": [h for h, _ in _HORIZONS],
        "indices": indices,
    }
