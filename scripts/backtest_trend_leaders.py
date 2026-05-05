"""
Backtest engine for Trend Leaders 20 — trend-following portfolio

Dual-frequency rebalance:
  - Monthly entry: select top-N stocks by Trend Quality Score
  - Weekly exit: sell if Close < 200 DMA

Variants:
  - base: monthly entry + weekly exit, no market filter
  - market_filter: + Nifty 500 < 200 DMA caps exposure at 50%
  - monthly_only: monthly entry and exit, no weekly checks

Usage:
    python scripts/backtest_trend_leaders.py \
      --signals data/trend_leaders/signals/trend_leaders_signals.csv \
      --prices-dir nse500_data \
      --benchmark data/benchmarks/nifty100.csv \
      --output-dir data/trend_leaders/backtests/base \
      --variant base
"""

import argparse
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.backtest_momentum import load_price_panels, load_benchmark, map_signal_to_trade


# ---------------------------------------------------------------------------
# Signal loading
# ---------------------------------------------------------------------------

def load_trend_signals(path: Path, top_n: int, exit_buffer: int = 10):
    """Load trend leader signals.

    Returns:
        entry_signals: {signal_date: [top_n symbols]} for entries
        rank_map: {signal_date: {symbol: rank}} for exit hysteresis
    """
    df = pd.read_csv(path, parse_dates=["date"])

    # Entry signals: top-N per date
    entry_df = df[df["rank"] <= top_n]
    entry_signals = entry_df.groupby("date")["symbol"].apply(list).to_dict()
    entry_signals = {pd.Timestamp(k): v for k, v in entry_signals.items()}

    # Rank map: all ranked stocks (for exit hysteresis)
    rank_map = {}
    for date, group in df.groupby("date"):
        rank_map[pd.Timestamp(date)] = dict(zip(group["symbol"], group["rank"]))

    return entry_signals, rank_map


# ---------------------------------------------------------------------------
# Date utilities
# ---------------------------------------------------------------------------

def derive_weekly_exit_dates(calendar: pd.DatetimeIndex) -> set:
    """Last trading day of each week (Friday-anchored)."""
    cal_series = pd.Series(index=calendar, data=calendar)
    weekly_last = cal_series.resample("W-FRI").last().dropna()
    return set(pd.Timestamp(d) for d in weekly_last.values)


def derive_monthly_entry_dates_from_signals(signal_dates: list, calendar: pd.DatetimeIndex) -> dict:
    """Map signal dates to trade execution dates (next trading day).

    Returns {trade_date: signal_date}.
    """
    mapping = {}
    for signal_date in signal_dates:
        trade_date = map_signal_to_trade(signal_date, calendar)
        if trade_date is not None:
            mapping[pd.Timestamp(trade_date)] = pd.Timestamp(signal_date)
    return mapping


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def run_backtest(
    prices_dir: Path,
    signals_path: Path,
    benchmark_path: Path,
    output_dir: Path,
    initial_capital: float = 1_000_000,
    top_n: int = 20,
    exit_buffer: int = 10,
    max_weight: float = 0.075,
    slippage: float = 0.002,
    variant: str = "base",
    market_filter_index_path: Path = None,
    market_filter_max_exposure: float = 0.50,
    whole_shares: bool = True,
    min_hold_days: int = 0,
    unified_rebalance: bool = False,
    hold_signals_path: Path = None,
):
    exit_threshold = top_n + exit_buffer  # e.g., 30

    # Load data
    print("Loading price panels...")
    close_panel, trade_panel = load_price_panels(prices_dir)
    calendar = close_panel.index

    print("Loading signals...")
    entry_signals, entry_rank_map = load_trend_signals(signals_path, top_n, exit_buffer)

    # Hold signals: used for exit decisions (rank-based exit hysteresis)
    # If not provided, use same as entry signals
    if hold_signals_path and hold_signals_path.exists():
        print(f"Loading separate hold signals from {hold_signals_path}...")
        _, rank_map = load_trend_signals(hold_signals_path, top_n, exit_buffer)
    else:
        rank_map = entry_rank_map

    print("Loading benchmark...")
    benchmark = load_benchmark(benchmark_path)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    # Map signal dates to trade dates
    entry_schedule = derive_monthly_entry_dates_from_signals(
        sorted(entry_signals.keys()), calendar
    )
    monthly_trade_dates = set(entry_schedule.keys())

    # Weekly exit dates
    weekly_exit_dates = derive_weekly_exit_dates(calendar)

    # Pre-compute 200 DMA for weekly exit checks (skip if unified rebalance)
    sma_200_panel = None
    if not unified_rebalance:
        print("Pre-computing 200 DMA for exit checks...")
        sma_200_panel = close_panel.rolling(window=200, min_periods=200).mean()

    # Market filter: load index data and compute its 200 DMA
    mf_close = None
    mf_sma_200 = None
    if variant == "market_filter" and market_filter_index_path is not None:
        print(f"Loading market filter index from {market_filter_index_path}...")
        mf_df = pd.read_csv(market_filter_index_path, parse_dates=["date"])
        mf_df = mf_df.sort_values("date").set_index("date")
        mf_close = mf_df["close"].reindex(calendar).ffill()
        mf_sma_200 = mf_close.rolling(window=200, min_periods=200).mean()

    # Filter calendar to start from first trade date
    first_trade_date = min(monthly_trade_dates) if monthly_trade_dates else calendar[0]
    active_calendar = calendar[calendar >= first_trade_date]
    print(f"Backtest period: {active_calendar[0].date()} to {active_calendar[-1].date()} "
          f"({len(active_calendar)} trading days)")
    print(f"Rebalance dates: {len(monthly_trade_dates)}")
    print(f"Variant: {variant}" + (f" | min_hold_days={min_hold_days}" if min_hold_days > 0 else "")
          + (" | unified_rebalance" if unified_rebalance else ""))

    # State
    holdings = {}       # symbol -> shares
    cost_basis = {}     # symbol -> total cost
    entry_meta = {}     # symbol -> {date, rank, signal_date}
    cash = initial_capital
    trade_records = []
    equity_records = []
    turnover_records = []
    exit_records = []
    holdings_snapshots = []
    peak_equity = initial_capital
    last_prices = {}

    def get_price(panel, date, symbol):
        """Get price from panel with fallback to last known price."""
        price = panel.loc[date, symbol] if symbol in panel.columns else np.nan
        if pd.isna(price):
            price = last_prices.get(symbol, np.nan)
        return price

    def execute_sell(symbol, date, reason):
        """Sell entire position in symbol. Returns proceeds."""
        nonlocal cash
        shares = holdings.pop(symbol, 0)
        if shares == 0:
            return 0

        price = get_price(trade_panel, date, symbol)
        if pd.isna(price) or price <= 0:
            holdings[symbol] = shares  # Put back if no price
            return 0

        proceeds = shares * price * (1 - slippage)
        cash += proceeds
        notional = shares * price
        cost = notional * slippage

        # Exit record for P&L tracking
        avg_cost = cost_basis.get(symbol, 0) / shares if shares else 0
        meta = entry_meta.pop(symbol, {"date": date, "rank": None, "signal_date": None})
        pnl_pct = price / avg_cost - 1 if avg_cost > 0 else None
        exit_records.append({
            "symbol": symbol,
            "entry_date": meta.get("date"),
            "exit_date": date,
            "entry_rank": meta.get("rank"),
            "holding_days": (date - meta["date"]).days if meta.get("date") else None,
            "pnl_pct": pnl_pct,
            "reason": reason,
        })

        cost_basis.pop(symbol, None)

        trade_records.append({
            "date": date,
            "symbol": symbol,
            "side": "SELL",
            "shares": shares,
            "price": price,
            "notional": notional,
            "slippage": cost,
            "reason": reason,
        })

        return proceeds

    def execute_buy(symbol, target_notional, date, rank=None, signal_date=None):
        """Buy shares of symbol up to target_notional."""
        nonlocal cash

        price = get_price(trade_panel, date, symbol)
        if pd.isna(price) or price <= 0:
            return 0

        if whole_shares:
            shares = math.floor(target_notional / (price * (1 + slippage)))
        else:
            shares = target_notional / (price * (1 + slippage))

        if shares < 1 and whole_shares:
            return 0

        cost = shares * price * (1 + slippage)
        if cost > cash + 0.01:
            if whole_shares:
                shares = math.floor(cash / (price * (1 + slippage)))
            else:
                shares = cash / (price * (1 + slippage))
            cost = shares * price * (1 + slippage)

        if shares < 1 and whole_shares:
            return 0

        holdings[symbol] = holdings.get(symbol, 0) + shares
        cost_basis[symbol] = cost_basis.get(symbol, 0) + cost
        if symbol not in entry_meta:
            entry_meta[symbol] = {"date": date, "rank": rank, "signal_date": signal_date}
        cash -= cost

        notional = shares * price
        trade_records.append({
            "date": date,
            "symbol": symbol,
            "side": "BUY",
            "shares": shares,
            "price": price,
            "notional": notional,
            "slippage": shares * price * slippage,
            "reason": "entry",
        })

        return cost

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------
    for date in active_calendar:
        close_row = close_panel.loc[date]

        # Update last known prices
        for sym in holdings:
            p = close_row.get(sym, np.nan)
            if not pd.isna(p):
                last_prices[sym] = p

        # 1. Mark-to-market
        portfolio_value = cash
        for sym, shares in holdings.items():
            price = close_row.get(sym, last_prices.get(sym, 0))
            if pd.isna(price):
                price = last_prices.get(sym, 0)
            portfolio_value += shares * price

        peak_equity = max(peak_equity, portfolio_value)
        drawdown = portfolio_value / peak_equity - 1 if peak_equity > 0 else 0
        cash_pct = cash / portfolio_value if portfolio_value > 0 else 1.0

        # 2. Record equity
        equity_records.append({
            "date": date,
            "portfolio_value": portfolio_value,
            "cash": cash,
            "invested": portfolio_value - cash,
            "cash_pct": cash_pct,
            "holdings_count": len(holdings),
            "benchmark": benchmark_aligned.get(date, np.nan),
            "drawdown": drawdown,
        })

        # 3. Weekly exit check (BEFORE monthly entry if same day)
        #    Skip if unified_rebalance (exits handled at rebalance via rank drop)
        if date in weekly_exit_dates and variant != "monthly_only" and not unified_rebalance:
            exits_this_week = []
            for sym in list(holdings.keys()):
                # Min hold check
                if min_hold_days > 0:
                    entry_date = entry_meta.get(sym, {}).get("date")
                    if entry_date and (date - entry_date).days < min_hold_days:
                        continue

                sym_close = close_row.get(sym, np.nan)
                sym_sma200 = sma_200_panel.loc[date, sym] if sym in sma_200_panel.columns else np.nan

                if pd.isna(sym_close) or pd.isna(sym_sma200):
                    continue

                if sym_close < sym_sma200:
                    exits_this_week.append(sym)

            for sym in exits_this_week:
                execute_sell(sym, date, reason="weekly_exit")

        # 4. Monthly entry/rebalance
        if date in monthly_trade_dates:
            signal_date = entry_schedule[date]
            entry_symbols = entry_signals.get(signal_date, [])[:top_n]
            current_ranks = rank_map.get(signal_date, {})

            # Determine market filter exposure
            max_exposure = 1.0
            if variant == "market_filter" and mf_close is not None and mf_sma_200 is not None:
                idx_close = mf_close.get(date, np.nan)
                idx_sma = mf_sma_200.get(date, np.nan)
                if not pd.isna(idx_close) and not pd.isna(idx_sma):
                    if idx_close < idx_sma:
                        max_exposure = market_filter_max_exposure

            # Exit hysteresis: sell holdings ranked > exit_threshold (or unranked)
            for sym in list(holdings.keys()):
                # Min hold check
                if min_hold_days > 0:
                    entry_date = entry_meta.get(sym, {}).get("date")
                    if entry_date and (date - entry_date).days < min_hold_days:
                        continue

                sym_rank = current_ranks.get(sym, float("inf"))
                if sym_rank > exit_threshold:
                    execute_sell(sym, date, reason="monthly_exit")

            # Determine how many slots are open
            open_slots = max(0, top_n - len(holdings))

            # Fill open slots from entry_symbols (ranked 1 to top_n)
            entrants = [sym for sym in entry_symbols if sym not in holdings][:open_slots]

            if entrants:
                # Recalculate portfolio value after sells
                pv_after_sells = cash
                for sym, shares in holdings.items():
                    price = close_row.get(sym, last_prices.get(sym, 0))
                    if pd.isna(price):
                        price = last_prices.get(sym, 0)
                    pv_after_sells += shares * price

                # Target weight for new entrants: equal share of portfolio
                n_total = len(holdings) + len(entrants)
                raw_weight = 1.0 / n_total if n_total > 0 else 0
                stock_weight = min(raw_weight, max_weight) * max_exposure
                target_per_stock = pv_after_sells * stock_weight

                for sym in entrants:
                    alloc = min(target_per_stock, cash * 0.99)
                    if alloc <= 0:
                        break
                    rank_in_signal = current_ranks.get(sym, None)
                    execute_buy(sym, alloc, date, rank=rank_in_signal, signal_date=signal_date)

            # Record turnover
            buy_notional = sum(t["notional"] for t in trade_records
                             if t["date"] == date and t["side"] == "BUY")
            sell_notional = sum(t["notional"] for t in trade_records
                              if t["date"] == date and t["side"] == "SELL")
            total_turnover = buy_notional + sell_notional

            # Holdings snapshot
            snapshot_rows = []
            for sym, shares in sorted(holdings.items()):
                price = close_row.get(sym, last_prices.get(sym, 0))
                value = shares * price if not pd.isna(price) else 0
                meta = entry_meta.get(sym, {})
                snapshot_rows.append({
                    "date": date,
                    "symbol": sym,
                    "shares": shares,
                    "price": price,
                    "value": value,
                    "weight": value / portfolio_value if portfolio_value > 0 else 0,
                    "cost_basis": cost_basis.get(sym, 0),
                    "entry_date": meta.get("date"),
                    "rank": meta.get("rank"),
                })
            holdings_snapshots.extend(snapshot_rows)

            turnover_records.append({
                "date": date,
                "signal_date": signal_date,
                "buy_notional": buy_notional,
                "sell_notional": sell_notional,
                "turnover": total_turnover,
                "turnover_pct": total_turnover / portfolio_value if portfolio_value > 0 else 0,
                "holdings_count": len(holdings),
                "max_exposure": max_exposure,
            })

        # Also record weekly exit turnover
        elif date in weekly_exit_dates and variant != "monthly_only":
            sell_notional = sum(t["notional"] for t in trade_records
                              if t["date"] == date and t["side"] == "SELL")
            if sell_notional > 0:
                turnover_records.append({
                    "date": date,
                    "signal_date": None,
                    "buy_notional": 0,
                    "sell_notional": sell_notional,
                    "turnover": sell_notional,
                    "turnover_pct": sell_notional / portfolio_value if portfolio_value > 0 else 0,
                    "holdings_count": len(holdings),
                    "max_exposure": None,
                })

    # -----------------------------------------------------------------------
    # Build output DataFrames
    # -----------------------------------------------------------------------
    equity_df = pd.DataFrame(equity_records)
    trades_df = pd.DataFrame(trade_records)
    turnover_df = pd.DataFrame(turnover_records)
    holdings_df = pd.DataFrame(holdings_snapshots)

    # -----------------------------------------------------------------------
    # Compute metrics
    # -----------------------------------------------------------------------
    metrics = compute_metrics(equity_df, trades_df, turnover_df, exit_records,
                              initial_capital, top_n)

    # -----------------------------------------------------------------------
    # Save outputs
    # -----------------------------------------------------------------------
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    equity_df.to_csv(output_dir / "tl20_equity.csv", index=False)
    trades_df.to_csv(output_dir / "tl20_trades.csv", index=False)
    turnover_df.to_csv(output_dir / "tl20_turnover.csv", index=False)
    holdings_df.to_csv(output_dir / "tl20_holdings.csv", index=False)
    metrics.to_csv(output_dir / "tl20_metrics.csv", index=False)

    print(f"\nResults saved to {output_dir}/")
    print(f"  tl20_equity.csv   ({len(equity_df)} rows)")
    print(f"  tl20_trades.csv   ({len(trades_df)} rows)")
    print(f"  tl20_turnover.csv ({len(turnover_df)} rows)")
    print(f"  tl20_holdings.csv ({len(holdings_df)} rows)")
    print(f"  tl20_metrics.csv")

    # Print summary
    if not metrics.empty:
        m = metrics.iloc[0]
        print(f"\n=== Performance Summary ({variant}) ===")
        print(f"Period: {m.get('start', '?')} to {m.get('end', '?')}")
        print(f"Total Return: {m.get('total_return', 0):.1%}")
        print(f"CAGR: {m.get('cagr', 0):.1%}")
        print(f"Max Drawdown: {m.get('max_drawdown', 0):.1%}")
        print(f"Sharpe Ratio: {m.get('sharpe_ratio', 0):.2f}")
        print(f"Sortino Ratio: {m.get('sortino_ratio', 0):.2f}")
        print(f"Calmar Ratio: {m.get('calmar_ratio', 0):.2f}")
        print(f"Annualized Turnover: {m.get('annualized_turnover', 0):.0%}")
        print(f"Hit Rate: {m.get('hit_rate_overall', 0):.1%}")
        print(f"Avg Holdings: {m.get('avg_holdings_count', 0):.1f}")
        print(f"Avg Cash %: {m.get('avg_cash_pct', 0):.1%}")
        print(f"Total Trades: {int(m.get('trades_total', 0))}")
        print(f"Weekly Exits: {int(m.get('weekly_exits', 0))}")
        print(f"Monthly Exits: {int(m.get('monthly_exits', 0))}")

    return metrics


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_metrics(equity_df, trades_df, turnover_df, exit_records,
                    initial_capital, top_n):
    """Compute comprehensive performance metrics."""
    if equity_df.empty:
        return pd.DataFrame()

    start_val = equity_df["portfolio_value"].iloc[0]
    end_val = equity_df["portfolio_value"].iloc[-1]
    total_return = end_val / start_val - 1

    start_date = equity_df["date"].iloc[0]
    end_date = equity_df["date"].iloc[-1]
    if isinstance(start_date, str):
        start_date = pd.Timestamp(start_date)
        end_date = pd.Timestamp(end_date)
    years = max((end_date - start_date).days / 365.25, 1e-6)
    cagr = (1 + total_return) ** (1 / years) - 1

    # Volatility and risk metrics
    daily_returns = equity_df["portfolio_value"].pct_change().dropna()
    ann_vol = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0
    sharpe = cagr / ann_vol if ann_vol > 0 else 0

    downside_returns = daily_returns[daily_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 1 else 0
    sortino = cagr / downside_vol if downside_vol > 0 else 0

    max_dd = equity_df["drawdown"].min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else 0

    # Drawdown duration
    longest_dd = 0
    current_dd = 0
    for val in equity_df["drawdown"].values:
        if val < 0:
            current_dd += 1
            longest_dd = max(longest_dd, current_dd)
        else:
            current_dd = 0

    # Turnover (proper: one-sided sell notional / average portfolio value)
    turnover_stats = {}
    avg_pv = equity_df["portfolio_value"].mean()
    if not turnover_df.empty:
        turnover_stats["avg_turnover_pct"] = turnover_df["turnover_pct"].mean()
        turnover_stats["max_turnover_pct"] = turnover_df["turnover_pct"].max()
        sell_notional = turnover_df["sell_notional"].sum()
        turnover_stats["annualized_turnover"] = sell_notional / avg_pv / years if (years > 0 and avg_pv > 0) else 0
    else:
        turnover_stats = {"avg_turnover_pct": 0, "max_turnover_pct": 0, "annualized_turnover": 0}

    # Cost drag
    cost_drag = trades_df["slippage"].sum() / initial_capital if not trades_df.empty else 0

    # Trade stats
    hit_rate = None
    avg_hold = None
    med_hold = None
    weekly_exits = 0
    monthly_exits = 0
    if exit_records:
        exit_df = pd.DataFrame(exit_records)
        valid = exit_df.dropna(subset=["pnl_pct"])
        hit_rate = (valid["pnl_pct"] > 0).mean() if not valid.empty else None
        avg_hold = exit_df["holding_days"].mean()
        med_hold = exit_df["holding_days"].median()
        weekly_exits = int((exit_df["reason"] == "weekly_exit").sum())
        monthly_exits = int((exit_df["reason"] == "monthly_exit").sum())

    trade_counts = {
        "trades_total": len(trades_df),
        "buys": len(trades_df[trades_df["side"] == "BUY"]) if not trades_df.empty else 0,
        "sells": len(trades_df[trades_df["side"] == "SELL"]) if not trades_df.empty else 0,
    }

    # Holdings and cash stats
    avg_holdings = equity_df["holdings_count"].mean()
    med_holdings = equity_df["holdings_count"].median()
    avg_cash_pct = equity_df["cash_pct"].mean()

    # % time invested (at least 1 holding)
    pct_time_invested = (equity_df["holdings_count"] > 0).mean()

    # Monthly returns
    monthly_pv = equity_df.set_index("date")["portfolio_value"].resample("ME").last().dropna()
    monthly_returns = monthly_pv.pct_change().dropna()
    win_rate_monthly = (monthly_returns > 0).mean() if len(monthly_returns) > 0 else None
    best_month = monthly_returns.max() if len(monthly_returns) > 0 else None
    worst_month = monthly_returns.min() if len(monthly_returns) > 0 else None
    avg_monthly = monthly_returns.mean() if len(monthly_returns) > 0 else None

    metrics = {
        "start": start_date,
        "end": end_date,
        "total_return": total_return,
        "cagr": cagr,
        "annualized_volatility": ann_vol,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "max_drawdown_duration_days": longest_dd,
        "calmar_ratio": calmar,
        "cost_drag_pct": cost_drag,
        **turnover_stats,
        "hit_rate_overall": hit_rate,
        "avg_holding_days": avg_hold,
        "median_holding_days": med_hold,
        **trade_counts,
        "weekly_exits": weekly_exits,
        "monthly_exits": monthly_exits,
        "avg_holdings_count": avg_holdings,
        "median_holdings_count": med_holdings,
        "avg_cash_pct": avg_cash_pct,
        "pct_time_invested": pct_time_invested,
        "win_rate_monthly": win_rate_monthly,
        "best_month": best_month,
        "worst_month": worst_month,
        "avg_monthly_return": avg_monthly,
    }
    return pd.DataFrame([metrics])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Backtest Trend Leaders 20 — dual-frequency trend-following portfolio"
    )
    parser.add_argument("--signals", required=True, type=Path,
                        help="Path to trend leaders signals CSV (used for entry ranking)")
    parser.add_argument("--hold-signals", type=Path, default=None,
                        help="Separate signals for hold/exit decisions (if different from entry)")
    parser.add_argument("--prices-dir", default="nse500_data", type=Path)
    parser.add_argument("--benchmark", default="data/benchmarks/nifty100.csv", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--top-n", type=int, default=20)
    parser.add_argument("--exit-buffer", type=int, default=10,
                        help="Keep stock unless rank drops below top_n + buffer (default 10)")
    parser.add_argument("--max-weight", type=float, default=0.075)
    parser.add_argument("--slippage", type=float, default=0.002)
    parser.add_argument("--variant", choices=["base", "market_filter", "monthly_only"],
                        default="base")
    parser.add_argument("--market-filter-index", type=Path, default=None,
                        help="Index CSV for market filter (e.g., indices_data/NIFTY_500.csv)")
    parser.add_argument("--market-filter-max-exposure", type=float, default=0.50)
    parser.add_argument("--min-hold-days", type=int, default=0,
                        help="Minimum holding period in days (default 0)")
    parser.add_argument("--unified-rebalance", action="store_true",
                        help="Unified rebalance: entry+exit on same dates (no separate weekly exit)")
    parser.add_argument("--no-whole-shares", action="store_true",
                        help="Use fractional shares (default: whole shares)")

    args = parser.parse_args()

    # Auto-set market filter index if variant is market_filter
    mf_index = args.market_filter_index
    if args.variant == "market_filter" and mf_index is None:
        mf_index = Path("indices_data/NIFTY_500.csv")

    run_backtest(
        prices_dir=args.prices_dir,
        signals_path=args.signals,
        benchmark_path=args.benchmark,
        output_dir=args.output_dir,
        initial_capital=args.initial_capital,
        top_n=args.top_n,
        exit_buffer=args.exit_buffer,
        max_weight=args.max_weight,
        min_hold_days=args.min_hold_days,
        unified_rebalance=args.unified_rebalance,
        hold_signals_path=args.hold_signals,
        slippage=args.slippage,
        variant=args.variant,
        market_filter_index_path=mf_index,
        market_filter_max_exposure=args.market_filter_max_exposure,
        whole_shares=not args.no_whole_shares,
    )


if __name__ == "__main__":
    main()
