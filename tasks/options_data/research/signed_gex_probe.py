"""Stage 3 probe — sign the dealer/writer gamma book from recorded ticks.

Spec: NOTE_stage3_signed_gex.md. The pipeline's gamma profile is unsigned
(where gamma sits); this probe estimates WHO is long/short it, empirically,
from our own tick tape — never from the US CE-long/PE-short assumption.

Method per contract, per session:
  1. Aggressor classification (Lee-Ready order): a trade is a positive
     delta in cumulative `volume` between consecutive ticks, priced at the
     new `ltp`, classified against the PREVIOUS tick's book (the quote
     standing when the trade hit): at/above ask -> buyer-initiated,
     at/below bid -> seller-initiated, else mid test, else tick rule.
  2. Writer attribution per minute: pro/writer side is modeled as the
     PASSIVE side of classified flow (market-maker assumption), so the
     writer inventory delta is -net_aggressive_flow, and the minute's
     dOI splits it into opened/closed vs transferred (OI-flat) volume.
  3. Signed profile: writer_delta_k x gamma_k x F^2 aggregated by strike
     -> the day's net dealer-gamma FLOW (Rs cr / 1% move). Flow, not
     level: the standing book before our recording began is unknowable
     from ticks, and is NOT assumed. Everything here is ESTIMATED.

Outputs one JSON + printed table per day; the sign test vs the journal's
behavioural labels happens across days in RESULTS (spec step 4).

Run (worker box has ticks + DB; locally point --ticks-dir at a sample):
  python signed_gex_probe.py --date 2026-08-07 \
      --ticks-dir /data/options/ticks --out-dir signed_gex_results
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

CR = 1e7

BUY, SELL, UNCLASSIFIED = 1, -1, 0


def classify_trade(price: float, prev_bid: float, prev_ask: float,
                   prev_ltp: float) -> int:
    """Lee-Ready order against the standing quote; tick rule as fallback."""
    if prev_ask > 0 and price >= prev_ask:
        return BUY
    if prev_bid > 0 and price <= prev_bid:
        return SELL
    if prev_bid > 0 and prev_ask > prev_bid:
        mid = (prev_bid + prev_ask) / 2.0
        if price > mid:
            return BUY
        if price < mid:
            return SELL
    if prev_ltp > 0 and price != prev_ltp:
        return BUY if price > prev_ltp else SELL
    return UNCLASSIFIED


def contract_flow(df: pd.DataFrame) -> pd.DataFrame:
    """Per-minute classified flow + OI delta for ONE contract's tick tape.

    Expects recorder columns: exch_ts, ltp, volume, oi, bid1_price,
    ask1_price. Returns minute, buy_qty, sell_qty, unclassified_qty, d_oi.
    """
    df = df.sort_values(["exch_ts", "recv_ts"], kind="stable").reset_index(drop=True)
    vol = df.volume.to_numpy(dtype=np.int64)
    qty = np.diff(vol, prepend=vol[0])
    qty[qty < 0] = 0  # cumulative-volume resets (reconnects) are not trades

    price = df.ltp.to_numpy(float)
    prev_bid = np.roll(df.bid1_price.to_numpy(float), 1)
    prev_ask = np.roll(df.ask1_price.to_numpy(float), 1)
    prev_ltp = np.roll(price, 1)
    prev_bid[0] = prev_ask[0] = prev_ltp[0] = 0.0

    side = np.zeros(len(df), dtype=np.int8)
    traded = qty > 0
    for i in np.flatnonzero(traded):
        side[i] = classify_trade(price[i], prev_bid[i], prev_ask[i], prev_ltp[i])

    out = pd.DataFrame({
        "minute": pd.to_datetime(df.exch_ts).dt.floor("min"),
        "buy_qty": np.where(side == BUY, qty, 0),
        "sell_qty": np.where(side == SELL, qty, 0),
        "unclassified_qty": np.where(traded & (side == UNCLASSIFIED), qty, 0),
        "oi": df.oi.to_numpy(dtype=np.int64),
    })
    g = out.groupby("minute").agg(
        buy_qty=("buy_qty", "sum"), sell_qty=("sell_qty", "sum"),
        unclassified_qty=("unclassified_qty", "sum"), oi_close=("oi", "last"))
    g["d_oi"] = g.oi_close.diff().fillna(0).astype(np.int64)
    return g.reset_index()


@dataclass
class MinuteAttribution:
    writer_delta: int      # passive-side inventory change, -net aggressive flow
    opened_closed: int     # |d_oi| portion: contracts created/destroyed
    transferred: int       # OI-flat portion: position transfer, noisier


def attribute_minute(buy_qty: int, sell_qty: int, d_oi: int) -> MinuteAttribution:
    """Writer inventory delta for one contract-minute.

    Writers are modeled as the passive side (spec: pros provide, retail
    takes). Net aggressive buying means writers sold -> writer book grows
    short by that amount (negative delta = shorter). dOI splits the flow
    into opened/closed (clean attribution) vs transferred (ambiguous).
    """
    net_aggr = buy_qty - sell_qty
    classified = buy_qty + sell_qty
    oc = min(abs(d_oi), classified)
    return MinuteAttribution(writer_delta=-net_aggr, opened_closed=oc,
                             transferred=max(classified - oc, 0))


def day_flow(ticks: pd.DataFrame) -> pd.DataFrame:
    """Classified flow + writer attribution per contract-minute for a day."""
    frames = []
    for cid, cdf in ticks.groupby("contract_id"):
        if cid == "NIFTY_SPOT" or cdf.kind.iloc[0] not in ("CE", "PE"):
            continue
        f = contract_flow(cdf)
        f["contract_id"] = cid
        f["strike"] = cdf.strike.iloc[0]
        f["kind"] = cdf.kind.iloc[0]
        f["expiry"] = cdf.expiry.iloc[0]
        frames.append(f)
    if not frames:
        return pd.DataFrame()
    flow = pd.concat(frames, ignore_index=True)
    attr = flow.apply(lambda r: attribute_minute(int(r.buy_qty), int(r.sell_qty),
                                                 int(r.d_oi)), axis=1)
    flow["writer_delta"] = [a.writer_delta for a in attr]
    flow["opened_closed"] = [a.opened_closed for a in attr]
    flow["transferred"] = [a.transferred for a in attr]
    return flow


def signed_profile(flow: pd.DataFrame, greeks: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aggregate writer flow x gamma by strike -> signed dealer-gamma FLOW.

    greeks: strike, kind, gamma, underlying at the 15:15 snapshot (near
    expiry). writer_gamma_cr > 0 means the passive/writer book ADDED long
    gamma at that strike over the day; < 0 it got shorter gamma.
    """
    near = flow[flow.expiry == flow.expiry.min()]
    by_k = near.groupby(["strike", "kind"]).agg(
        writer_delta=("writer_delta", "sum"),
        buy_qty=("buy_qty", "sum"), sell_qty=("sell_qty", "sum"),
        unclassified_qty=("unclassified_qty", "sum"),
        opened_closed=("opened_closed", "sum"),
        transferred=("transferred", "sum"), d_oi=("d_oi", "sum")).reset_index()
    m = by_k.merge(greeks[["strike", "kind", "gamma", "underlying"]],
                   on=["strike", "kind"], how="left")
    F = float(greeks.underlying.median()) if not greeks.empty else np.nan
    m["writer_gamma_cr"] = m.writer_delta * m.gamma * F * F * 0.01 / CR

    classified = float(m.buy_qty.sum() + m.sell_qty.sum())
    total_traded = classified + float(m.unclassified_qty.sum())
    summary = {
        "net_writer_gamma_flow_cr": round(float(m.writer_gamma_cr.sum()), 1),
        "sign": ("LONG-GAMMA-BUILDING" if m.writer_gamma_cr.sum() > 0
                 else "SHORT-GAMMA-BUILDING"),
        "classified_pct": round(classified / total_traded * 100, 1) if total_traded else 0.0,
        "opened_closed_pct": round(float(m.opened_closed.sum()) / classified * 100, 1) if classified else 0.0,
        "forward": round(F, 1) if np.isfinite(F) else None,
        "estimated": True,
    }
    return m.sort_values("strike"), summary


def load_ticks(ticks_dir: Path, day: str) -> pd.DataFrame:
    files = sorted(glob.glob(str(ticks_dir / f"date={day}" / "*.parquet")))
    if not files:
        raise SystemExit(f"no tick files under {ticks_dir}/date={day}")
    return pd.concat((pd.read_parquet(f) for f in files), ignore_index=True)


def load_greeks(day: str, database_url: Optional[str]) -> pd.DataFrame:
    from sqlalchemy import create_engine, text
    url = database_url or os.environ.get("DATABASE_PUBLIC_URL") or os.environ["DATABASE_URL"]
    engine = create_engine(url)
    with engine.connect() as conn:
        g = pd.read_sql(text("""
            select g.strike, g.kind, g.gamma, g.underlying
            from option_greeks_minute g
            where date(g.minute)=:d and g.gamma is not null
              and g.expiry=(select min(expiry) from option_greeks_minute where date(minute)=:d)
              and to_char(g.minute at time zone 'Asia/Kolkata', 'HH24:MI')='15:15'
        """), conn, params={"d": day})
    engine.dispose()
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--ticks-dir", default="/data/options/ticks")
    ap.add_argument("--database-url", default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    ticks = load_ticks(Path(args.ticks_dir), args.date)
    flow = day_flow(ticks)
    if flow.empty:
        raise SystemExit("no option contracts in tick data")
    greeks = load_greeks(args.date, args.database_url)
    profile, summary = signed_profile(flow, greeks)

    print(f"# Signed dealer-gamma probe — {args.date} (ESTIMATED, flow-based)")
    print(f"net writer gamma flow: {summary['net_writer_gamma_flow_cr']:+,.1f} cr/1% "
          f"-> {summary['sign']}")
    print(f"classified {summary['classified_pct']}% of traded qty | "
          f"opened/closed share {summary['opened_closed_pct']}%")
    cols = ["strike", "kind", "buy_qty", "sell_qty", "d_oi", "writer_delta", "writer_gamma_cr"]
    print(profile[cols].to_string(index=False))

    if args.out_dir:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        payload = {"date": args.date, "summary": summary,
                   "by_strike": profile[cols].to_dict(orient="records")}
        (out / f"{args.date}.json").write_text(json.dumps(payload, indent=2, default=str))
        print(f"\nwrote {out / f'{args.date}.json'}")


if __name__ == "__main__":
    main()
