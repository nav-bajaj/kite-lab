"""Forced-sale-for-tax simulation and post-tax equity curve.

At each Apr 1, the investor owes ``tax_owed`` for the prior FY. Since the
strategies are typically fully invested, cash on hand is far smaller than the
tax bill, so we assume the entire tax is funded by liquidating positions.
Raising ``tax_owed`` rupees of cash after 30 bps slippage requires selling
``tax_owed / (1 - slip)`` rupees of market value, i.e. an extra
``tax_owed * slip / (1 - slip)`` of slippage cost.

The post-tax equity curve is built **multiplicatively**: at each tax event,
the cumulative scale factor drops by ``drag / pre_tax_PV``. This reflects the
real-world dynamic where tax money is gone and the smaller post-tax portfolio
compounds forward at the strategy's rate.

Simplifications (see PLAN.md "Out of scope"):
  - The realized P&L from forced sales is NOT fed into the next FY's tax base.
    Forced sales target the smallest positions (least appreciated); their
    realized gains are small relative to tax owed, so the propagation error is
    a few bps of CAGR per year.
  - Cash-availability check skipped — we assume cash << tax_owed (true for
    fully-invested momentum strategies; the few-bp error is documented in
    caveats).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from tax_engine import FYTax

FORCED_SALE_SLIPPAGE_RATE = 0.003  # 30 bps — must match the backtest slippage


@dataclass
class TaxEvent:
    pay_date: pd.Timestamp       # Apr 1 of the FY in which tax is paid
    fy_assessed: pd.Timestamp    # Apr 1 of the FY whose income is being taxed
    fy_label: str
    tax_paid: float              # ₹ remitted to the tax authority
    forced_sale_slippage: float  # extra ₹ lost to slippage raising the cash
    total_drag: float            # tax_paid + forced_sale_slippage
    pre_tax_pv: float            # PV at pay_date (from backtest equity)
    post_tax_pv_pre_event: float # pre-event scaled PV
    post_tax_pv_post_event: float
    deferred: bool = False       # True if pay_date was past equity end (provisioned on last day)


def build_tax_events(fy_results: Iterable[FYTax],
                      equity: pd.DataFrame,
                      slip_rate: float = FORCED_SALE_SLIPPAGE_RATE
                      ) -> tuple[list[TaxEvent], pd.Series]:
    """For each FY with tax owed, create a TaxEvent on the following Apr 1.

    Returns:
      events:          list of TaxEvent (chronological, all the actual tax
                       payments — events with zero tax are dropped)
      scale_series:    pd.Series indexed by equity['date'] giving the
                       multiplicative scale factor at each date (post-tax PV =
                       pre-tax PV × scale).
    """
    eq = equity.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.sort_values("date").reset_index(drop=True)

    pv = eq["pv"].to_numpy().astype(float)
    dates_np = eq["date"].to_numpy().astype("datetime64[ns]")
    scale = np.ones(len(eq))
    current_scale = 1.0
    cursor = 0
    events: list[TaxEvent] = []

    for fy in fy_results:
        if fy.total_tax <= 0:
            continue
        pay_date = pd.Timestamp(year=fy.fy_start.year + 1, month=4, day=1)
        # Find first equity index on or after pay_date
        idx = int(np.searchsorted(dates_np, np.datetime64(pay_date), side="left"))
        deferred = False
        if idx >= len(pv):
            # Pay date is past the end of the equity series. The investor still
            # owes this tax — would settle it on next Apr 1 in real life. To
            # reflect the deferred liability in the post-tax PV, we apply it on
            # the last equity day. Slight overstatement of drag (the money
            # could have compounded for ~11 more months) but matches the
            # "settled net worth" view; without it B&H looks artificially
            # tax-free, since its only realized gain is on the final SELL.
            idx = len(pv) - 1
            deferred = True

        pre_tax_pv_at = float(pv[idx])
        if pre_tax_pv_at <= 0:
            continue

        slip = fy.total_tax * slip_rate / (1.0 - slip_rate)
        drag = fy.total_tax + slip

        post_pre = pre_tax_pv_at * current_scale
        post_post = post_pre - drag
        if post_post <= 0:
            # Would drive the portfolio negative — clamp
            post_post = 0.0

        # Fill scale[cursor:idx] with the *prior* scale (this point's value is
        # the pre-event value; the event lands at this index and propagates).
        scale[cursor:idx] = current_scale
        # New scale: post_post / pre_tax_pv_at
        current_scale = post_post / pre_tax_pv_at
        cursor = idx

        events.append(TaxEvent(
            pay_date=eq.iloc[idx]["date"],
            fy_assessed=fy.fy_start,
            fy_label=fy.fy_label,
            tax_paid=fy.total_tax,
            forced_sale_slippage=slip,
            total_drag=drag,
            pre_tax_pv=pre_tax_pv_at,
            post_tax_pv_pre_event=post_pre,
            post_tax_pv_post_event=post_post,
            deferred=deferred,
        ))

    # Fill the remainder
    scale[cursor:] = current_scale

    scale_series = pd.Series(scale, index=eq["date"])
    return events, scale_series


def post_tax_summary(equity: pd.DataFrame,
                      events: list[TaxEvent],
                      scale: pd.Series) -> dict:
    """Compute headline summary stats from the scale curve."""
    eq = equity.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.sort_values("date").reset_index(drop=True)

    initial_pv = float(eq.iloc[0]["pv"])
    final_pre = float(eq.iloc[-1]["pv"])
    final_post = final_pre * float(scale.iloc[-1])
    years = (eq.iloc[-1]["date"] - eq.iloc[0]["date"]).days / 365.25

    pretax_cagr = (final_pre / initial_pv) ** (1.0 / years) - 1.0 if years > 0 else 0.0
    posttax_cagr = (final_post / initial_pv) ** (1.0 / years) - 1.0 if years > 0 else 0.0
    drag_bps = (pretax_cagr - posttax_cagr) * 10_000

    total_tax = sum(e.tax_paid for e in events)
    total_slip = sum(e.forced_sale_slippage for e in events)
    total_drag = sum(e.total_drag for e in events)

    return {
        "initial_pv": initial_pv,
        "final_pretax_pv": final_pre,
        "final_posttax_pv": final_post,
        "years": years,
        "pretax_cagr": pretax_cagr,
        "posttax_cagr": posttax_cagr,
        "drag_bps": drag_bps,
        "total_tax_paid": total_tax,
        "total_forced_slippage": total_slip,
        "total_drag_nominal": total_drag,  # raw sum of nominal drags, not compounded
        "n_tax_events": len(events),
        "tax_as_pct_final_pretax_pv": total_tax / final_pre * 100 if final_pre > 0 else 0,
        "drag_as_pct_final_pretax_pv": total_drag / final_pre * 100 if final_pre > 0 else 0,
    }
