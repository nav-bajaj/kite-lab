"""Daily options report — the analytics digest generated after each EOD.

    python -m app.microstructure.daily_report --date 2026-07-30

Consumes option_minute_bars + option_greeks_minute (+ daily_sessions) and
renders a markdown report: session quality, spot day, gamma profile and
regime read, OI migration, IV/straddle ledger, depth & friction. Written
by the worker's EOD hook to <options_data_dir>/reports/<date>.md and
returned as text. This module is also the skeleton of the future morning
day-plan generator — every section here is an input to that decision.

Regime labels are HEURISTIC and say so; thresholds will be calibrated as
the day-type library grows.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text


def _resolve_url(database_url: Optional[str]) -> str:
    if database_url:
        return database_url
    from app.config import get_settings

    return get_settings().database_url


def _q(conn, sql, **p):
    return pd.read_sql(text(sql), conn, params=p)


def _ist(series):
    return pd.to_datetime(series, utc=True).dt.tz_convert("Asia/Kolkata")


def _spot_section(conn, day, out):
    spot = _q(conn, """
        select minute, open, high, low, close from option_minute_bars
        where contract_id='NIFTY_SPOT' and date(minute)=:d order by minute
    """, d=day)
    if spot.empty:
        out.append("No spot bars for this date.")
        return None
    prev = _q(conn, """
        select close from option_minute_bars
        where contract_id='NIFTY_SPOT' and date(minute) < :d
        order by minute desc limit 1
    """, d=day)
    o, h, l, c = spot.open.iloc[0], spot.high.max(), spot.low.min(), spot.close.iloc[-1]
    pc = prev.close.iloc[0] if not prev.empty else None
    out.append("## Spot day")
    gap = f"{(o - pc):+.1f} pts gap" if pc is not None else "no prior close"
    chg = f"{(c - pc):+.1f} ({(c / pc - 1) * 100:+.2f}%)" if pc is not None else "n/a"
    out.append(f"- Open {o:.1f} ({gap}) | High {h:.1f} | Low {l:.1f} | Close {c:.1f}")
    out.append(f"- Day change {chg} | Range {h - l:.1f} pts ({(h - l) / c * 100:.2f}%)")
    return {"open": o, "high": h, "low": l, "close": c, "prev_close": pc}


def _session_section(conn, day, out):
    row = _q(conn, "select stats from daily_sessions where session_date=:d", d=day)
    out.append("## Session quality")
    if row.empty:
        out.append("- No daily_sessions row (worker EOD may not have run).")
        return
    s = json.loads(row.stats.iloc[0])
    rec = s.get("recorder") or {}
    out.append(f"- Ticks recorded: {rec.get('rows_written', 0):,} | bars {s.get('bars_emitted', 0):,} "
               f"(inserted {s.get('bars_inserted', 0):,}, db_errors {s.get('db_errors', 0)}) | "
               f"widen events {s.get('widen_events', 0)}")


def _gamma_section(conn, day, spotinfo, out):
    g = _q(conn, """
        select g.minute, g.strike, g.gamma, g.underlying, b.oi_close, g.expiry
        from option_greeks_minute g
        join option_minute_bars b on b.contract_id=g.contract_id and b.minute=g.minute
        where date(g.minute)=:d and g.gamma is not null
          and g.expiry = (select min(expiry) from option_greeks_minute where date(minute)=:d)
    """, d=day)
    out.append("## Gamma profile (near expiry, measured — no dealer assumptions)")
    if g.empty:
        out.append("- No greeks rows.")
        return None
    g["hm"] = _ist(g.minute).dt.strftime("%H:%M")
    g["gex_cr"] = g.gamma * g.oi_close * g.underlying ** 2 * 0.01 / 1e7
    reads = {}
    for hm in ("10:00", "13:00", "15:15"):
        m = g[g.hm == hm]
        if m.empty:
            continue
        by_k = m.groupby("strike")["gex_cr"].sum()
        total = by_k.sum()
        conc = by_k.max() / total if total else np.nan
        reads[hm] = (total, by_k.idxmax(), conc)
        out.append(f"- {hm}: total ₹{total:,.0f}cr/1% | max-gamma strike {by_k.idxmax():.0f} "
                   f"({conc:.0%} of total)")
    if reads:
        concs = [v[2] for v in reads.values()]
        regime = ("PIN-GRAVITY (concentrating)" if concs[-1] > 0.35 and concs[-1] >= concs[0]
                  else "DIFFUSE (trend-capable)" if concs[-1] < 0.25
                  else "MIXED")
        out.append(f"- Heuristic regime read: **{regime}** (thresholds uncalibrated — {len(concs)} snapshots)")
    return reads


def _oi_migration_section(conn, day, spotinfo, out):
    df = _q(conn, """
        select b.strike, b.kind, b.minute, b.oi_close from option_minute_bars b
        where date(b.minute)=:d and b.kind in ('CE','PE')
          and b.expiry = (select min(expiry) from option_minute_bars
                          where date(minute)=:d and kind in ('CE','PE'))
    """, d=day)
    out.append("## OI migration (near expiry)")
    if df.empty or spotinfo is None:
        out.append("- insufficient data")
        return
    df["hm"] = _ist(df.minute).dt.strftime("%H:%M")
    base = df[df.hm <= "09:45"].sort_values("minute").groupby(["strike", "kind"])["oi_close"].last()
    eod = df.sort_values("minute").groupby(["strike", "kind"])["oi_close"].last()
    chg = ((eod / base) - 1).dropna()
    center = round(spotinfo["close"] / 50) * 50
    rows = []
    for k in range(int(center - 200), int(center + 250), 100):
        ce = chg.get((float(k), "CE"), np.nan)
        pe = chg.get((float(k), "PE"), np.nan)
        rows.append(f"  {k}: CE {ce:+.0%} | PE {pe:+.0%}" if np.isfinite(ce) and np.isfinite(pe) else f"  {k}: —")
    out.append("- EOD OI vs 09:45 base, strikes around close:")
    out.extend(rows)


def _iv_section(conn, day, spotinfo, out):
    iv = _q(conn, """
        select g.minute, g.strike, g.kind, g.iv, g.underlying
        from option_greeks_minute g
        where date(g.minute)=:d and g.iv is not null
          and g.expiry = (select min(expiry) from option_greeks_minute where date(minute)=:d)
    """, d=day)
    out.append("## IV & straddle ledger (near expiry)")
    if iv.empty:
        out.append("- no IV rows")
        return
    iv["hm"] = _ist(iv.minute).dt.strftime("%H:%M")
    for hm in ("09:20", "12:30", "15:15"):
        m = iv[iv.hm == hm]
        if m.empty:
            continue
        u = m.underlying.iloc[0]
        m = m.assign(dist=(m.strike - u).abs())
        atm = m[m.dist == m.dist.min()]
        out.append(f"- {hm}: forward {u:.0f} | ATM IV {atm.iv.mean() * 100:.2f}%")
    bars = _q(conn, """
        select strike, kind, close from option_minute_bars
        where date(minute)=:d and kind in ('CE','PE')
          and expiry=(select min(expiry) from option_minute_bars where date(minute)=:d and kind in ('CE','PE'))
          and minute = (select max(minute) from option_minute_bars where date(minute)=:d and contract_id='NIFTY_SPOT')
    """, d=day)
    if not bars.empty and spotinfo:
        eodp = bars.pivot_table(index="strike", columns="kind", values="close", aggfunc="first").dropna()
        if not eodp.empty:
            atm_k = eodp.index[np.abs(eodp.index - spotinfo["close"]).argmin()]
            straddle = eodp.loc[atm_k].sum()
            out.append(f"- EOD ATM straddle ({atm_k:.0f}): {straddle:.1f} pts "
                       f"= {straddle / spotinfo['close'] * 100:.2f}% implied to expiry")


def _depth_section(conn, day, spotinfo, out):
    df = _q(conn, """
        select minute, strike, avg_spread, close, avg_depth_imbalance
        from option_minute_bars
        where date(minute)=:d and source='live' and kind in ('CE','PE')
          and avg_spread is not null and abs(strike - :c) <= 100
    """, d=day, c=float(spotinfo["close"]) if spotinfo else 24000.0)
    out.append("## Depth & friction (ATM±100, live-captured)")
    if df.empty:
        out.append("- no live depth bars (replay/hist day)")
        return
    ist = _ist(df.minute)
    df["bucket"] = pd.cut(ist.dt.hour * 60 + ist.dt.minute, bins=[555, 630, 810, 870, 931],
                          labels=["open-10:30", "10:30-13:30", "13:30-14:30", "14:30-close"])
    df["pct"] = df.avg_spread / df.close.clip(lower=0.5) * 100
    agg = df.groupby("bucket", observed=True).agg(sp=("avg_spread", "mean"), pct=("pct", "mean"))
    out.append("- Spread: " + "  |  ".join(f"{b}: {r.sp:.2f}pts ({r.pct:.2f}%)" for b, r in agg.iterrows()))
    out.append(f"- Mean book imbalance {df.avg_depth_imbalance.mean():+.2f} "
               f"(structural bid-skew baseline; deviations matter, level does not)")


def generate(day: str, database_url: Optional[str] = None) -> str:
    engine = create_engine(_resolve_url(database_url))
    out = [f"# Options daily report — {day}", ""]
    with engine.connect() as conn:
        spotinfo = _spot_section(conn, day, out)
        _session_section(conn, day, out)
        if spotinfo:
            _gamma_section(conn, day, spotinfo, out)
            _oi_migration_section(conn, day, spotinfo, out)
            _iv_section(conn, day, spotinfo, out)
            _depth_section(conn, day, spotinfo, out)
            try:
                from app.microstructure.paper_straddle import compute_day, render_section

                out.extend(render_section(compute_day(conn, day)))
            except Exception as exc:
                out.append(f"## Paper straddle (MAE ledger)\n- failed: {exc}")
    engine.dispose()
    out.append("")
    out.append("*Generated by app/microstructure/daily_report.py — heuristic labels; "
               "thresholds calibrate as the day-type library grows.*")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--out", default=None, help="write markdown here as well")
    args = ap.parse_args()
    md = generate(args.date)
    if args.out:
        from pathlib import Path

        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(md)
    print(md)


if __name__ == "__main__":
    main()
