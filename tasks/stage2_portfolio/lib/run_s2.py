"""S2 (Stage 2) portfolio runner.

Weekly-rebalanced trend-following book on the NSE 500, entry-gated on a hard
Weinstein/Minervini stage-2 classification and ranked by stage QUALITY rather
than trailing return.

Exit design is deliberately gate-first: a name that leaves stage 2 stops being
scored at all, so it falls out of the ranking and is sold on the next weekly
check. The per-position stop is a separate, optional overlay - the VCP relook
(project-vcp-relook) showed that on this payoff shape the exit, not the entry,
is what decides the outcome, so it is a swept dimension and not a constant.

Runs survivorship-free by default: reconstructed NSE 500 membership from
tasks/index_reconstruction plus the ex-member price backfill.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts._clean_engine import fridays
from scripts.universe_membership import (
    load_membership, all_ever_members, make_membership_fn, make_candidate_fn)
from lib.panels import build_panels, MEMBERSHIP_RECON, MEMBERSHIP_PROD, ROOT as PROOT
from lib.stage2 import build_stage2_panels, make_s2_score, VARIANTS
from lib.s2_engine import run_s2_strategy

BENCHMARK = ROOT / "indices_data/NIFTY_500.csv"
SECTOR_CSV = ROOT / "data/static/zerodha_sectors.csv"


def load_sector_map(path: Path = SECTOR_CSV) -> dict:
    df = pd.read_csv(path)
    df = df.dropna(subset=["symbol", "zerodha_sector"])
    return dict(zip(df["symbol"].astype(str).str.strip(), df["zerodha_sector"]))


def load_benchmark(path: Path, calendar) -> pd.Series:
    df = pd.read_csv(path)
    dcol = "date" if "date" in df.columns else df.columns[0]
    df[dcol] = pd.to_datetime(df[dcol], errors="coerce").dt.normalize()
    df = df.dropna(subset=[dcol]).sort_values(dcol).drop_duplicates(dcol, keep="last")
    s = df.set_index(dcol)["close"].astype(float)
    return s.reindex(calendar).ffill()


def build_context(membership_csv: Path = MEMBERSHIP_RECON, **gate_kwargs):
    mem = load_membership(membership_csv)
    symbols = all_ever_members(mem)
    P = build_panels(symbols)
    panels = build_stage2_panels(P["close"], P["volume"], **gate_kwargs)
    return {
        "prices": P,
        "panels": panels,
        "membership_fn": make_membership_fn(mem),
        "candidate_fn": make_candidate_fn(mem),
        "benchmark": load_benchmark(BENCHMARK, P["calendar"]),
        "sector_map": load_sector_map(),
    }


def run_one(ctx, *, variant="B_quality", top_n=22, exit_buffer=10,
            stop=0.0, max_weight=0.075, slippage=0.002,
            weight_mode="trim", sector_cap=0, asymmetric_gate=False,
            hold_mode="strict", exit_confirm_weeks=1,
            start="2009-09-01", end=None, initial_capital=1_000_000,
            min_hold_days=0):
    P, panels = ctx["prices"], ctx["panels"]
    calendar = P["calendar"]

    weekly = fridays(calendar)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) if end else calendar[-1]
    sig = weekly[(weekly >= start_ts) & (weekly <= end_ts)]

    score_fn = make_s2_score(panels, candidate_fn=ctx["candidate_fn"],
                             asymmetric_gate=asymmetric_gate,
                             hold_mode=hold_mode,
                             **VARIANTS[variant])

    return run_s2_strategy(
        close_panel=P["close"], trade_panel=P["trade"], calendar=calendar,
        benchmark_aligned=ctx["benchmark"],
        signal_dates=sig, score_fn=score_fn,
        top_n=top_n, exit_buffer=exit_buffer, max_weight=max_weight,
        slippage=slippage, stop=stop, weight_mode=weight_mode,
        sector_map=ctx["sector_map"], sector_cap=sector_cap,
        min_hold_days=min_hold_days,
        exit_confirm_weeks=exit_confirm_weeks,
        membership_fn=ctx["membership_fn"],
        entry_gate=(panels["gate"]
                    if (asymmetric_gate or hold_mode != "strict") else None),
        initial_capital=initial_capital, end=end_ts,
    )


def metrics(res, benchmark=None, rf=0.0):
    if res is None:
        return None
    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    yrs = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    mdd = (pv / pv.cummax()).min() - 1
    downside = rets[rets < 0].std() * math.sqrt(252)
    trades = res["trades"]
    exits = res["exits"]
    n_years = yrs
    buys = int((trades["side"] == "BUY").sum()) if len(trades) else 0
    out = {
        "start": str(pv.index[0].date()), "end": str(pv.index[-1].date()),
        "years": round(yrs, 2),
        "cagr_pct": round(cagr * 100, 2),
        "vol_pct": round(vol * 100, 2),
        "sharpe": round((cagr - rf) / vol, 2) if vol > 0 else 0.0,
        "sortino": round((cagr - rf) / downside, 2) if downside > 0 else 0.0,
        "max_dd_pct": round(mdd * 100, 2),
        "calmar": round(cagr / abs(mdd), 2) if mdd else 0.0,
        "n_buys": buys,
        "buys_per_year": round(buys / n_years, 1) if n_years else 0,
    }
    if len(exits):
        ex = exits.dropna(subset=["pnl_pct"])
        if len(ex):
            out["win_rate_pct"] = round((ex["pnl_pct"] > 0).mean() * 100, 1)
            out["avg_win_pct"] = round(ex.loc[ex["pnl_pct"] > 0, "pnl_pct"].mean() * 100, 2)
            out["avg_loss_pct"] = round(ex.loc[ex["pnl_pct"] <= 0, "pnl_pct"].mean() * 100, 2)
            out["median_hold_days"] = int(ex["hold_days"].median())
            out["exit_mix"] = exits["reason"].value_counts().to_dict()
            out["pct_gt_100"] = round((ex["pnl_pct"] > 1.0).mean() * 100, 2)
    if benchmark is not None:
        b = benchmark.reindex(pv.index).ffill().dropna()
        if len(b) > 1:
            byrs = max((b.index[-1] - b.index[0]).days / 365.25, 1e-9)
            bcagr = (b.iloc[-1] / b.iloc[0]) ** (1 / byrs) - 1
            out["bench_cagr_pct"] = round(bcagr * 100, 2)
            out["alpha_cagr_pp"] = round((cagr - bcagr) * 100, 2)
    return out
