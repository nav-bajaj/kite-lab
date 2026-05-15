"""L6 momentum v2 production pipeline — migrated to the new engine.

Uses scripts/_momentum_engine.py (atop scripts/_clean_engine.run_strategy)
instead of the legacy scripts/backtest_momentum.py. Calibrated to within
0.4pp CAGR / 0.01 Sharpe of legacy on the same data (verified during the
MM-tuning calibration investigation).

Production config — same as current live L6 (no parameter changes):
  Universe:    NSE 500
  Score:       momentum_6m / max(realized_vol, 0.05)^1.0, cross-sectional z-score
  Cadence:     Weekly Thursday signal → Friday OHLC/4 execution
  Top-N:       24 stocks, equal-weight 1/24, max 7.5%
  Min hold:    8 days
  Slippage:    0.2% (20 bps)
  Skip days:   0
  Exit buffer: 0 (immediate exit when out of top-24)
  No DD stop, no regime overlay (those are for the Defensive sibling)

Typical usage:
  # Backtest from 2009 (research-replication mode):
  python scripts/run_l6_v2_portfolio.py --start 2009-09-01

  # Live production (uses nse500_data live Kite, 2020+):
  python scripts/run_l6_v2_portfolio.py --prices-dir nse500_data --start 2020-01-01
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._momentum_engine import (
    BASELINE, build_momentum_panels, run_momentum,
    lookback_months_to_days,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.metrics_common import write_dashboard_metrics


def write_dashboard_outputs(*, dashboard_dir: Path, eq: pd.DataFrame,
                             trades: pd.DataFrame, exits: pd.DataFrame,
                             close_panel: pd.DataFrame, slippage: float) -> None:
    """Write L6-momentum-schema CSVs for the dashboard sync_service.

    Schema (matches OM25 v3 / TL25 v3 / legacy L6):
      momentum_equity.csv   - date, portfolio_value, drawdown, benchmark
      momentum_holdings.csv - symbol, shares, avg_cost, entry_date,
                              entry_rank, holding_days, last_price,
                              pnl_pct, notional, contribution_pct
      momentum_trades.csv   - date, symbol, side, shares, price, notional, slippage
      momentum_metrics.csv  - single-row summary
    """
    eq_out = eq.copy()
    eq_out["date"] = pd.to_datetime(eq_out["date"])
    eq_out = eq_out.sort_values("date").reset_index(drop=True)
    eq_out["portfolio_value"] = eq_out["pv"].astype(float)
    eq_out["drawdown"] = eq_out["portfolio_value"] / eq_out["portfolio_value"].cummax() - 1.0
    bench_col = eq_out["benchmark"] if "benchmark" in eq_out.columns else None
    out_cols = ["date", "portfolio_value", "drawdown"]
    if bench_col is not None:
        out_cols.append("benchmark")
    eq_out[out_cols].to_csv(dashboard_dir / "momentum_equity.csv", index=False)

    tr_out = trades.copy()
    tr_out["date"] = pd.to_datetime(tr_out["date"])
    keep = ["date", "symbol", "side", "shares", "price", "notional", "slippage"]
    tr_out = tr_out[[c for c in keep if c in tr_out.columns]]
    tr_out.to_csv(dashboard_dir / "momentum_trades.csv", index=False)

    # Reconstruct current holdings from the trade ledger
    held = {}
    for _, tr in trades.sort_values("date").iterrows():
        sym = tr["symbol"]; side = tr["side"]; sh = tr["shares"]; price = tr["price"]
        if side == "BUY":
            if sym not in held:
                held[sym] = {"shares": 0, "cost_basis": 0,
                              "entry_date": tr["date"], "entry_price": price}
            held[sym]["shares"] += sh
            held[sym]["cost_basis"] += sh * price * (1 + slippage)
        else:
            if sym in held and held[sym]["shares"] > 0:
                cost_per_share = held[sym]["cost_basis"] / held[sym]["shares"]
                held[sym]["shares"] -= sh
                held[sym]["cost_basis"] -= sh * cost_per_share
                if held[sym]["shares"] <= 0:
                    held.pop(sym, None)

    last_date = pd.to_datetime(eq_out["date"].iloc[-1])
    final_pv = float(eq_out["portfolio_value"].iloc[-1])
    holdings_rows = []
    for sym, info in held.items():
        if info["shares"] <= 0: continue
        last_close = (close_panel.loc[last_date, sym]
                      if sym in close_panel.columns else None)
        if last_close is None or pd.isna(last_close): continue
        notional = info["shares"] * float(last_close)
        avg_cost = info["cost_basis"] / info["shares"] if info["shares"] > 0 else 0
        pnl = (float(last_close) / avg_cost - 1) if avg_cost > 0 else 0
        days = (last_date - info["entry_date"]).days
        holdings_rows.append({
            "symbol": sym,
            "shares": int(info["shares"]),
            "avg_cost": round(avg_cost, 4),
            "entry_date": info["entry_date"].strftime("%Y-%m-%d"),
            "entry_rank": 1,
            "holding_days": int(days),
            "last_price": round(float(last_close), 4),
            "pnl_pct": round(pnl, 6),
            "notional": round(notional, 2),
            "contribution_pct": round(notional / final_pv, 6) if final_pv > 0 else 0,
        })
    holdings_df = pd.DataFrame(holdings_rows).sort_values("notional", ascending=False)
    holdings_df.to_csv(dashboard_dir / "momentum_holdings.csv", index=False)

    write_dashboard_metrics(dashboard_dir, eq_out, trades, exits)


def parse_args():
    ap = argparse.ArgumentParser(description="L6 v2 production pipeline (new engine)")
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged",
                    help="Stock OHLC panel dir; use nse500_data for live production")
    ap.add_argument("--universe", type=Path,
                    default=ROOT / BASELINE["universe_csv"])
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--start", type=str, default="2009-09-01",
                    help="Backtest start date (signal entries from here)")
    ap.add_argument("--end", type=str, default=None,
                    help="Backtest end date (default: panel end)")
    ap.add_argument("--top-n", type=int, default=BASELINE["top_n"])
    ap.add_argument("--lookback-months", type=int, default=BASELINE["lookback_months"])
    ap.add_argument("--skip-days", type=int, default=BASELINE["skip_days"])
    ap.add_argument("--vol-floor", type=float, default=BASELINE["vol_floor"])
    ap.add_argument("--vol-power", type=float, default=BASELINE["vol_power"])
    ap.add_argument("--min-hold-days", type=int, default=BASELINE["min_hold_days"])
    ap.add_argument("--max-weight", type=float, default=BASELINE["max_weight"])
    ap.add_argument("--slippage", type=float, default=BASELINE["slippage"])
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Output dir; default: data/l6_v2_portfolios/l6_v2_portfolio_<ts>")
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or (
        ROOT / f"data/l6_v2_portfolios/l6_v2_portfolio_{ts}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    dashboard_dir = out_dir / "backtests" / "baseline"
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    print(f"[run] L6 v2 production pipeline (new engine)")
    print(f"  output → {out_dir}")
    print(f"  prices → {args.prices_dir}")
    print(f"  universe → {args.universe.name}")
    print(f"  cadence → weekly Thursday → Friday")
    print(f"  start → {args.start}")

    print(f"[load] panels ...")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    universe = load_universe(args.universe)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  universe: {len(cols)} symbols")

    print(f"[panels] building momentum + vol panels "
          f"(L{args.lookback_months}, skip={args.skip_days}) ...")
    panels = build_momentum_panels(
        close_uni,
        lookback_days=lookback_months_to_days(args.lookback_months),
        skip_days=args.skip_days,
    )

    cfg = {
        "top_n": args.top_n,
        "lookback_months": args.lookback_months,
        "skip_days": args.skip_days,
        "vol_floor": args.vol_floor,
        "vol_power": args.vol_power,
        "min_hold_days": args.min_hold_days,
        "max_weight": args.max_weight,
        "slippage": args.slippage,
    }

    print(f"[backtest] running ...")
    res = run_momentum(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
        start=args.start, end=args.end or "2099-12-31", config=cfg,
    )

    if res is None or res["equity"].empty:
        print("  [no result — empty rebalance set]")
        return

    eq = res["equity"].copy()
    trades = res["trades"].copy()
    exits = res["exits"].copy()
    eq["date"] = pd.to_datetime(eq["date"])

    # Save native L6 v2 CSVs at the run dir root
    eq.to_csv(out_dir / "l6_equity.csv", index=False)
    trades.to_csv(out_dir / "l6_trades.csv", index=False)
    exits.to_csv(out_dir / "l6_exits.csv", index=False)

    # Write dashboard-schema CSVs for sync_service
    write_dashboard_outputs(
        dashboard_dir=dashboard_dir,
        eq=eq, trades=trades, exits=exits,
        close_panel=close_panel, slippage=args.slippage,
    )

    # Headline metrics + config snapshot
    pv = eq.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    days = (pv.index[-1] - pv.index[0]).days
    yrs = max(days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0
    mdd = (pv / pv.cummax()).min() - 1

    metrics = {
        "config": {k: v for k, v in vars(args).items() if not isinstance(v, Path)},
        "result": {
            "start": str(pv.index[0].date()),
            "end": str(pv.index[-1].date()),
            "years": round(yrs, 2),
            "cagr_pct": round(cagr * 100, 2),
            "sharpe_rf5": round(sharpe, 2),
            "vol_pct": round(vol * 100, 2),
            "max_dd_pct": round(mdd * 100, 2),
            "n_buys": int((trades["side"] == "BUY").sum()),
            "n_sells": int((trades["side"] == "SELL").sum()),
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))

    print(f"\n[done]  CAGR={cagr*100:.2f}%  Sharpe={sharpe:.2f}  MaxDD={mdd*100:.2f}%")
    print(f"        Trades: {(trades['side']=='BUY').sum()} buys / {(trades['side']=='SELL').sum()} sells")
    print(f"[wrote] {out_dir}/")


if __name__ == "__main__":
    main()
