import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def load_price_panels(prices_dir: Path):
    rows = []
    for csv_path in sorted(prices_dir.glob("*_day.csv")):
        symbol = csv_path.stem.replace("_day", "")
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty or "close" not in df.columns:
            continue
        df["symbol"] = symbol
        if {"open", "high", "low", "close"}.issubset(df.columns):
            df["trade_price"] = df[["open", "high", "low", "close"]].mean(axis=1)
        else:
            df["trade_price"] = df["close"]
        rows.append(df[["date", "symbol", "close", "trade_price"]])
    if not rows:
        raise RuntimeError(f"No price files found in {prices_dir}")
    combined = pd.concat(rows, ignore_index=True)
    close_panel = combined.pivot(index="date", columns="symbol", values="close").sort_index()
    trade_panel = combined.pivot(index="date", columns="symbol", values="trade_price").sort_index()
    close_panel = close_panel.ffill()
    trade_panel = trade_panel.ffill()
    return close_panel, trade_panel


def load_signals(path: Path, top_n: int, exit_buffer: int = 0):
    df = pd.read_csv(path, parse_dates=["date"])
    entry_df = df[df["rank"] <= top_n]
    entry_grouped = entry_df.groupby("date")["symbol"].apply(list)

    exit_threshold = top_n + exit_buffer
    exit_df = df[df["rank"] <= exit_threshold]
    rank_map_by_date = {}
    score_map_by_date = {}
    for date, group in exit_df.groupby("date"):
        rank_map_by_date[pd.Timestamp(date)] = dict(zip(group["symbol"], group["rank"]))
        if "score" in group.columns:
            score_map_by_date[pd.Timestamp(date)] = dict(zip(group["symbol"], group["score"]))

    max_rank = df["rank"].max()
    if exit_threshold > max_rank:
        print(f"Warning: exit threshold ({exit_threshold}) exceeds max rank in signals ({max_rank}). Missing ranks will be treated as inf.")

    return entry_grouped, rank_map_by_date, score_map_by_date, df


def build_streak_map(signals_df: pd.DataFrame, top_n: int) -> dict:
    """For each rebalance date, map symbol -> consecutive weeks in top-N.

    Returns {Timestamp: {symbol: streak_count}}.
    A stock appearing for the first time has streak=1.
    """
    entry_df = signals_df[signals_df["rank"] <= top_n]
    dates = sorted(entry_df["date"].unique())
    prev_symbols = set()
    streaks = {}  # symbol -> current streak
    result = {}

    for date in dates:
        current_symbols = set(entry_df[entry_df["date"] == date]["symbol"])
        new_streaks = {}
        for sym in current_symbols:
            new_streaks[sym] = streaks.get(sym, 0) + 1 if sym in prev_symbols else 1
        # Reset streaks for symbols that dropped out
        streaks = new_streaks
        result[pd.Timestamp(date)] = dict(streaks)
        prev_symbols = current_symbols

    return result


def load_benchmark(path: Path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date")
    df = df.set_index("date")
    return df["close"].ffill()


def map_signal_to_trade(signal_date, calendar):
    """Map signal date to trade execution date (next trading day after signal).

    Trades always execute AFTER the signal day, never on or before.
    Looks up to 5 days forward to find the next trading day.
    """
    for offset in range(1, 6):
        candidate = signal_date + pd.Timedelta(days=offset)
        if candidate in calendar:
            return candidate
    return None


def longest_drawdown_duration(drawdown_series: pd.Series) -> int:
    longest = 0
    current = 0
    for val in drawdown_series:
        if val < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def summarise_metrics(
    equity_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    turnover_df: pd.DataFrame,
    exit_records: list,
    initial_capital: float,
    top_n: int,
):
    if equity_df.empty:
        return pd.DataFrame()

    start_val = equity_df["portfolio_value"].iloc[0]
    end_val = equity_df["portfolio_value"].iloc[-1]
    total_return = end_val / start_val - 1

    start_date = equity_df["date"].iloc[0]
    end_date = equity_df["date"].iloc[-1]
    years = max((end_date - start_date).days / 365.25, 1e-6)
    cagr = (1 + total_return) ** (1 / years) - 1

    max_dd = equity_df["drawdown"].min()
    dd_duration = longest_drawdown_duration(equity_df["drawdown"].values)

    turnover_stats = {"avg_turnover_pct": None, "max_turnover_pct": None, "annualized_turnover": None}
    if not turnover_df.empty:
        turnover_stats["avg_turnover_pct"] = turnover_df["turnover_pct"].mean()
        turnover_stats["max_turnover_pct"] = turnover_df["turnover_pct"].max()
        total_turnover = turnover_df["turnover"].sum()
        turnover_stats["annualized_turnover"] = total_turnover / initial_capital / years if years > 0 else None

    cost_drag = trades_df["slippage"].sum() / initial_capital if not trades_df.empty else 0

    hit_rates = {"hit_rate_overall": None}
    hold_stats = {"avg_holding_days": None, "median_holding_days": None}
    if exit_records:
        exit_df = pd.DataFrame(exit_records)
        hit_rates["hit_rate_overall"] = (exit_df["pnl_pct"] > 0).mean()
        hold_stats["avg_holding_days"] = exit_df["holding_days"].mean()
        hold_stats["median_holding_days"] = exit_df["holding_days"].median()

        # Hit-rate by entry-rank quintile
        # Filter out rows with None entry_rank before binning
        valid_exit_df = exit_df.dropna(subset=["entry_rank"])
        if not valid_exit_df.empty and len(valid_exit_df) > 0:
            bins = [0, *(i * top_n / 5 for i in range(1, 5)), top_n + 1]
            labels = [f"q{i}" for i in range(1, 6)]
            valid_exit_df["rank_quintile"] = pd.cut(valid_exit_df["entry_rank"], bins=bins, labels=labels, include_lowest=True)
            for label, grp in valid_exit_df.groupby("rank_quintile"):
                hit_rates[f"hit_rate_{label}"] = (grp["pnl_pct"] > 0).mean()

    trade_counts = {
        "trades_total": len(trades_df),
        "buys": len(trades_df[trades_df["side"] == "BUY"]),
        "sells": len(trades_df[trades_df["side"] == "SELL"]),
        "trades_per_week": None,
        "trades_per_month": None,
        "trades_per_year": None,
    }
    if not trades_df.empty:
        weeks = len(pd.period_range(start_date, end_date, freq="W")) or 1
        months = len(pd.period_range(start_date, end_date, freq="M")) or 1
        years_count = len(pd.period_range(start_date, end_date, freq="Y")) or 1
        trade_counts["trades_per_week"] = trade_counts["trades_total"] / weeks
        trade_counts["trades_per_month"] = trade_counts["trades_total"] / months
        trade_counts["trades_per_year"] = trade_counts["trades_total"] / years_count

    metrics = {
        "start": start_date,
        "end": end_date,
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "max_drawdown_duration_days": dd_duration,
        "cost_drag_pct": cost_drag,
        **turnover_stats,
        **hold_stats,
        **hit_rates,
        **trade_counts,
    }
    return pd.DataFrame([metrics])


def run_backtest(
    prices_dir,
    signals_path,
    benchmark_path,
    output_dir,
    initial_capital,
    top_n,
    slippage,
    scenario,
    cooldown_weeks=1,
    staged_step=0.25,
    vol_lookback=63,
    target_vol=0.15,
    exit_buffer=0,
    pnl_hold_threshold=None,
    min_score=None,
    score_rebalance_mode="full",
    min_entry_score=None,
    min_exit_score=None,
    min_consecutive_weeks=1,
    entry_rank=None,
    min_hold_days=0,
):
    # Handle backward compatibility: if min_score is set but entry/exit not set, use min_score for both
    if min_score is not None:
        if min_entry_score is None:
            min_entry_score = min_score
        if min_exit_score is None:
            min_exit_score = min_score

    close_panel, trade_panel = load_price_panels(prices_dir)
    entry_signals, rank_map_by_date, score_map_by_date, _signals_df = load_signals(signals_path, top_n, exit_buffer)
    streak_map = build_streak_map(_signals_df, top_n) if min_consecutive_weeks > 1 else {}
    benchmark = load_benchmark(benchmark_path)
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    schedule = {}
    # Build trade_date -> signal_date mapping for score lookup
    trade_to_signal_map = {}
    for signal_date, symbols in entry_signals.items():
        trade_date = map_signal_to_trade(signal_date, calendar)
        if trade_date is not None:
            schedule[pd.Timestamp(trade_date)] = symbols
            trade_to_signal_map[pd.Timestamp(trade_date)] = pd.Timestamp(signal_date)

    rebalance_dates = sorted(schedule.keys())

    holdings = {}
    cost_basis = {}
    last_prices = {}
    entry_meta = {}
    cash = initial_capital
    trade_records = []
    equity_records = []
    turnover_records = []
    exit_records = []
    peak_equity = initial_capital
    exposure = 1.0 if scenario != "vol_trigger" else 0.0
    cooldown_counter = 0

    for date in calendar:
        close_row = close_panel.loc[date]
        benchmark_price = benchmark_aligned.loc[date]

        portfolio_value = cash
        for symbol, shares in sorted(holdings.items()):
            price = close_row.get(symbol)
            if pd.isna(price):
                price = last_prices.get(symbol)
            else:
                last_prices[symbol] = price
            if price is None or pd.isna(price):
                continue
            portfolio_value += shares * price

        peak_equity = max(peak_equity, portfolio_value)
        drawdown = portfolio_value / peak_equity - 1
        drawdown_hit = drawdown <= -0.25

        if scenario == "baseline":
            pass
        elif scenario == "cooldown":
            if drawdown_hit and cooldown_counter == 0:
                cooldown_counter = cooldown_weeks
                exposure = 0.0
            if cooldown_counter > 0 and date in rebalance_dates:
                cooldown_counter -= 1
                exposure = min(1.0, exposure + staged_step)
        elif scenario == "vol_trigger":
            realized_vol = close_panel.pct_change().rolling(vol_lookback).std().loc[date].mean()
            if pd.isna(realized_vol) or realized_vol == 0:
                realized_vol = target_vol
            exposure = min(1.0, target_vol / realized_vol)

        equity_records.append({
            "date": date,
            "portfolio_value": portfolio_value,
            "cash": cash,
            "invested": portfolio_value - cash,
            "benchmark": benchmark_price,
            "drawdown": drawdown,
            "exposure": exposure,
        })

        if date not in rebalance_dates:
            continue

        target_symbols = schedule.get(date)
        if target_symbols is None:
            continue

        target_symbols = target_symbols[:top_n]

        # Apply score filtering if min_entry_score is specified and > 0
        # Lookup scores using signal date (not trade date)
        signal_date = trade_to_signal_map.get(date)
        current_scores = score_map_by_date.get(signal_date, {}) if signal_date else {}
        if min_entry_score is not None and min_entry_score > 0 and current_scores:
            target_symbols = [sym for sym in target_symbols if current_scores.get(sym, 0) >= min_entry_score]

        if exposure <= 0:
            holdings.clear()
            cost_basis.clear()
            entry_meta.clear()
            continue
        current_symbols = set(holdings.keys())
        target_set = set(target_symbols)

        exit_threshold = top_n + exit_buffer
        # Lookup ranks using signal date (not trade date)
        current_ranks = rank_map_by_date.get(signal_date, {}) if signal_date else {}
        exits = []
        for sym in sorted(current_symbols):
            if sym in target_set:
                continue
            rank = current_ranks.get(sym, float("inf"))
            score = current_scores.get(sym, 0) if (min_exit_score is not None and min_exit_score > 0) else None
            price_for_pnl = trade_panel.loc[date].get(sym)
            if pd.isna(price_for_pnl):
                price_for_pnl = close_row.get(sym)
            pnl_pct = None
            if price_for_pnl is not None and not pd.isna(price_for_pnl):
                avg_cost = cost_basis.get(sym, 0) / holdings.get(sym, 1)
                if avg_cost > 0:
                    pnl_pct = price_for_pnl / avg_cost - 1
            should_exit = rank > exit_threshold
            # Also exit if score falls below minimum exit threshold
            if min_exit_score is not None and min_exit_score > 0 and score is not None and score < min_exit_score:
                should_exit = True
            if pnl_hold_threshold is not None and should_exit and pnl_pct is not None and pnl_pct > pnl_hold_threshold:
                should_exit = False
            if min_hold_days > 0 and should_exit:
                entry_date = entry_meta.get(sym, {}).get("date")
                if entry_date is not None and (date - entry_date).days < min_hold_days:
                    should_exit = False
            if should_exit:
                exits.append(sym)
        rebalance_turnover = 0
        for sym in exits:
            shares = holdings.pop(sym)
            price = trade_panel.loc[date].get(sym)
            if pd.isna(price):
                price = close_row.get(sym)
            if pd.isna(price) or price <= 0:
                holdings[sym] = shares
                continue
            proceeds = shares * price * (1 - slippage)
            cash += proceeds
            avg_cost = cost_basis.get(sym, 0) / shares if shares else 0
            cost_basis[sym] = cost_basis.get(sym, 0) - avg_cost * shares
            if holdings.get(sym, 0) == 0:
                cost_basis.pop(sym, None)
                meta = entry_meta.pop(sym, {"date": date, "rank": None})
                pnl_pct = price / avg_cost - 1 if avg_cost else None
                exit_records.append(
                    {
                        "symbol": sym,
                        "entry_date": meta.get("date"),
                        "exit_date": date,
                        "entry_rank": meta.get("rank"),
                        "holding_days": (date - meta.get("date")).days if meta.get("date") is not None else None,
                        "pnl_pct": pnl_pct,
                    }
                )
            notional = shares * price
            cost = notional * slippage
            rebalance_turnover += abs(notional)
            trade_records.append({
                "date": date,
                "symbol": sym,
                "side": "SELL",
                "shares": shares,
                "price": price,
                "notional": notional,
                "slippage": cost,
                "cash_after": cash,
            })

        entrants = [sym for sym in target_symbols if sym not in holdings]

        # Filter entrants by consecutive weeks in top-N
        if min_consecutive_weeks > 1 and streak_map:
            streaks = streak_map.get(signal_date, {})
            entrants = [sym for sym in entrants if streaks.get(sym, 0) >= min_consecutive_weeks]

        # Filter entrants by entry rank (must be top entry_rank to enter,
        # but existing holdings stay until they exit the full top_n band)
        if entry_rank is not None:
            entrants = [sym for sym in entrants if current_ranks.get(sym, float("inf")) <= entry_rank]

        # When pnl-hold keeps stocks beyond their rank, cap new entrants
        # so total holdings never exceed top_n.
        if pnl_hold_threshold is not None:
            max_new = max(0, top_n - len(holdings))
            entrants = entrants[:max_new]

        # Handle position sizing based on rebalance mode (for score filtering)
        if min_entry_score is not None and min_entry_score > 0 and score_rebalance_mode == "full" and (entrants or len(target_symbols) != len(holdings)):
            # Full rebalance mode: rebalance all holdings to equal weight
            # Calculate total portfolio value
            portfolio_val = cash
            for sym, qty in sorted(holdings.items()):
                price = close_row.get(sym, last_prices.get(sym, 0))
                portfolio_val += price * qty

            # Calculate target position size for each stock
            num_positions = len(target_symbols)
            if num_positions > 0:
                target_per_stock = (portfolio_val * exposure) / num_positions

                # Collect all needed buys/sells first
                trades_needed = []
                for sym in target_symbols:
                    price = trade_panel.loc[date].get(sym)
                    if pd.isna(price):
                        price = close_row.get(sym)
                    if pd.isna(price) or price <= 0:
                        continue

                    current_value = holdings.get(sym, 0) * price
                    target_value = target_per_stock
                    delta_value = target_value - current_value

                    if abs(delta_value) < 1:  # Skip tiny adjustments
                        continue

                    trades_needed.append((sym, price, delta_value))

                # Execute sells first to free up cash
                for sym, price, delta_value in trades_needed:
                    if delta_value < 0:  # Sell
                        shares_to_sell = min(-delta_value / price, holdings.get(sym, 0))
                        if shares_to_sell > 0:
                            proceeds = shares_to_sell * price * (1 - slippage)
                            cash += proceeds
                            holdings[sym] = holdings.get(sym, 0) - shares_to_sell
                            avg_cost = cost_basis.get(sym, 0) / (holdings.get(sym, 0) + shares_to_sell)
                            cost_basis[sym] = cost_basis.get(sym, 0) - avg_cost * shares_to_sell
                            if holdings[sym] < 1e-6:
                                holdings.pop(sym, None)
                                cost_basis.pop(sym, None)
                            notional = shares_to_sell * price
                            rebalance_turnover += abs(notional)
                            trade_records.append({
                                "date": date,
                                "symbol": sym,
                                "side": "SELL",
                                "shares": shares_to_sell,
                                "price": price,
                                "notional": notional,
                                "slippage": shares_to_sell * price * slippage,
                                "cash_after": cash,
                            })

                # Execute buys, giving remaining cash to last buy
                buys_needed = [(sym, price, delta) for sym, price, delta in trades_needed if delta > 0]
                for idx, (sym, price, delta_value) in enumerate(buys_needed):
                    is_last_buy = (idx == len(buys_needed) - 1)

                    if is_last_buy and len(buys_needed) > 1:
                        # Give all remaining cash to last buy to avoid rounding errors
                        shares_to_buy = cash / (price * (1 + slippage))
                        cost = cash
                    else:
                        shares_to_buy = delta_value / (price * (1 + slippage))
                        cost = shares_to_buy * price * (1 + slippage)
                        if cost > cash + 0.01:  # Allow small tolerance
                            shares_to_buy = cash / (price * (1 + slippage))
                            cost = cash

                    if shares_to_buy > 0:
                        holdings[sym] = holdings.get(sym, 0) + shares_to_buy
                        cost_basis[sym] = cost_basis.get(sym, 0) + cost
                        if sym not in entry_meta:
                            entry_meta[sym] = {"date": date, "rank": current_ranks.get(sym)}
                        cash -= cost
                        notional = shares_to_buy * price
                        rebalance_turnover += abs(notional)
                        trade_records.append({
                            "date": date,
                            "symbol": sym,
                            "side": "BUY",
                            "shares": shares_to_buy,
                            "price": price,
                            "notional": notional,
                            "slippage": shares_to_buy * price * slippage,
                            "cash_after": cash,
                        })
        elif entrants:
            # Incremental mode (default): only allocate to new entrants
            target_cash = cash + sum(close_row.get(sym, last_prices.get(sym, 0)) * qty for sym, qty in holdings.items())
            deploy_cash = target_cash * exposure - (target_cash - cash)
            deploy_cash = max(0, deploy_cash)
            allocation = deploy_cash / len(entrants) if entrants else 0

            # Track valid entrants (those with prices)
            valid_entrants = []
            for sym in entrants:
                price = trade_panel.loc[date].get(sym)
                if pd.isna(price):
                    price = close_row.get(sym)
                if not pd.isna(price) and price > 0:
                    valid_entrants.append((sym, price))

            # Execute buys, giving remaining cash to last stock to avoid rounding issues
            for idx, (sym, price) in enumerate(valid_entrants):
                is_last = (idx == len(valid_entrants) - 1)

                if is_last and len(valid_entrants) > 1:
                    # Give all remaining cash to last stock to ensure full deployment
                    gross = cash
                else:
                    gross = allocation

                shares = gross / (price * (1 + slippage))
                cost = shares * price * (1 + slippage)

                # Allow small tolerance for floating-point errors
                if cost > cash + 0.01:
                    continue

                # Ensure we don't overdraw cash (clamp to available)
                if cost > cash:
                    shares = cash / (price * (1 + slippage))
                    cost = cash

                holdings[sym] = holdings.get(sym, 0) + shares
                cost_basis[sym] = cost_basis.get(sym, 0) + cost
                entry_meta[sym] = {"date": date, "rank": current_ranks.get(sym)}
                cash -= cost
                notional = shares * price
                rebalance_turnover += abs(notional)
                trade_records.append({
                    "date": date,
                    "symbol": sym,
                    "side": "BUY",
                    "shares": shares,
                    "price": price,
                    "notional": notional,
                    "slippage": shares * price * slippage,
                    "cash_after": cash,
                })

        if rebalance_turnover:
            turnover_records.append({
                "date": date,
                "turnover": rebalance_turnover,
                "turnover_pct": rebalance_turnover / portfolio_value if portfolio_value else 0,
            })

    equity_df = pd.DataFrame(equity_records)
    trades_df = pd.DataFrame(trade_records)
    turnover_df = pd.DataFrame(turnover_records)
    holdings_records = []

    if not trades_df.empty:
        first_trade = trades_df["date"].min()
        equity_df = equity_df[equity_df["date"] >= first_trade]
        turnover_df = turnover_df[turnover_df["date"] >= first_trade]

    output_dir.mkdir(parents=True, exist_ok=True)
    equity_df.to_csv(output_dir / "momentum_equity.csv", index=False)
    trades_df.to_csv(output_dir / "momentum_trades.csv", index=False)
    turnover_df.to_csv(output_dir / "momentum_turnover.csv", index=False)
    metrics_df = summarise_metrics(equity_df, trades_df, turnover_df, exit_records, initial_capital, top_n)
    if not metrics_df.empty:
        metrics_df.to_csv(output_dir / "momentum_metrics.csv", index=False)
    # Snapshot current portfolio
    if holdings:
        final_value = equity_df["portfolio_value"].iloc[-1] if not equity_df.empty else None
        last_date = calendar[-1]
        for sym, shares in holdings.items():
            # Use the latest actual close in the panel (no forward fill past the last known date)
            series = close_panel[sym].dropna()
            price = series.iloc[-1] if not series.empty else None
            avg_cost = cost_basis.get(sym, 0) / shares if shares else 0
            notional = price * shares if price is not None and not pd.isna(price) else None
            pnl_pct = price / avg_cost - 1 if avg_cost and price is not None and not pd.isna(price) else None
            meta = entry_meta.get(sym, {})
            entry_date = meta.get("date")
            holding_days = (last_date - entry_date).days if entry_date is not None else None
            contribution_pct = (notional / final_value) if final_value and notional is not None else None
            holdings_records.append({
                "symbol": sym,
                "shares": shares,
                "avg_cost": avg_cost,
                "entry_date": entry_date,
                "entry_rank": meta.get("rank"),
                "holding_days": holding_days,
                "last_price": price,
                "pnl_pct": pnl_pct,
                "notional": notional,
                "contribution_pct": contribution_pct,
            })
        if holdings_records:
            pd.DataFrame(holdings_records).to_csv(output_dir / "momentum_holdings.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="Backtest NSE 500 momentum strategy")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--signals", type=Path, default=Path("data/momentum/top25_signals.csv"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/backtests"))
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--slippage", type=float, default=0.002)
    parser.add_argument("--scenario", choices=["baseline", "cooldown", "vol_trigger"], default="baseline")
    parser.add_argument("--cooldown-weeks", type=int, default=1)
    parser.add_argument("--staged-step", type=float, default=0.25)
    parser.add_argument("--vol-lookback", type=int, default=63)
    parser.add_argument("--target-vol", type=float, default=0.15)
    parser.add_argument("--exit-buffer", type=int, default=0, help="Allow exits only when rank exceeds top_n + buffer (hysteresis)")
    parser.add_argument("--pnl-hold-threshold", type=float, help="If set, defer exit when rank is outside band but unrealized PnL > threshold (e.g., 0.05 for +5 percent)")
    parser.add_argument("--min-score", type=float, help="Minimum momentum score required to enter/hold positions (e.g., 2.0) - deprecated, use --min-entry-score and --min-exit-score")
    parser.add_argument("--min-entry-score", type=float, help="Minimum score required to enter a position (e.g., 2.5)")
    parser.add_argument("--min-exit-score", type=float, help="Minimum score to remain in position; exit when below this (e.g., 1.5)")
    parser.add_argument("--score-rebalance-mode", choices=["full", "incremental"], default="incremental", help="full: rebalance all holdings to equal weight; incremental: only allocate to new entrants")
    parser.add_argument("--min-consecutive-weeks", type=int, default=1, help="Require stock to be in top-N for N consecutive weeks before entry (default: 1 = no filter)")
    parser.add_argument("--entry-rank", type=int, help="Only enter stocks ranked <= this value; existing holdings stay until they leave top-N (e.g., 12 = enter top-12, hold until out of top-24)")
    parser.add_argument("--min-hold-days", type=int, default=0, help="Minimum days to hold a position before it can be exited (default: 0)")
    args = parser.parse_args()

    run_backtest(
        args.prices_dir,
        args.signals,
        args.benchmark,
        args.output_dir,
        args.initial_capital,
        args.top_n,
        args.slippage,
        args.scenario,
        cooldown_weeks=args.cooldown_weeks,
        staged_step=args.staged_step,
        vol_lookback=args.vol_lookback,
        target_vol=args.target_vol,
        exit_buffer=args.exit_buffer,
        pnl_hold_threshold=args.pnl_hold_threshold,
        min_score=args.min_score,
        score_rebalance_mode=args.score_rebalance_mode,
        min_entry_score=args.min_entry_score,
        min_exit_score=args.min_exit_score,
        min_consecutive_weeks=args.min_consecutive_weeks,
        entry_rank=args.entry_rank,
        min_hold_days=args.min_hold_days,
    )


if __name__ == "__main__":
    main()
