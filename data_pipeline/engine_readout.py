"""Pure helpers for reading what the engine decided at a rebalance.

The engine emits multiple trades on the rebalance date with different
``reason`` codes — ``entry``, ``rank``, ``regime_bear`` (partial trim during
bear regime), ``regime_topup`` (partial buy when regime turns up), and
weekly-exit reasons (``atr_stop``, ``200dma``, ``donchian``,
``rank_weekly``). For the rebalance *page* we surface **membership changes
only**: a partial trim or top-up on a continuing holding is **not** an action
the subscriber should take. The product reasoning is in
``tasks/rebalance_page/PLAN.md`` — see "Action scope: membership changes
only" and the "partial trims are not membership changes" gotcha.

This module is pure (no pandas dataframe ops beyond column access, no DB,
no network), so it stays cheap to unit-test and is fully decoupled from the
producer script that wires it up to the engine.
"""
from __future__ import annotations

from typing import Iterable, Mapping, Optional, Union

import pandas as pd


def holdings_from_trades(
    trades: pd.DataFrame,
    up_to: Optional[Union[str, pd.Timestamp]] = None,
) -> dict:
    """Reconstruct net shares held per symbol from a trade ledger.

    Args:
        trades: rows with ``date``, ``symbol``, ``side`` (``BUY`` / ``SELL``),
            ``shares``. Extra columns (e.g. ``reason``, ``price``) are ignored.
        up_to: optional inclusive cutoff. Trades with ``date > up_to`` are
            ignored. ``None`` means use the full ledger.

    Returns:
        ``{symbol: shares}`` for symbols with strictly positive net shares.
        Symbols whose net shares fell to zero (or below) are dropped, so a
        ``len(...)`` of this dict is the current model book size.
    """
    if trades is None or len(trades) == 0:
        return {}

    df = trades[["date", "symbol", "side", "shares"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    if up_to is not None:
        df = df[df["date"] <= pd.Timestamp(up_to)]

    held: dict = {}
    for _, row in df.iterrows():
        sym = row["symbol"]
        sh = int(row["shares"])
        side = row["side"]
        if side == "BUY":
            held[sym] = held.get(sym, 0) + sh
        elif side == "SELL":
            held[sym] = held.get(sym, 0) - sh
        # Ignore any other side codes — engine only emits BUY/SELL today.

    return {s: v for s, v in held.items() if v > 0}


def partition_membership_by_date(
    trades: pd.DataFrame,
    exec_date: Union[str, pd.Timestamp],
) -> dict:
    """Partition holdings into exits / entries / continuing at ``exec_date``.

    Membership-only: derived from the **net share transition** across the
    exec date. A partial trim that leaves the position alive is a HOLD, not
    a SELL. A top-up that adds shares to a continuing holding is a HOLD,
    not a BUY.

    Args:
        trades: the engine's full trade ledger (after the placeholder-bar
            run so the signal-day rebalance is present).
        exec_date: the placeholder exec date — i.e. the trade date of the
            rebalance we are surfacing.

    Returns:
        ``{"exits": [...], "entries": [...], "continuing": [...]}`` with
        symbols sorted alphabetically inside each list.
    """
    exec_ts = pd.Timestamp(exec_date)
    # Pre = strictly before exec_date; Post = inclusive of exec_date.
    pre = holdings_from_trades(trades, up_to=exec_ts - pd.Timedelta(days=1))
    post = holdings_from_trades(trades, up_to=exec_ts)

    pre_set = set(pre)
    post_set = set(post)

    return {
        "exits": sorted(pre_set - post_set),
        "entries": sorted(post_set - pre_set),
        "continuing": sorted(pre_set & post_set),
    }
