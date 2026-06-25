"""Emit the upcoming-rebalance proposal artifact for a portfolio run.

Reuses the strategy's own ``score_fn`` to rank the universe at the last data
bar, then the engine-faithful membership rule
(``data_pipeline.rebalance_proposal``) to produce the membership-only proposal
a subscriber can act on. Writes, into the run's dashboard dir:

  proposed_orders_<target_date>.csv  symbol, side, target_weight, est_notional, est_shares
  proposal_meta.json                 target_date, is_entry, regime, drawdown_from_peak, ...

Callers MUST guard this (a failure here must never break the daily pipeline).
The artifact has no consumer until the sync/API/UI land, so emitting it is
side-effect-free beyond the two files; staging reconciliation validates it
before it reaches clients.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

from data_pipeline.rebalance_proposal import propose_next_rebalance


def _next_friday(d: pd.Timestamp) -> pd.Timestamp:
    """The next calendar Friday strictly after `d`."""
    nf = d + pd.Timedelta(days=(4 - d.weekday()) % 7)
    if nf <= d:
        nf += pd.Timedelta(days=7)
    return nf


def is_entry_week(entry_dates, last_date, interval_weeks: int) -> bool:
    """Whether the upcoming Friday is an entry rebalance vs an exit-only check.

    Weekly strategies enter every Friday. Biweekly strategies enter on every
    `interval_weeks`-th Friday measured from the last actual entry date, so the
    off-week Fridays are exit-only.
    """
    if interval_weeks <= 1:
        return True
    entries = [pd.Timestamp(x) for x in entry_dates]
    if not entries:
        return True
    last_entry = max(entries)
    nf = _next_friday(pd.Timestamp(last_date))
    weeks = round((nf - last_entry).days / 7)
    return weeks % interval_weeks == 0


def emit_proposal(
    *,
    dashboard_dir,
    score_fn,
    close_panel,
    calendar,
    entry_dates,
    top_n: int,
    exit_buffer: int,
    interval_weeks: int = 2,
    regime=None,
    bear_skips_entries: bool = True,
):
    """Compute and write the proposal artifact. Returns the meta dict (or None).

    Reads current holdings + portfolio value from the dashboard CSVs the runner
    has just written, so the only engine coupling is `score_fn` and the panels.
    """
    dashboard_dir = Path(dashboard_dir)
    holdings_path = dashboard_dir / "momentum_holdings.csv"
    if not holdings_path.exists():
        return None
    cur_df = pd.read_csv(holdings_path)
    current_symbols = [str(s) for s in cur_df.get("symbol", [])]

    last_date = pd.Timestamp(calendar[-1])
    scores = score_fn(last_date)
    if scores is None or len(scores) == 0:
        return None
    ranked = list(
        scores.dropna().sort_values(ascending=False).head(top_n + exit_buffer).index
    )

    is_entry = is_entry_week(entry_dates, last_date, interval_weeks)
    is_bear = False
    if regime is not None:
        try:
            is_bear = not bool(regime.get(last_date, True))
        except Exception:
            is_bear = False

    prices = {}
    if last_date in close_panel.index:
        row = close_panel.loc[last_date]
        for s in set(ranked) | set(current_symbols):
            if s in close_panel.columns:
                v = row.get(s)
                if v is not None and not pd.isna(v):
                    prices[s] = float(v)

    capital = None
    drawdown = None
    eq_path = dashboard_dir / "momentum_equity.csv"
    if eq_path.exists():
        eq = pd.read_csv(eq_path)
        if len(eq):
            capital = float(eq["portfolio_value"].iloc[-1])
            if "drawdown" in eq.columns:
                drawdown = float(eq["drawdown"].iloc[-1])

    proposal = propose_next_rebalance(
        ranked,
        current_symbols,
        top_n=top_n,
        exit_buffer=exit_buffer,
        is_entry=is_entry,
        is_bear=is_bear,
        bear_skips_entries=bear_skips_entries,
        prices=prices,
        capital=capital,
    )

    target_date = _next_friday(last_date).date().isoformat()
    orders_path = dashboard_dir / f"proposed_orders_{target_date}.csv"
    with orders_path.open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["symbol", "side", "target_weight", "est_notional", "est_shares"],
        )
        writer.writeheader()
        for row in proposal.to_rows():
            writer.writerow(row)

    meta = {
        "target_date": target_date,
        "is_entry": is_entry,
        "regime": "bear" if is_bear else "bull",
        "drawdown_from_peak": drawdown,
        "data_as_of": last_date.date().isoformat(),
        "capital": capital,
        "sell_count": len(proposal.sells),
        "buy_count": len(proposal.buys),
        "hold_count": len(proposal.holds),
    }
    (dashboard_dir / "proposal_meta.json").write_text(json.dumps(meta, indent=2))
    return meta
