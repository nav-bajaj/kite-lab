"""COMBO Defensive portfolio orchestrator — production wiring.

50-50 L6 + OM25 v3 with priority dedup, biweekly Friday → Monday cadence,
NIFTY 100 100-DMA + 3-conf + 50% bear regime overlay.

Spec locked in tasks/MM-tuning/DD_REDUCTION_RESEARCH.md + scripts/combo_defensive.py:LOCKED.

Typical usage:
  # Backtest from 2009 (research-replication mode):
  python scripts/run_combo_defensive_portfolio.py --start 2009-09-01

  # Live production (uses nse500_data live Kite, 2020+):
  python scripts/run_combo_defensive_portfolio.py \\
      --prices-dir nse500_data --start 2020-01-01
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

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays,
)
from scripts._momentum_engine import (
    BASELINE as MM_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.combo_defensive import LOCKED, make_combo_score_fn
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.metrics_common import write_dashboard_metrics


def write_dashboard_outputs(*, dashboard_dir: Path, eq: pd.DataFrame,
                             trades: pd.DataFrame, exits: pd.DataFrame,
                             close_panel: pd.DataFrame, slippage: float) -> None:
    """Dashboard CSV schema (matches OM25 v3 / TL25 v3 / L6 v2)."""
    eq_out = eq.copy()
    eq_out["date"] = pd.to_datetime(eq_out["date"])
    eq_out = eq_out.sort_values("date").reset_index(drop=True)
    eq_out["portfolio_value"] = eq_out["pv"].astype(float)
    eq_out["drawdown"] = eq_out["portfolio_value"] / eq_out["portfolio_value"].cummax() - 1.0
    out_cols = ["date", "portfolio_value", "drawdown"]
    if "benchmark" in eq_out.columns:
        out_cols.append("benchmark")
    eq_out[out_cols].to_csv(dashboard_dir / "momentum_equity.csv", index=False)

    tr_out = trades.copy()
    tr_out["date"] = pd.to_datetime(tr_out["date"])
    keep = ["date", "symbol", "side", "shares", "price", "notional", "slippage"]
    tr_out = tr_out[[c for c in keep if c in tr_out.columns]]
    tr_out.to_csv(dashboard_dir / "momentum_trades.csv", index=False)

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
                cps = held[sym]["cost_basis"] / held[sym]["shares"]
                held[sym]["shares"] -= sh
                held[sym]["cost_basis"] -= sh * cps
                if held[sym]["shares"] <= 0:
                    held.pop(sym, None)

    last_date = pd.to_datetime(eq_out["date"].iloc[-1])
    final_pv = float(eq_out["portfolio_value"].iloc[-1])
    rows = []
    for sym, info in held.items():
        if info["shares"] <= 0: continue
        last_close = close_panel.loc[last_date, sym] if sym in close_panel.columns else None
        if last_close is None or pd.isna(last_close): continue
        notional = info["shares"] * float(last_close)
        avg_cost = info["cost_basis"] / info["shares"] if info["shares"] > 0 else 0
        pnl = (float(last_close) / avg_cost - 1) if avg_cost > 0 else 0
        days = (last_date - info["entry_date"]).days
        rows.append({
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
    holdings_df = pd.DataFrame(rows).sort_values("notional", ascending=False)
    holdings_df.to_csv(dashboard_dir / "momentum_holdings.csv", index=False)

    write_dashboard_metrics(dashboard_dir, eq_out, trades, exits)


def parse_args():
    ap = argparse.ArgumentParser(description="COMBO Defensive production pipeline")
    ap.add_argument("--prices-dir", type=Path,
                    default=ROOT / "nse500_data_merged",
                    help="Stock OHLC panel dir (use nse500_data for live)")
    ap.add_argument("--benchmark", type=Path,
                    default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--start", type=str, default="2009-09-01")
    ap.add_argument("--end", type=str, default=None)
    ap.add_argument("--regime-index", type=Path,
                    default=ROOT / LOCKED["regime_index_path"])
    ap.add_argument("--l6-membership", type=Path,
                    default=ROOT / "data/static/nse500_membership.csv",
                    help="Effective-dated membership for the L6 component; "
                         "non-existent path = legacy snapshot.")
    ap.add_argument("--om25-membership", type=Path,
                    default=ROOT / "data/static/nifty250_membership.csv",
                    help="Effective-dated membership for the OM25 component; "
                         "non-existent path = legacy snapshot.")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--slippage", type=float, default=LOCKED["slippage"])
    ap.add_argument("--output-dir", type=Path, default=None)
    ap.add_argument("--shared-state-file", type=Path, default=None,
                    help="Pickle cache from scripts/pipeline_core.py; if set, "
                         "use cached panels (Phase 2 load-once)")
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or (
        ROOT / f"data/combo_defensive_portfolios/combo_defensive_portfolio_{ts}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    dashboard_dir = out_dir / "backtests" / "baseline"
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    print(f"[run] COMBO Defensive production pipeline")
    print(f"  output → {out_dir}")
    print(f"  prices → {args.prices_dir}")
    print(f"  cadence → biweekly Fri → Mon")
    print(f"  regime → NIFTY 100 vs {LOCKED['regime_ma_window']}-DMA, "
          f"{LOCKED['regime_confirm_days']}-day confirm, "
          f"bear={LOCKED['regime_bear_exposure']*100:.0f}%")
    print(f"  start → {args.start}")

    if args.shared_state_file is not None:
        from scripts.pipeline_core import load_from_cache, describe
        state = load_from_cache(args.shared_state_file)
        print(f"[load] shared state from {args.shared_state_file.name}")
        print(f"       {describe(state)}")
        close_panel = state.close_panel
        trade_panel = state.trade_panel
        benchmark = state.benchmark
        cached_regime = state.regime_panel
    else:
        print(f"[load] panels ...")
        close_panel, trade_panel = load_price_panels(args.prices_dir)
        benchmark = load_benchmark(args.benchmark)
        cached_regime = None
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    from scripts.universe_membership import resolve_universe, union_membership_fns

    # L6 component
    print(f"[component] L6 score on NSE 500 ...")
    nse500_uni, l6_membership_fn, l6_candidate_fn = resolve_universe(
        args.l6_membership, ROOT / LOCKED["l6_universe_csv"])
    nse500_cols = [s for s in close_panel.columns if s in nse500_uni]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(LOCKED["l6_lookback_months"]),
        skip_days=LOCKED["l6_skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=LOCKED["l6_vol_floor"],
        vol_power=LOCKED["l6_vol_power"], cross_sectional_zscore=True,
        candidate_fn=l6_candidate_fn,
    )

    # OM25 component (uses OM25's internal regime tilt — separate from the
    # portfolio-level regime overlay applied later)
    print(f"[component] OM25 v3 score on Nifty 250 ...")
    nifty250_uni, om25_membership_fn, om25_candidate_fn = resolve_universe(
        args.om25_membership, ROOT / LOCKED["om25_universe_csv"])
    nifty250_cols = [s for s in close_panel.columns if s in nifty250_uni]
    om25_returns = close_panel[nifty250_cols].pct_change()
    if cached_regime is not None:
        om25_regime_for_score = cached_regime.reindex(calendar).ffill()
    else:
        om25_regime_for_score = build_regime_panel_confirmed(
            args.regime_index,
            OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
            calendar=calendar,
        )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime_for_score,
        bull_w_uc=LOCKED["om25_bull_w_uc"], bull_w_cr=LOCKED["om25_bull_w_cr"],
        bear_w_uc=LOCKED["om25_bear_w_uc"], bear_w_cr=LOCKED["om25_bear_w_cr"],
        return_filter=LOCKED["om25_return_filter"],
        lookback=LOCKED["om25_lookback"], min_obs=LOCKED["om25_min_obs"],
        candidate_fn=om25_candidate_fn,
    )

    # Combined score (priority dedup: L6 → OM25)
    print(f"[combo] priority dedup: L6 → OM25, {LOCKED['n_per_strategy']} each")
    combo_score = make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=LOCKED["n_per_strategy"],
    )

    # Portfolio-level regime overlay (NIFTY 100 100-DMA + 3-conf, bear=50%)
    print(f"[regime overlay] {args.regime_index.name}, "
          f"{LOCKED['regime_ma_window']}-DMA, "
          f"{LOCKED['regime_confirm_days']}-day confirm")
    if cached_regime is not None:
        portfolio_regime = cached_regime.reindex(calendar).ffill()
    else:
        portfolio_regime = build_regime_panel_confirmed(
            args.regime_index,
            LOCKED["regime_ma_window"], LOCKED["regime_confirm_days"],
            calendar=calendar,
        )

    # Dates: biweekly Friday entry, weekly Friday for regime/DD checks
    weekly_fri = fridays(calendar)
    entry_all = biweekly_fridays(calendar)
    start_ts = pd.Timestamp(args.start)
    end_ts = pd.Timestamp(args.end) if args.end else calendar[-1]
    weekly_filt = weekly_fri[(weekly_fri >= start_ts) & (weekly_fri <= end_ts)]
    entry_dates = entry_all[(entry_all >= start_ts) & (entry_all <= end_ts)]
    print(f"  signals: {len(entry_dates)} entry dates, {len(weekly_filt)} weekly checks")

    print(f"[backtest] running ...")
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=combo_score, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
        max_weight=LOCKED["max_weight"], slippage=args.slippage,
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
        weekly_rank_check=False,
        regime_panel=portfolio_regime,
        bear_exposure=LOCKED["regime_bear_exposure"],
        # Blend-level membership: eligible iff member of either component
        # universe on the date (see union_membership_fns docstring for the
        # per-component slot-discipline caveat).
        membership_fn=(union_membership_fns([l6_membership_fn, om25_membership_fn])
                       if (l6_membership_fn or om25_membership_fn) else None),
        min_hold_days=LOCKED["min_hold_days"],
        initial_capital=args.initial_capital,
    )

    if res is None or res["equity"].empty:
        print("  [no result — empty rebalance set]")
        return

    eq = res["equity"].copy()
    trades = res["trades"].copy()
    exits = res["exits"].copy()
    eq["date"] = pd.to_datetime(eq["date"])

    eq.to_csv(out_dir / "combo_equity.csv", index=False)
    trades.to_csv(out_dir / "combo_trades.csv", index=False)
    exits.to_csv(out_dir / "combo_exits.csv", index=False)

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
    mdd = (pv / pv.cummax()).min() - 1

    metrics = {
        "config": {k: str(v) if isinstance(v, Path) else v
                   for k, v in vars(args).items()},
        "locked": {k: v for k, v in LOCKED.items()},
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
