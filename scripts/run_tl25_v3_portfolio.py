"""TL25 v3 production pipeline — locked-in May 2026 OOS retune stack.

Single entry point for daily/periodic TL25 operations:

  1. Build eligibility + 3-component trend panels (Persistence, Drawdown, Momentum)
  2. Score with locked weights 0.40 / 0.20 / 0.40 (Offensive P+M)
  3. Run the clean (no-lookahead) backtest with biweekly entry + weekly rank-exit
     + 20% drawdown stop
  4. Save equity, trades, exits, holdings, signals to the output dir

Locked-in config defaults — see scripts/tl25_v3.py:V3_LOCKED.

Typical usage:
    # Backtest from 2017 (OOS-only replication mode):
    python scripts/run_tl25_v3_portfolio.py --start 2017-01-01

    # Live production (uses nse500_data/, current Kite prices, 2020+):
    python scripts/run_tl25_v3_portfolio.py \
        --prices-dir nse500_data \
        --start 2020-01-01
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

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score, V3_LOCKED
from scripts.metrics_common import write_dashboard_metrics


def write_dashboard_outputs(*, dashboard_dir: Path, eq: pd.DataFrame,
                             trades: pd.DataFrame, exits: pd.DataFrame,
                             close_panel: pd.DataFrame, slippage: float) -> None:
    """Write L6-momentum-schema CSVs that kite-api sync_service can read.

    Schema match required by app/services/sync_service.py:
      - momentum_equity.csv:    date, portfolio_value, benchmark, drawdown
      - momentum_holdings.csv:  symbol, shares, avg_cost, entry_date,
                                entry_rank, holding_days, last_price,
                                pnl_pct, notional, contribution_pct
      - momentum_trades.csv:    date, symbol, side, shares, price,
                                notional, slippage
      - momentum_metrics.csv:   single-row with cagr, total_return,
                                max_drawdown, sharpe_ratio, etc.
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

    held = {}
    for _, tr in trades.sort_values("date").iterrows():
        sym = tr["symbol"]
        side = tr["side"]
        sh = tr["shares"]
        price = tr["price"]
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
        if info["shares"] <= 0:
            continue
        last_close = (close_panel.loc[last_date, sym]
                      if sym in close_panel.columns else None)
        if last_close is None or pd.isna(last_close):
            continue
        notional = info["shares"] * float(last_close)
        avg_cost = info["cost_basis"] / info["shares"] if info["shares"] > 0 else 0
        pnl = (float(last_close) / avg_cost - 1) if avg_cost > 0 else 0
        days = (last_date - info["entry_date"]).days
        holdings_rows.append({
            "symbol": sym,
            "shares": int(info["shares"]),
            "avg_cost": round(avg_cost, 4),
            "entry_date": info["entry_date"].strftime("%Y-%m-%d"),
            "entry_rank": 1,  # not tracked; placeholder
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
    ap = argparse.ArgumentParser(description="TL25 v3 production pipeline")
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged",
                    help="Stock OHLC panel directory (use nse500_data for live)")
    ap.add_argument("--universe", type=Path,
                    default=ROOT / V3_LOCKED["universe_csv"])
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--start", type=str, default="2009-09-01",
                    help="Backtest start date (signal entries from here)")
    ap.add_argument("--end", type=str, default=None,
                    help="Backtest end date (default: panel end)")
    ap.add_argument("--cadence", choices=["biweekly"],
                    default=V3_LOCKED["cadence"],
                    help="TL25 v3 only supports biweekly entry")
    ap.add_argument("--top-n", type=int, default=V3_LOCKED["top_n"])
    ap.add_argument("--exit-buffer", type=int, default=V3_LOCKED["exit_buffer"])
    ap.add_argument("--max-weight", type=float, default=V3_LOCKED["max_weight"])
    ap.add_argument("--slippage", type=float, default=V3_LOCKED["slippage"])
    ap.add_argument("--w-persistence", type=float, default=V3_LOCKED["w_persistence"])
    ap.add_argument("--w-drawdown", type=float, default=V3_LOCKED["w_drawdown"])
    ap.add_argument("--w-momentum", type=float, default=V3_LOCKED["w_momentum"])
    ap.add_argument("--persistence-window", type=int, default=V3_LOCKED["persistence_window"])
    ap.add_argument("--drawdown-window", type=int, default=V3_LOCKED["drawdown_window"])
    ap.add_argument("--momentum-window", type=int, default=V3_LOCKED["momentum_window"])
    ap.add_argument("--drawdown-stop", type=float, default=V3_LOCKED["atr_min_floor"],
                    help="%-from-peak drawdown stop (0 to disable)")
    ap.add_argument("--no-weekly-rank-exit", action="store_true",
                    help="Disable weekly rank-exit (default ON in V3 LOCKED)")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Output dir; default: data/tl25_v3_portfolios/tl25_v3_portfolio_<ts>")
    ap.add_argument("--shared-state-file", type=Path, default=None,
                    help="Pickle cache from scripts/pipeline_core.py; if set, "
                         "use cached close/trade/benchmark panels (Phase 2 load-once)")
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or (
        ROOT / f"data/tl25_v3_portfolios/tl25_v3_portfolio_{ts}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    dashboard_dir = out_dir / "backtests" / "baseline"
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    weekly_rank_check = not args.no_weekly_rank_exit

    print(f"[run] TL25 v3 production pipeline")
    print(f"  output → {out_dir}")
    print(f"  prices → {args.prices_dir}")
    print(f"  universe → {args.universe.name}")
    print(f"  cadence → {args.cadence} entry + weekly DD-stop"
          + (" + weekly rank-exit" if weekly_rank_check else ""))
    print(f"  weights → P={args.w_persistence} DD={args.w_drawdown} M={args.w_momentum}")
    print(f"  start → {args.start}")

    if args.shared_state_file is not None:
        from scripts.pipeline_core import load_from_cache, describe
        state = load_from_cache(args.shared_state_file)
        print(f"[load] shared state from {args.shared_state_file.name}")
        print(f"       {describe(state)}")
        close_panel = state.close_panel
        trade_panel = state.trade_panel
        benchmark = state.benchmark
    else:
        print(f"[load] panels...")
        close_panel, trade_panel = load_price_panels(args.prices_dir)
        benchmark = load_benchmark(args.benchmark)
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_panel = close_panel.pct_change().rolling(20).std()

    weekly_fri = fridays(calendar)
    entry_all = biweekly_fridays(calendar)
    start_ts = pd.Timestamp(args.start)
    end_ts = pd.Timestamp(args.end) if args.end else calendar[-1]

    weekly_filt = weekly_fri[(weekly_fri >= start_ts) & (weekly_fri <= end_ts)]
    entry_dates = entry_all[(entry_all >= start_ts) & (entry_all <= end_ts)]

    print(f"  signals: {len(entry_dates)} entry dates, {len(weekly_filt)} weekly checks")

    universe = load_universe(args.universe)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  universe: {len(cols)} symbols")

    print(f"[panels] building TL25 panels "
          f"(persistence {args.persistence_window}d, drawdown {args.drawdown_window}d², "
          f"momentum {args.momentum_window}d) ...")
    panels = build_tl25_panels(
        close_uni,
        dma_short=V3_LOCKED["dma_short"],
        dma_long=V3_LOCKED["dma_long"],
        dma_persist_ref=V3_LOCKED["dma_persist_ref"],
        persistence_window=args.persistence_window,
        drawdown_window=args.drawdown_window,
        drawdown_concavity=V3_LOCKED["drawdown_concavity"],
        momentum_window=args.momentum_window,
    )
    score_fn = make_tl25_score(
        panels,
        w_persistence=args.w_persistence,
        w_drawdown=args.w_drawdown,
        w_momentum=args.w_momentum,
    )

    print(f"[backtest] running ...")
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_panel,
        top_n=args.top_n, exit_buffer=args.exit_buffer,
        max_weight=args.max_weight, slippage=args.slippage,
        atr_mult=0.0, atr_min_floor=args.drawdown_stop,
        use_trailing_stop=args.drawdown_stop > 0,
        use_dma_exit=False,
        weekly_rank_check=weekly_rank_check,
        regime_panel=None, bear_exposure=0.0,
        initial_capital=args.initial_capital,
    )

    if res is None:
        print("  [no result — empty rebalance set]")
        return

    eq = res["equity"].copy()
    trades = res["trades"].copy()
    exits = res["exits"].copy()
    eq["date"] = pd.to_datetime(eq["date"])

    print(f"[signals] computing per-rebalance ranking ...")
    signal_rows = []
    for ed in entry_dates:
        if ed not in panels["eligibility"].index:
            continue
        scores = score_fn(ed)
        if scores.empty:
            continue
        ranked = scores.sort_values(ascending=False).head(args.top_n + args.exit_buffer)
        for rank, (sym, sc) in enumerate(ranked.items(), 1):
            signal_rows.append({
                "date": ed, "rank": rank, "symbol": sym,
                "score": round(float(sc), 4),
            })
    signals_df = pd.DataFrame(signal_rows)

    eq.to_csv(out_dir / "tl25_equity.csv", index=False)
    trades.to_csv(out_dir / "tl25_trades.csv", index=False)
    exits.to_csv(out_dir / "tl25_exits.csv", index=False)
    signals_df.to_csv(out_dir / "tl25_signals.csv", index=False)

    write_dashboard_outputs(
        dashboard_dir=dashboard_dir,
        eq=eq, trades=trades, exits=exits,
        close_panel=close_panel, slippage=args.slippage,
    )

    pv = eq.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    days = (pv.index[-1] - pv.index[0]).days
    yrs = max(days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0
    cum = pv / pv.cummax()
    mdd = cum.min() - 1

    metrics = {
        "config": {k: v for k, v in vars(args).items() if not isinstance(v, Path)},
        "result": {
            "start": str(pv.index[0].date()),
            "end": str(pv.index[-1].date()),
            "years": round(yrs, 2),
            "start_value": round(float(pv.iloc[0]), 2),
            "end_value": round(float(pv.iloc[-1]), 2),
            "total_return_pct": round((pv.iloc[-1] / pv.iloc[0] - 1) * 100, 2),
            "cagr_pct": round(cagr * 100, 2),
            "sharpe_rf5": round(sharpe, 2),
            "vol_pct": round(vol * 100, 2),
            "max_dd_pct": round(mdd * 100, 2),
            "n_buys": int((trades["side"] == "BUY").sum()),
            "n_sells": int((trades["side"] == "SELL").sum()),
            "n_signals": len(signals_df),
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))

    print(f"\n[done]  CAGR={cagr*100:.2f}%  Sharpe={sharpe:.2f}  MaxDD={mdd*100:.2f}%")
    print(f"        Trades: {(trades['side']=='BUY').sum()} buys / {(trades['side']=='SELL').sum()} sells")
    print(f"        Signals: {len(signals_df)} rows over {len(entry_dates)} rebalance dates")
    print(f"[wrote] {out_dir}/")


if __name__ == "__main__":
    main()
