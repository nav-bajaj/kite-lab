"""Per-trade Indian capital-gains tax engine.

Walks a trades.csv in chronological order, FIFO-matches each SELL against the
oldest open BUY lots for that symbol, classifies the realized gain/loss as
short-term (≤365 days) or long-term (>365 days), aggregates by Indian financial
year (Apr 1 → Mar 31), applies 8-FY FIFO loss carry-forward and the ₹1.25L
annual LTCG exemption, then applies the current Indian rates:

    STCG  20%
    LTCG  12.5% above ₹1.25L FY exemption

Prices in trades.csv are the raw OHLC/4 execution price; the `slippage` column
is the absolute ₹ cost of slippage at the configured rate. Effective costs
used for P&L calculation:

    BUY:   effective cost per share    = (notional + slippage) / shares
    SELL:  effective proceeds per share = (notional - slippage) / shares

Memory: P&L must use effective prices — the user corrected this once already.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

STCG_RATE = 0.20
LTCG_RATE = 0.125
LTCG_FY_EXEMPTION = 125_000.0
LTCG_HOLDING_DAYS = 365  # > this many days = long term
CARRY_FORWARD_FYS = 8


@dataclass
class RealizedLot:
    sell_date: pd.Timestamp
    buy_date: pd.Timestamp
    symbol: str
    shares: float
    cost: float          # effective ₹ paid for those shares (incl buy slippage)
    proceeds: float      # effective ₹ received from sale (incl sell slippage)
    holding_days: int
    bucket: str          # "ST" or "LT"

    @property
    def gross_pnl(self) -> float:
        return self.proceeds - self.cost


@dataclass
class FYTax:
    fy_start: pd.Timestamp
    st_gross: float           # signed sum of all ST events in FY
    lt_gross: float
    st_taxable: float         # after all offsets & exemption (>=0)
    lt_taxable: float
    stcg_tax: float
    ltcg_tax: float
    total_tax: float
    intra_fy_stcl_used_against_lt: float
    cf_stcl_used: float
    cf_ltcl_used: float
    ltcg_exemption_used: float
    stcl_carry_in: float      # opening balance at start of FY
    ltcl_carry_in: float
    stcl_carry_out: float     # closing balance at end of FY (after this year's events)
    ltcl_carry_out: float

    @property
    def fy_label(self) -> str:
        return f"FY{self.fy_start.year}-{str(self.fy_start.year + 1)[-2:]}"


def fy_for(d: pd.Timestamp) -> pd.Timestamp:
    """Return the Apr 1 start of the Indian FY containing date d."""
    yr = d.year if d.month >= 4 else d.year - 1
    return pd.Timestamp(year=yr, month=4, day=1)


def match_lots(trades: pd.DataFrame) -> tuple[list[RealizedLot], dict[str, list[dict]]]:
    """FIFO-match SELLs against open BUYs in chronological order.

    Returns (realized_lots, open_positions). open_positions maps each symbol
    with remaining open shares to a list of {buy_date, shares_remaining,
    cost_per_share} lots still held at the end of the trade log.
    """
    realized: list[RealizedLot] = []
    open_lots: dict[str, deque] = {}

    trades = trades.copy()
    trades["date"] = pd.to_datetime(trades["date"])
    trades = trades.sort_values(["date", "side"], ascending=[True, False]).reset_index(drop=True)
    # Sort BUY before SELL on the same date so that same-day BUY→SELL is matchable.

    for _, t in trades.iterrows():
        sym = str(t["symbol"])
        shares = float(t["shares"])
        notional = float(t["notional"])
        slip = float(t["slippage"])
        side = str(t["side"]).upper()
        date = t["date"]

        q = open_lots.setdefault(sym, deque())

        if side == "BUY":
            cps = (notional + slip) / shares
            q.append({
                "buy_date": date,
                "shares_remaining": shares,
                "cost_per_share": cps,
            })
        elif side == "SELL":
            pps = (notional - slip) / shares
            to_match = shares
            while to_match > 1e-9 and q:
                lot = q[0]
                matched = min(lot["shares_remaining"], to_match)
                cost = matched * lot["cost_per_share"]
                proc = matched * pps
                hold = (date - lot["buy_date"]).days
                realized.append(RealizedLot(
                    sell_date=date,
                    buy_date=lot["buy_date"],
                    symbol=sym,
                    shares=matched,
                    cost=cost,
                    proceeds=proc,
                    holding_days=hold,
                    bucket="LT" if hold > LTCG_HOLDING_DAYS else "ST",
                ))
                lot["shares_remaining"] -= matched
                to_match -= matched
                if lot["shares_remaining"] < 1e-9:
                    q.popleft()
            if to_match > 1e-9:
                raise RuntimeError(
                    f"SELL exceeds open lots for {sym} on {date}: "
                    f"{to_match} shares unmatched"
                )
        else:
            raise ValueError(f"Unknown trade side: {side!r}")

    open_positions = {s: list(q) for s, q in open_lots.items() if q}
    return realized, open_positions


def _take_from_queue(q: deque, amount: float) -> tuple[float, deque]:
    """Consume up to `amount` from the FIFO queue of (origin_fy, ₹) entries.
    Returns (amount_actually_used, new_queue)."""
    used = 0.0
    new_q: deque = deque()
    remaining = amount
    for orig_fy, amt in q:
        if remaining <= 1e-9:
            new_q.append((orig_fy, amt))
            continue
        take = min(amt, remaining)
        used += take
        remaining -= take
        if amt - take > 1e-9:
            new_q.append((orig_fy, amt - take))
    return used, new_q


def compute_tax_per_fy(realized: list[RealizedLot]) -> list[FYTax]:
    """Apply Indian CG tax law: intra-FY set-off, 8-year FIFO carry-forward,
    ₹1.25L LTCG exemption, then rates."""
    grouped: dict[pd.Timestamp, dict[str, list[RealizedLot]]] = {}
    for r in realized:
        fy = fy_for(r.sell_date)
        grouped.setdefault(fy, {"ST": [], "LT": []})[r.bucket].append(r)
    if not grouped:
        return []
    fys = sorted(grouped.keys())

    stcl_cf: deque[tuple[pd.Timestamp, float]] = deque()
    ltcl_cf: deque[tuple[pd.Timestamp, float]] = deque()
    out: list[FYTax] = []

    for fy in fys:
        events = grouped[fy]
        st_gross = sum(r.gross_pnl for r in events["ST"])
        lt_gross = sum(r.gross_pnl for r in events["LT"])

        # Expire carry-forward entries older than 8 FYs
        cutoff = pd.Timestamp(year=fy.year - CARRY_FORWARD_FYS, month=4, day=1)
        while stcl_cf and stcl_cf[0][0] < cutoff:
            stcl_cf.popleft()
        while ltcl_cf and ltcl_cf[0][0] < cutoff:
            ltcl_cf.popleft()
        stcl_carry_in = sum(amt for _, amt in stcl_cf)
        ltcl_carry_in = sum(amt for _, amt in ltcl_cf)

        # Step 1: Intra-FY set-off. STCL (negative ST) can offset positive LT
        # in the same FY. LTCL cannot offset STCG.
        net_st = st_gross
        net_lt = lt_gross
        intra_fy_stcl_used = 0.0
        if net_st < 0 and net_lt > 0:
            absorbed = min(-net_st, net_lt)
            net_lt -= absorbed
            net_st += absorbed
            intra_fy_stcl_used = absorbed

        # Step 2: Carry-forward STCL → first against ST, then against LT
        cf_stcl_used = 0.0
        if net_st > 0 and stcl_cf:
            used, stcl_cf = _take_from_queue(stcl_cf, net_st)
            net_st -= used
            cf_stcl_used += used
        if net_lt > 0 and stcl_cf:
            used, stcl_cf = _take_from_queue(stcl_cf, net_lt)
            net_lt -= used
            cf_stcl_used += used

        # Step 3: Carry-forward LTCL → only against LT
        cf_ltcl_used = 0.0
        if net_lt > 0 and ltcl_cf:
            used, ltcl_cf = _take_from_queue(ltcl_cf, net_lt)
            net_lt -= used
            cf_ltcl_used += used

        # Step 4: Apply ₹1.25L LTCG exemption
        ltcg_exemption_used = 0.0
        if net_lt > 0:
            used = min(LTCG_FY_EXEMPTION, net_lt)
            net_lt -= used
            ltcg_exemption_used = used

        # Step 5: Add this year's residual losses to carry-forward queues
        # (only the portion NOT absorbed intra-FY)
        if st_gross < 0:
            stcl_residual = (-st_gross) - intra_fy_stcl_used
            if stcl_residual > 1e-9:
                stcl_cf.append((fy, stcl_residual))
        if lt_gross < 0:
            # LTCL never gets absorbed intra-FY (it can only offset LTCG which
            # is itself negative this year, so nothing to absorb against).
            ltcl_cf.append((fy, -lt_gross))

        stcg_tax = STCG_RATE * max(0.0, net_st)
        ltcg_tax = LTCG_RATE * max(0.0, net_lt)

        out.append(FYTax(
            fy_start=fy,
            st_gross=st_gross,
            lt_gross=lt_gross,
            st_taxable=max(0.0, net_st),
            lt_taxable=max(0.0, net_lt),
            stcg_tax=stcg_tax,
            ltcg_tax=ltcg_tax,
            total_tax=stcg_tax + ltcg_tax,
            intra_fy_stcl_used_against_lt=intra_fy_stcl_used,
            cf_stcl_used=cf_stcl_used,
            cf_ltcl_used=cf_ltcl_used,
            ltcg_exemption_used=ltcg_exemption_used,
            stcl_carry_in=stcl_carry_in,
            ltcl_carry_in=ltcl_carry_in,
            stcl_carry_out=sum(amt for _, amt in stcl_cf),
            ltcl_carry_out=sum(amt for _, amt in ltcl_cf),
        ))

    return out


def value_open_positions(open_positions: dict[str, list[dict]],
                          prices_dir: Path,
                          asof: pd.Timestamp) -> tuple[float, float]:
    """Return (market_value, total_cost_basis) for open positions at `asof`."""
    mv = 0.0
    cb = 0.0
    for sym, lots in open_positions.items():
        f = prices_dir / f"{sym}_day.csv"
        if not f.exists():
            continue
        prices = pd.read_csv(f, parse_dates=["date"])
        on_or_before = prices[prices["date"] <= asof]
        if on_or_before.empty:
            continue
        close = float(on_or_before.iloc[-1]["close"])
        for lot in lots:
            mv += lot["shares_remaining"] * close
            cb += lot["shares_remaining"] * lot["cost_per_share"]
    return mv, cb


def sanity_check(equity_df: pd.DataFrame, realized: list[RealizedLot],
                  open_positions: dict[str, list[dict]],
                  prices_dir: Path) -> dict:
    """Verify realized + unrealized P&L matches equity curve total return."""
    initial_pv = float(equity_df.iloc[0]["pv"])
    final_pv = float(equity_df.iloc[-1]["pv"])
    final_date = equity_df.iloc[-1]["date"]

    realized_pnl = sum(r.gross_pnl for r in realized)
    mv, cb = value_open_positions(open_positions, prices_dir, final_date)
    unrealized_pnl = mv - cb
    total_pnl = realized_pnl + unrealized_pnl
    expected_pnl = final_pv - initial_pv
    diff = total_pnl - expected_pnl
    diff_pct = diff / abs(expected_pnl) * 100 if expected_pnl != 0 else 0.0

    return {
        "initial_pv": initial_pv,
        "final_pv": final_pv,
        "realized_pnl": realized_pnl,
        "unrealized_mv": mv,
        "unrealized_cost_basis": cb,
        "unrealized_pnl": unrealized_pnl,
        "total_pnl": total_pnl,
        "expected_pnl": expected_pnl,
        "diff": diff,
        "diff_pct": diff_pct,
    }


def fy_tax_to_dataframe(fys: Iterable[FYTax]) -> pd.DataFrame:
    rows = [{
        "fy": x.fy_label,
        "st_gross": x.st_gross,
        "lt_gross": x.lt_gross,
        "stcl_cf_in": x.stcl_carry_in,
        "ltcl_cf_in": x.ltcl_carry_in,
        "intra_stcl_used": x.intra_fy_stcl_used_against_lt,
        "cf_stcl_used": x.cf_stcl_used,
        "cf_ltcl_used": x.cf_ltcl_used,
        "ltcg_exempt_used": x.ltcg_exemption_used,
        "st_taxable": x.st_taxable,
        "lt_taxable": x.lt_taxable,
        "stcg_tax": x.stcg_tax,
        "ltcg_tax": x.ltcg_tax,
        "total_tax": x.total_tax,
        "stcl_cf_out": x.stcl_carry_out,
        "ltcl_cf_out": x.ltcl_carry_out,
    } for x in fys]
    return pd.DataFrame(rows)
