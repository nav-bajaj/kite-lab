"""OM25 v3 production pipeline — locked-in May 2026 stack.

Single entry point for daily/periodic OM25 operations:

  1. Build signals at biweekly Fridays from <start> to today
     using the regime-tilted UC/CR composite score
  2. Run the clean (no-lookahead) backtest with 20% drawdown stop
  3. Save equity, trades, exits, holdings, signals to the output dir

Locked-in config defaults — see scripts/om25_v3.py:LOCKED.

Typical usage:
    # Backtest from 2016 (research-replication mode):
    python scripts/run_om25_v3_portfolio.py --start 2016-01-01

    # Live production (uses indices_data/, current Kite prices):
    python scripts/run_om25_v3_portfolio.py \
        --prices-dir nse500_data \
        --regime-index indices_data/NIFTY_100.csv

    # Different cadence / universe override:
    python scripts/run_om25_v3_portfolio.py --cadence monthly \
        --universe data/static/nse500_universe.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.om25_v3 import (
    LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)


def parse_args():
    ap = argparse.ArgumentParser(description="OM25 v3 production pipeline")
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged",
                    help="Stock OHLC panel directory")
    ap.add_argument("--universe", type=Path,
                    default=ROOT / LOCKED["universe_csv"])
    ap.add_argument("--regime-index", type=Path,
                    default=ROOT / LOCKED["regime_index_path"],
                    help="Index CSV used for regime signal")
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--start", type=str, default="2016-01-01",
                    help="Backtest start date (signal entries from here)")
    ap.add_argument("--end", type=str, default=None,
                    help="Backtest end date (default: panel end)")
    ap.add_argument("--cadence", choices=["monthly", "biweekly"],
                    default=LOCKED["cadence"])
    ap.add_argument("--top-n", type=int, default=LOCKED["top_n"])
    ap.add_argument("--exit-buffer", type=int, default=LOCKED["exit_buffer"])
    ap.add_argument("--lookback", type=int, default=LOCKED["lookback"])
    ap.add_argument("--min-obs", type=int, default=LOCKED["min_obs"])
    ap.add_argument("--max-weight", type=float, default=LOCKED["max_weight"])
    ap.add_argument("--slippage", type=float, default=LOCKED["slippage"])
    ap.add_argument("--bull-w-uc", type=float, default=LOCKED["bull_w_uc"])
    ap.add_argument("--bull-w-cr", type=float, default=LOCKED["bull_w_cr"])
    ap.add_argument("--bear-w-uc", type=float, default=LOCKED["bear_w_uc"])
    ap.add_argument("--bear-w-cr", type=float, default=LOCKED["bear_w_cr"])
    ap.add_argument("--ma-window", type=int, default=LOCKED["regime_ma_window"])
    ap.add_argument("--confirm-days", type=int, default=LOCKED["regime_confirm_days"])
    ap.add_argument("--drawdown-stop", type=float, default=LOCKED["drawdown_stop_pct"],
                    help="%-from-peak drawdown stop (0 to disable)")
    ap.add_argument("--no-return-filter", action="store_true")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--output-dir", type=Path, default=None,
                    help="Output dir; default: data/om25/v3/runs/<ts>")
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or (ROOT / f"data/om25/v3/runs/{ts}")
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[run] OM25 v3 production pipeline")
    print(f"  output → {out_dir}")
    print(f"  prices → {args.prices_dir}")
    print(f"  universe → {args.universe.name}")
    print(f"  regime index → {args.regime_index.name}")
    print(f"  cadence → {args.cadence}")
    print(f"  start → {args.start}")

    print(f"[load] panels...")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()

    weekly_fri = fridays(calendar)
    if args.cadence == "biweekly":
        entry_all = biweekly_fridays(calendar)
    else:
        entry_all = monthly_first_trading_day(calendar)
    start_ts = pd.Timestamp(args.start)
    end_ts = pd.Timestamp(args.end) if args.end else calendar[-1]

    weekly_filt = weekly_fri[(weekly_fri >= start_ts) & (weekly_fri <= end_ts)]
    entry_dates = entry_all[(entry_all >= start_ts) & (entry_all <= end_ts)]

    print(f"  signals: {len(entry_dates)} entry dates, {len(weekly_filt)} weekly checks")

    universe = load_universe(args.universe)
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()
    print(f"  universe: {len(cols)} symbols")

    print(f"[regime] {args.regime_index.name}: {args.ma_window}-DMA, {args.confirm_days}-day confirm")
    regime = build_regime_panel_confirmed(
        args.regime_index, args.ma_window, args.confirm_days, calendar=calendar
    )

    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_w_uc=args.bull_w_uc, bull_w_cr=args.bull_w_cr,
        bear_w_uc=args.bear_w_uc, bear_w_cr=args.bear_w_cr,
        return_filter=not args.no_return_filter,
        lookback=args.lookback, min_obs=args.min_obs,
    )

    print(f"[backtest] running...")
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200,
        atr_20_panel=close_panel.pct_change().rolling(20).std(),
        top_n=args.top_n, exit_buffer=args.exit_buffer,
        max_weight=args.max_weight, slippage=args.slippage,
        atr_mult=0.0, atr_min_floor=args.drawdown_stop,
        use_trailing_stop=args.drawdown_stop > 0,
        use_dma_exit=False,
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

    # Compute and save signals (rank list per entry date)
    print(f"[signals] computing per-rebalance ranking ...")
    signal_rows = []
    for ed in entry_dates:
        if ed not in returns_uni.index:
            continue
        scores = score_fn(ed)
        if scores.empty:
            continue
        ranked = scores.sort_values(ascending=False).head(args.top_n + args.exit_buffer)
        rv = bool(regime.get(ed, True))
        for rank, (sym, sc) in enumerate(ranked.items(), 1):
            signal_rows.append({
                "date": ed, "rank": rank, "symbol": sym,
                "score": round(float(sc), 4),
                "regime": "bull" if rv else "bear",
            })
    signals_df = pd.DataFrame(signal_rows)

    eq.to_csv(out_dir / "om25_equity.csv", index=False)
    trades.to_csv(out_dir / "om25_trades.csv", index=False)
    exits.to_csv(out_dir / "om25_exits.csv", index=False)
    signals_df.to_csv(out_dir / "om25_signals.csv", index=False)

    # Compute headline metrics
    pv = eq.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    days = (pv.index[-1] - pv.index[0]).days
    yrs = max(days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    import math
    vol = rets.std() * math.sqrt(252)
    # CAGR-based Sharpe (rf=5%); matches research-report convention
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
