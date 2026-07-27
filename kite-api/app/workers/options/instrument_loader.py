"""NFO instrument master handling + daily contract selection.

Pure selection logic — no network in any function that tests exercise.
The live fetch path (fetch_nfo_dump / fetch_nifty_spot) is a thin wrapper
kept at the bottom, testable only by hand.

Scope (tasks/options_data/PLAN.md): NIFTY spot, current + next month
futures, and ATM +/- N strikes of CE/PE for the current + next option
expiry. ATM is anchored on spot, never on futures (options settle to spot;
near-expiry forward is within points of spot).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

UNDERLYING = "NIFTY"

# NSE index instrument for the spot feed. The token is stable and
# well-known, but select_contracts prefers a live lookup row when the
# caller provides one (see spot_row_from_nse_dump).
NIFTY_SPOT_TRADINGSYMBOL = "NIFTY 50"
NIFTY_SPOT_TOKEN_FALLBACK = 256265


@dataclass(frozen=True)
class Contract:
    contract_id: str
    instrument_token: int
    tradingsymbol: str
    kind: str  # "CE" | "PE" | "FUT" | "SPOT"
    expiry: Optional[date]
    strike: Optional[float]
    lot_size: Optional[int]
    tick_size: Optional[float]
    segment: str
    exchange: str


@dataclass
class Selection:
    trade_date: date
    spot_price: float
    atm_strike: float
    strike_step: float
    option_expiries: List[date]
    future_expiries: List[date]
    contracts: List[Contract] = field(default_factory=list)

    @property
    def tokens(self) -> List[int]:
        return [c.instrument_token for c in self.contracts]

    def summary(self) -> str:
        kinds = {}
        for c in self.contracts:
            kinds[c.kind] = kinds.get(c.kind, 0) + 1
        return (
            f"{self.trade_date} spot={self.spot_price:.2f} atm={self.atm_strike:g} "
            f"opt_expiries={[d.isoformat() for d in self.option_expiries]} "
            f"fut_expiries={[d.isoformat() for d in self.future_expiries]} "
            f"contracts={kinds} total={len(self.contracts)}"
        )


def contract_id(expiry: Optional[date], strike: Optional[float], kind: str) -> str:
    """Stable internal id — never depend on instrument_token across days."""
    if kind == "SPOT":
        return f"{UNDERLYING}_SPOT"
    assert expiry is not None
    if kind == "FUT":
        return f"{UNDERLYING}_{expiry.strftime('%Y%m%d')}_FUT"
    return f"{UNDERLYING}_{expiry.strftime('%Y%m%d')}_{strike:g}_{kind}"


def _parse_expiry(value) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()


def normalize_rows(rows: Iterable[dict]) -> List[dict]:
    """Normalize a kite.instruments() dump (live objects or JSON/CSV strings)."""
    out = []
    for r in rows:
        r = dict(r)
        r["expiry"] = _parse_expiry(r.get("expiry"))
        r["strike"] = float(r.get("strike") or 0)
        r["instrument_token"] = int(r["instrument_token"])
        out.append(r)
    return out


def _nifty_rows(rows: Sequence[dict], instrument_types: Sequence[str]) -> List[dict]:
    # name == NIFTY excludes BANKNIFTY/FINNIFTY/etc; NFO-only guards against
    # BFO/MCX rows if a caller passes a full multi-exchange dump.
    return [
        r
        for r in rows
        if r.get("name") == UNDERLYING
        and r.get("exchange") == "NFO"
        and r.get("instrument_type") in instrument_types
    ]


def upcoming_expiries(rows: Sequence[dict], instrument_types: Sequence[str], today: date, count: int) -> List[date]:
    expiries = sorted({r["expiry"] for r in _nifty_rows(rows, instrument_types) if r["expiry"] and r["expiry"] >= today})
    return expiries[:count]


def strike_grid(rows: Sequence[dict], expiry: date) -> List[float]:
    return sorted({r["strike"] for r in _nifty_rows(rows, ("CE", "PE")) if r["expiry"] == expiry})


def atm_strike(grid: Sequence[float], spot: float) -> float:
    return min(grid, key=lambda s: (abs(s - spot), s))


def window_strikes(grid: Sequence[float], atm: float, n: int) -> List[float]:
    """ATM +/- n strikes by grid position (the grid is uneven far from ATM,
    so price arithmetic would over/under-shoot; positions are exact)."""
    grid = sorted(grid)
    i = grid.index(atm)
    return grid[max(0, i - n): i + n + 1]


def strikes_to_add(current: Sequence[float], grid: Sequence[float], new_atm: float, n: int) -> List[float]:
    """Widen-only intraday adjustment: strikes inside the window around the
    drifted ATM that we are not already subscribed to. Never removes."""
    return sorted(set(window_strikes(grid, new_atm, n)) - set(current))


def _to_contract(r: dict, kind: str) -> Contract:
    return Contract(
        contract_id=contract_id(r["expiry"], r["strike"] if kind in ("CE", "PE") else None, kind),
        instrument_token=r["instrument_token"],
        tradingsymbol=r["tradingsymbol"],
        kind=kind,
        expiry=r["expiry"],
        strike=r["strike"] if kind in ("CE", "PE") else None,
        lot_size=r.get("lot_size"),
        tick_size=r.get("tick_size"),
        segment=r.get("segment", ""),
        exchange=r.get("exchange", ""),
    )


def spot_contract(spot_row: Optional[dict] = None) -> Contract:
    token = int(spot_row["instrument_token"]) if spot_row else NIFTY_SPOT_TOKEN_FALLBACK
    return Contract(
        contract_id=contract_id(None, None, "SPOT"),
        instrument_token=token,
        tradingsymbol=NIFTY_SPOT_TRADINGSYMBOL,
        kind="SPOT",
        expiry=None,
        strike=None,
        lot_size=None,
        tick_size=None,
        segment="INDICES",
        exchange="NSE",
    )


def select_contracts(
    nfo_rows: Sequence[dict],
    spot_price: float,
    today: date,
    strike_window: int = 10,
    option_expiry_count: int = 2,
    future_expiry_count: int = 2,
    spot_row: Optional[dict] = None,
) -> Selection:
    rows = normalize_rows(nfo_rows)

    opt_expiries = upcoming_expiries(rows, ("CE", "PE"), today, option_expiry_count)
    fut_expiries = upcoming_expiries(rows, ("FUT",), today, future_expiry_count)
    if not opt_expiries:
        raise ValueError("no upcoming NIFTY option expiries in dump")
    if not fut_expiries:
        raise ValueError("no upcoming NIFTY futures expiries in dump")

    # ATM off the nearest expiry's grid — it is the densest and always has
    # the 50-point spacing near the money.
    near_grid = strike_grid(rows, opt_expiries[0])
    atm = atm_strike(near_grid, spot_price)
    near_atm = window_strikes(near_grid, atm, 1)
    step = min(b - a for a, b in zip(near_atm, near_atm[1:])) if len(near_atm) > 1 else 50.0

    contracts: List[Contract] = [spot_contract(spot_row)]

    for expiry in fut_expiries:
        futs = [r for r in _nifty_rows(rows, ("FUT",)) if r["expiry"] == expiry]
        contracts.extend(_to_contract(r, "FUT") for r in futs)

    for expiry in opt_expiries:
        grid = strike_grid(rows, expiry)
        wanted = set(window_strikes(grid, atm_strike(grid, spot_price), strike_window))
        for r in _nifty_rows(rows, ("CE", "PE")):
            if r["expiry"] == expiry and r["strike"] in wanted:
                contracts.append(_to_contract(r, r["instrument_type"]))

    return Selection(
        trade_date=today,
        spot_price=spot_price,
        atm_strike=atm,
        strike_step=step,
        option_expiries=opt_expiries,
        future_expiries=fut_expiries,
        contracts=contracts,
    )


def save_selection(selection: Selection, path: Path) -> None:
    """Persist the day's token list for crash recovery (worker restart
    mid-session re-reads this instead of re-selecting off a moved spot)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "trade_date": selection.trade_date.isoformat(),
        "spot_price": selection.spot_price,
        "atm_strike": selection.atm_strike,
        "strike_step": selection.strike_step,
        "option_expiries": [d.isoformat() for d in selection.option_expiries],
        "future_expiries": [d.isoformat() for d in selection.future_expiries],
        "contracts": [
            {
                "contract_id": c.contract_id,
                "instrument_token": c.instrument_token,
                "tradingsymbol": c.tradingsymbol,
                "kind": c.kind,
                "expiry": c.expiry.isoformat() if c.expiry else None,
                "strike": c.strike,
                "lot_size": c.lot_size,
                "tick_size": c.tick_size,
                "segment": c.segment,
                "exchange": c.exchange,
            }
            for c in selection.contracts
        ],
    }
    path.write_text(json.dumps(payload, indent=1))


def load_selection(path: Path) -> Selection:
    payload = json.loads(path.read_text())
    return Selection(
        trade_date=date.fromisoformat(payload["trade_date"]),
        spot_price=payload["spot_price"],
        atm_strike=payload["atm_strike"],
        strike_step=payload["strike_step"],
        option_expiries=[date.fromisoformat(d) for d in payload["option_expiries"]],
        future_expiries=[date.fromisoformat(d) for d in payload["future_expiries"]],
        contracts=[
            Contract(
                contract_id=c["contract_id"],
                instrument_token=c["instrument_token"],
                tradingsymbol=c["tradingsymbol"],
                kind=c["kind"],
                expiry=date.fromisoformat(c["expiry"]) if c["expiry"] else None,
                strike=c["strike"],
                lot_size=c["lot_size"],
                tick_size=c["tick_size"],
                segment=c["segment"],
                exchange=c["exchange"],
            )
            for c in payload["contracts"]
        ],
    )


# --- live fetch path (no test coverage; exercised by hand / in the worker) ---

def fetch_nfo_dump(kite) -> List[dict]:
    return kite.instruments("NFO")


def fetch_nifty_spot(kite) -> dict:
    """Returns {"price": float, "row": dict-or-None} for NSE:NIFTY 50."""
    quote = kite.ltp(f"NSE:{NIFTY_SPOT_TRADINGSYMBOL}")
    entry = quote[f"NSE:{NIFTY_SPOT_TRADINGSYMBOL}"]
    return {"price": float(entry["last_price"]), "row": {"instrument_token": entry["instrument_token"]}}


def save_dump(rows: Sequence[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def _default(o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        raise TypeError(type(o))

    path.write_text(json.dumps(list(rows), default=_default))


def load_dump(path: Path) -> List[dict]:
    return normalize_rows(json.loads(path.read_text()))
