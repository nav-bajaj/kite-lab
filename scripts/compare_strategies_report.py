"""Comparative HTML report across L6 momentum, OM25 v3, and TL25 v3.

Loads `momentum_*.csv` files from each strategy's run dir, slices to a
common start date, and emits a side-by-side comparison report with the
same level of detail as scripts/report_backtests.py output.

Each strategy must have, at the path given:
  - momentum_equity.csv   (date, portfolio_value, drawdown, benchmark)
  - momentum_holdings.csv (full holdings schema)
  - momentum_trades.csv   (date, symbol, side, shares, price, notional, slippage)
  - momentum_metrics.csv  (single-row summary)
"""
from __future__ import annotations

import argparse
import base64
import io
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


STRATEGY_COLORS = {
    "L6 Momentum": "#1976d2",
    "OM25 v3":     "#43a047",
    "TL25 v3":     "#6a1b9a",
    "Nifty 100":   "#888888",
}


def fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def load_strategy(run_dir: Path, sub: str | None = None) -> dict:
    """Load all four CSVs for a single strategy run."""
    base = run_dir / sub if sub else run_dir
    eq = pd.read_csv(base / "momentum_equity.csv", parse_dates=["date"])
    eq = eq.sort_values("date").reset_index(drop=True)
    trades = pd.read_csv(base / "momentum_trades.csv", parse_dates=["date"])
    holdings = pd.read_csv(base / "momentum_holdings.csv")
    metrics = pd.read_csv(base / "momentum_metrics.csv").iloc[0].to_dict()
    return dict(equity=eq, trades=trades, holdings=holdings, metrics=metrics)


def slice_from(start_ts: pd.Timestamp, data: dict) -> dict:
    """Slice equity + trades to `>= start_ts` and rebase equity to ₹1M."""
    eq = data["equity"].copy()
    eq = eq[eq["date"] >= start_ts].reset_index(drop=True)
    start_val = eq["portfolio_value"].iloc[0]
    rebase = 1_000_000 / start_val
    eq["portfolio_value"] = eq["portfolio_value"] * rebase
    eq["drawdown"] = eq["portfolio_value"] / eq["portfolio_value"].cummax() - 1.0
    tr = data["trades"].copy()
    tr = tr[tr["date"] >= start_ts].reset_index(drop=True)
    return dict(equity=eq, trades=tr,
                holdings=data["holdings"], metrics=data["metrics"])


def compute_stats(eq: pd.DataFrame, rf: float = 0.05) -> dict:
    pv = eq["portfolio_value"].astype(float)
    dates = eq["date"]
    rets = pv.pct_change().dropna()
    yrs = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    excess = cagr - rf
    sharpe = excess / vol if vol > 0 else 0
    downside = rets[rets < 0].std() * math.sqrt(252)
    sortino = excess / downside if downside > 0 else 0
    cum = pv / pv.cummax()
    mdd = cum.min() - 1
    calmar = cagr / abs(mdd) if mdd != 0 else 0
    gains = rets[rets > 0].sum()
    losses = abs(rets[rets < 0].sum())
    omega = gains / losses if losses > 0 else 0
    var95 = rets.quantile(0.05)
    cvar95 = rets[rets <= var95].mean()
    tail = abs(rets.quantile(0.95) / var95) if var95 != 0 else 0
    dd_series = ((pv / pv.cummax()) - 1) * 100
    ulcer = math.sqrt((dd_series ** 2).mean())
    skew = rets.skew()
    kurt = rets.kurt()
    hit_daily = (rets > 0).mean()
    return dict(
        cagr=cagr, vol=vol, sharpe=sharpe, sortino=sortino,
        max_dd=mdd, calmar=calmar, omega=omega, ulcer=ulcer,
        var95=var95, cvar95=cvar95, tail_ratio=tail,
        skew=skew, kurt=kurt, hit_daily=hit_daily,
        best_day=rets.max(), worst_day=rets.min(),
        total_ret=pv.iloc[-1] / pv.iloc[0] - 1,
        years=yrs, final_value=float(pv.iloc[-1]),
    )


def compute_vs_bench(eq: pd.DataFrame) -> dict:
    """Beta/alpha/up-down capture vs benchmark column."""
    if "benchmark" not in eq.columns or eq["benchmark"].isna().all():
        return {}
    df = eq[["date", "portfolio_value", "benchmark"]].dropna()
    if len(df) < 30:
        return {}
    p = df["portfolio_value"].pct_change()
    i = df["benchmark"].pct_change()
    df = pd.concat([p, i], axis=1).dropna()
    df.columns = ["p", "i"]
    if len(df) < 30:
        return {}
    cov = np.cov(df["p"], df["i"], ddof=0)
    beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 0
    rf_d = 0.05 / 252
    alpha_ann = (df["p"].mean() - rf_d) * 252 - beta * ((df["i"].mean() - rf_d) * 252)
    diff = df["p"] - df["i"]
    te = diff.std() * math.sqrt(252)
    ir = (diff.mean() * 252) / te if te > 0 else 0
    corr = df["p"].corr(df["i"])
    up = df[df["i"] > 0]
    dn = df[df["i"] < 0]
    up_cap = (up["p"].mean() / up["i"].mean()) if len(up) > 0 and up["i"].mean() > 0 else 0
    dn_cap = (dn["p"].mean() / dn["i"].mean()) if len(dn) > 0 and dn["i"].mean() < 0 else 0
    return dict(beta=beta, alpha_ann=alpha_ann, ir=ir, te=te,
                corr=corr, up_capture=up_cap, dn_capture=dn_cap)


def yearly_returns(eq: pd.DataFrame) -> pd.DataFrame:
    pv = eq.set_index("date")["portfolio_value"].astype(float)
    rows = []
    for y, gp in pv.groupby(pv.index.year):
        if len(gp) < 5: continue
        ret = gp.iloc[-1] / gp.iloc[0] - 1
        cum = gp / gp.cummax()
        dd = cum.min() - 1
        rows.append({"year": y, "ret": ret, "dd": dd})
    return pd.DataFrame(rows).set_index("year")


def monthly_heatmap_data(eq: pd.DataFrame) -> pd.DataFrame:
    s = eq.set_index("date")["portfolio_value"].astype(float)
    monthly = s.resample("ME").last().pct_change().dropna()
    if len(monthly) == 0:
        return pd.DataFrame()
    mat = pd.DataFrame(index=range(monthly.index.year.min(), monthly.index.year.max() + 1),
                       columns=range(1, 13), dtype=float)
    for date, val in monthly.items():
        mat.loc[date.year, date.month] = val
    return mat


def trailing_returns(eq: pd.DataFrame, *, periods=((30, "1M"), (90, "3M"), (180, "6M"),
                                                    (252, "1Y"), (504, "2Y"), (756, "3Y"),
                                                    (1260, "5Y"))) -> list:
    pv = eq.set_index("date")["portfolio_value"].astype(float)
    rows = []
    for days, label in periods:
        if len(pv) <= days:
            continue
        end = pv.iloc[-1]
        start = pv.iloc[-days - 1]
        rows.append({"period": label, "ret": end / start - 1,
                     "ann": (end / start) ** (252 / days) - 1 if days >= 252 else None})
    return rows


def trade_quality(trades: pd.DataFrame, holdings: pd.DataFrame) -> dict:
    """Round-trip trade quality from trades dataframe (FIFO matching)."""
    if trades.empty:
        return {}
    closed = []
    open_lots = {}
    for _, t in trades.sort_values("date").iterrows():
        sym = t["symbol"]; side = t["side"]; sh = int(t["shares"]); pr = float(t["price"])
        slip = t.get("slippage", 0) / max(sh, 1)
        if side == "BUY":
            eff = pr * (1 + 0.002)
            open_lots.setdefault(sym, []).append([sh, eff, t["date"]])
        else:
            eff = pr * (1 - 0.002)
            remaining = sh
            while remaining > 0 and open_lots.get(sym):
                lot_sh, lot_cost, lot_date = open_lots[sym][0]
                take = min(lot_sh, remaining)
                pnl_pct = (eff / lot_cost - 1)
                hold = (t["date"] - lot_date).days
                closed.append({"pnl_pct": pnl_pct, "hold_days": hold})
                lot_sh -= take; remaining -= take
                if lot_sh == 0:
                    open_lots[sym].pop(0)
                else:
                    open_lots[sym][0][0] = lot_sh
    if not closed:
        return {}
    df = pd.DataFrame(closed)
    pnls = df["pnl_pct"]
    winners = pnls[pnls > 0]
    losers = pnls[pnls <= 0]
    return dict(
        n_closed=len(pnls),
        win_rate=len(winners) / len(pnls) if len(pnls) else 0,
        avg_pnl=pnls.mean(),
        median_pnl=pnls.median(),
        avg_winner=winners.mean() if len(winners) else 0,
        avg_loser=losers.mean() if len(losers) else 0,
        best=pnls.max(),
        worst=pnls.min(),
        payoff=(winners.mean() / abs(losers.mean())) if len(winners) and len(losers) else 0,
        avg_hold=df["hold_days"].mean(),
    )


def fmt_pct(v, sign=False, d=2):
    if v is None or pd.isna(v): return "—"
    return f"{v*100:+.{d}f}%" if sign else f"{v*100:.{d}f}%"


def fmt_num(v, d=2):
    if v is None or pd.isna(v): return "—"
    return f"{v:.{d}f}"


def fmt_inr(v):
    if v is None or pd.isna(v): return "—"
    return f"₹{v:,.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--l6-dir", type=Path, default=Path("/tmp/comparison_runs/l6_momentum"))
    ap.add_argument("--om25-dir", type=Path, default=Path("/tmp/comparison_runs/om25_v3"))
    ap.add_argument("--om25-sub", default="backtests/baseline")
    ap.add_argument("--tl25-dir", type=Path, default=Path("/tmp/comparison_runs/tl25_v3"))
    ap.add_argument("--tl25-sub", default="backtests/baseline")
    ap.add_argument("--start", default="2017-01-01")
    ap.add_argument("--output", type=Path,
                    default=Path("reports/strategy_comparison.html"))
    args = ap.parse_args()

    start_ts = pd.Timestamp(args.start)

    print(f"[load] L6 from {args.l6_dir}")
    l6_raw = load_strategy(args.l6_dir)
    print(f"[load] OM25 from {args.om25_dir}/{args.om25_sub}")
    om25_raw = load_strategy(args.om25_dir, args.om25_sub)
    print(f"[load] TL25 from {args.tl25_dir}/{args.tl25_sub}")
    tl25_raw = load_strategy(args.tl25_dir, args.tl25_sub)

    print(f"[slice] from {args.start} ...")
    strategies = {
        "L6 Momentum": slice_from(start_ts, l6_raw),
        "OM25 v3":     slice_from(start_ts, om25_raw),
        "TL25 v3":     slice_from(start_ts, tl25_raw),
    }

    stats = {name: compute_stats(s["equity"]) for name, s in strategies.items()}
    vs_bench = {name: compute_vs_bench(s["equity"]) for name, s in strategies.items()}
    yearly = {name: yearly_returns(s["equity"]) for name, s in strategies.items()}
    trailing = {name: trailing_returns(s["equity"]) for name, s in strategies.items()}
    tradeq = {name: trade_quality(s["trades"], s["holdings"]) for name, s in strategies.items()}

    period_start = min(s["equity"]["date"].iloc[0] for s in strategies.values())
    period_end = max(s["equity"]["date"].iloc[-1] for s in strategies.values())

    # === Equity overlay chart ===
    print("[chart] equity overlay ...")
    fig, ax = plt.subplots(figsize=(13, 6))
    for name, s in strategies.items():
        eq = s["equity"]
        norm = eq["portfolio_value"] / eq["portfolio_value"].iloc[0] * 100
        ax.plot(eq["date"], norm, label=name,
                color=STRATEGY_COLORS[name], linewidth=2.0, alpha=0.95)
    # Benchmark from any strategy with benchmark col
    for s in strategies.values():
        if "benchmark" in s["equity"].columns and not s["equity"]["benchmark"].isna().all():
            b = s["equity"][["date", "benchmark"]].dropna()
            b_norm = b["benchmark"] / b["benchmark"].iloc[0] * 100
            ax.plot(b["date"], b_norm, label="Nifty 100",
                    color=STRATEGY_COLORS["Nifty 100"], linewidth=1.2, alpha=0.7)
            break
    ax.set_yscale("log")
    ax.set_title(f"Strategy Comparison — ₹100 indexed at {args.start} (log scale)",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Value")
    ax.legend(loc="upper left", framealpha=0.95)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.autofmt_xdate()
    equity_chart = fig_to_b64(fig)
    plt.close(fig)

    # === Drawdown overlay ===
    print("[chart] drawdown overlay ...")
    fig, ax = plt.subplots(figsize=(13, 4.5))
    for name, s in strategies.items():
        eq = s["equity"]
        ax.plot(eq["date"], eq["drawdown"] * 100, label=name,
                color=STRATEGY_COLORS[name], linewidth=1.5, alpha=0.9)
    ax.fill_between(strategies["L6 Momentum"]["equity"]["date"],
                    strategies["L6 Momentum"]["equity"]["drawdown"] * 100, 0,
                    color=STRATEGY_COLORS["L6 Momentum"], alpha=0.08)
    ax.set_title("Drawdowns", fontsize=14, fontweight="bold")
    ax.set_ylabel("Drawdown (%)")
    ax.axhline(0, color="#444", linewidth=0.8)
    ax.legend(loc="lower left", framealpha=0.95)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.autofmt_xdate()
    dd_chart = fig_to_b64(fig)
    plt.close(fig)

    # === Rolling 1y Sharpe ===
    print("[chart] rolling Sharpe ...")
    fig, ax = plt.subplots(figsize=(13, 4))
    for name, s in strategies.items():
        eq = s["equity"].set_index("date")
        r = eq["portfolio_value"].pct_change()
        rs = (r.rolling(252).mean() * 252) / (r.rolling(252).std() * np.sqrt(252))
        ax.plot(rs.index, rs.values, label=name,
                color=STRATEGY_COLORS[name], linewidth=1.6, alpha=0.95)
    ax.axhline(0, color="#888", linewidth=0.6)
    ax.axhline(1, color="#888", linewidth=0.4, linestyle="--")
    ax.set_title("Rolling 1-year Sharpe ratio", fontsize=14, fontweight="bold")
    ax.set_ylabel("Sharpe")
    ax.legend(loc="upper left", framealpha=0.95)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.autofmt_xdate()
    rs_chart = fig_to_b64(fig)
    plt.close(fig)

    # === Monthly heatmaps (one per strategy) ===
    print("[chart] heatmaps ...")
    heatmap_charts = {}
    for name, s in strategies.items():
        mh = monthly_heatmap_data(s["equity"])
        fig, ax = plt.subplots(figsize=(13, max(3.0, 0.4 * len(mh))))
        vals = (mh.values * 100).astype(float)
        im = ax.imshow(vals, aspect="auto", cmap="RdYlGn", vmin=-20, vmax=20)
        ax.set_xticks(range(12))
        ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
        ax.set_yticks(range(len(mh)))
        ax.set_yticklabels(mh.index)
        for i in range(len(mh)):
            for j in range(12):
                v = vals[i, j]
                if not np.isnan(v):
                    ax.text(j, i, f"{v:+.1f}",
                            ha="center", va="center", fontsize=8,
                            color="black" if abs(v) < 10 else "white")
        ax.set_title(f"{name} — Monthly Returns (%)", fontsize=13, fontweight="bold")
        plt.colorbar(im, ax=ax, fraction=0.02)
        heatmap_charts[name] = fig_to_b64(fig)
        plt.close(fig)

    # ============ HTML rendering ============
    print("[render] HTML ...")

    # Summary metrics table
    metric_defs = [
        ("Total Return", "total_ret", lambda v: fmt_pct(v, sign=True)),
        ("CAGR", "cagr", lambda v: fmt_pct(v, sign=True)),
        ("Annualized Volatility", "vol", lambda v: fmt_pct(v)),
        ("Sharpe Ratio (rf=5%)", "sharpe", lambda v: fmt_num(v)),
        ("Sortino Ratio", "sortino", lambda v: fmt_num(v)),
        ("Max Drawdown", "max_dd", lambda v: fmt_pct(v)),
        ("Calmar Ratio", "calmar", lambda v: fmt_num(v)),
        ("Omega Ratio", "omega", lambda v: fmt_num(v)),
        ("Ulcer Index", "ulcer", lambda v: fmt_num(v)),
        ("Daily VaR 95%", "var95", lambda v: fmt_pct(v)),
        ("Daily CVaR 95%", "cvar95", lambda v: fmt_pct(v)),
        ("Tail Ratio", "tail_ratio", lambda v: fmt_num(v)),
        ("Daily Skew", "skew", lambda v: fmt_num(v)),
        ("Daily Kurtosis", "kurt", lambda v: fmt_num(v)),
        ("Daily Hit Rate", "hit_daily", lambda v: fmt_pct(v)),
        ("Best Day", "best_day", lambda v: fmt_pct(v, sign=True)),
        ("Worst Day", "worst_day", lambda v: fmt_pct(v, sign=True)),
        ("Final Value (₹1M start)", "final_value", lambda v: fmt_inr(v)),
    ]
    summary_header = "".join(f"<th>{name}</th>" for name in strategies)
    summary_rows = ""
    for label, key, fmt in metric_defs:
        # Determine best/worst for highlighting
        vals = {n: stats[n].get(key) for n in strategies}
        # Higher is better for most; lower is better for vol, max_dd (more negative is worse),
        # var95, cvar95, ulcer, worst_day, kurt
        higher_better = key not in ("vol", "max_dd", "var95", "cvar95", "ulcer", "kurt", "worst_day")
        # For max_dd, var95, cvar95, worst_day: closer to 0 is better (these are negative)
        try:
            if higher_better:
                best_n = max(vals, key=lambda n: vals[n] if vals[n] is not None else -1e18)
            else:
                best_n = min(vals, key=lambda n: vals[n] if vals[n] is not None else 1e18)
        except (TypeError, ValueError):
            best_n = None
        cells = ""
        for n in strategies:
            v = vals[n]
            cls = "best" if n == best_n else ""
            cells += f"<td class='{cls}'>{fmt(v)}</td>"
        summary_rows += f"<tr><th>{label}</th>{cells}</tr>"

    # vs benchmark table
    vs_header = "".join(f"<th>{n}</th>" for n in strategies)
    vs_rows = ""
    for metric, key, fmt in [
        ("Beta",              "beta",       lambda v: fmt_num(v)),
        ("Alpha (annual)",    "alpha_ann",  lambda v: fmt_pct(v, sign=True)),
        ("Information Ratio", "ir",         lambda v: fmt_num(v)),
        ("Tracking Error",    "te",         lambda v: fmt_pct(v)),
        ("Correlation",       "corr",       lambda v: fmt_num(v)),
        ("Up-Capture",        "up_capture", lambda v: fmt_num(v)),
        ("Down-Capture",      "dn_capture", lambda v: fmt_num(v)),
    ]:
        cells = ""
        for n in strategies:
            cells += f"<td>{fmt(vs_bench[n].get(key) if vs_bench[n] else None)}</td>"
        vs_rows += f"<tr><th>{metric}</th>{cells}</tr>"

    # Year-by-year comparison
    all_years = sorted(set().union(*[set(y.index) for y in yearly.values()]))
    yr_header = "".join(f"<th>{n}</th><th>{n} DD</th>" for n in strategies)
    yr_rows = ""
    for y in all_years:
        cells = ""
        for n in strategies:
            df = yearly[n]
            if y in df.index:
                ret = df.loc[y, "ret"] * 100
                dd = df.loc[y, "dd"] * 100
                ret_color = "#2e7d32" if ret > 0 else "#c62828"
                cells += (f"<td style='color:{ret_color}'>{ret:+.2f}%</td>"
                          f"<td style='color:#c62828'>{dd:.1f}%</td>")
            else:
                cells += "<td>—</td><td>—</td>"
        yr_rows += f"<tr><th>{y}</th>{cells}</tr>"

    # Trailing returns
    tr_periods = ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y"]
    tr_rows = ""
    for period in tr_periods:
        cells = ""
        any_data = False
        for n in strategies:
            row = next((r for r in trailing[n] if r["period"] == period), None)
            if row:
                ret = row["ret"] * 100
                ret_color = "#2e7d32" if ret > 0 else "#c62828"
                ann = f" ({row['ann']*100:+.2f}% ann)" if row.get("ann") else ""
                cells += f"<td style='color:{ret_color}'>{ret:+.2f}%{ann}</td>"
                any_data = True
            else:
                cells += "<td>—</td>"
        if any_data:
            tr_rows += f"<tr><th>{period}</th>{cells}</tr>"

    # Trade quality side-by-side
    tq_metrics = [
        ("Closed Trades",   "n_closed",   lambda v: f"{int(v)}" if v else "—"),
        ("Win Rate",        "win_rate",   lambda v: fmt_pct(v)),
        ("Avg PnL/Trade",   "avg_pnl",    lambda v: fmt_pct(v, sign=True)),
        ("Median PnL",      "median_pnl", lambda v: fmt_pct(v, sign=True)),
        ("Avg Winner",      "avg_winner", lambda v: fmt_pct(v, sign=True)),
        ("Avg Loser",       "avg_loser",  lambda v: fmt_pct(v, sign=True)),
        ("Best Trade",      "best",       lambda v: fmt_pct(v, sign=True)),
        ("Worst Trade",     "worst",      lambda v: fmt_pct(v, sign=True)),
        ("Payoff Ratio",    "payoff",     lambda v: fmt_num(v)),
        ("Avg Holding (days)", "avg_hold", lambda v: f"{v:.1f}" if v else "—"),
    ]
    tq_rows = ""
    for label, key, fmt in tq_metrics:
        cells = ""
        for n in strategies:
            v = tradeq[n].get(key) if tradeq[n] else None
            cells += f"<td>{fmt(v)}</td>"
        tq_rows += f"<tr><th>{label}</th>{cells}</tr>"

    # Per-strategy holdings sections
    holdings_sections = ""
    for n, s in strategies.items():
        h = s["holdings"].copy()
        if h.empty:
            holdings_sections += f"<h3>{n} — Holdings: none</h3>"
            continue
        if "notional" in h.columns:
            h = h.sort_values("notional", ascending=False)
        rows = ""
        for _, r in h.iterrows():
            pnl = r.get("pnl_pct", 0)
            color = "#2e7d32" if pnl > 0 else "#c62828"
            rows += (
                f"<tr><td><strong>{r.get('symbol')}</strong></td>"
                f"<td>{int(r.get('shares', 0)):,}</td>"
                f"<td>₹{r.get('avg_cost', 0):,.2f}</td>"
                f"<td>₹{r.get('last_price', 0):,.2f}</td>"
                f"<td>₹{r.get('notional', 0):,.0f}</td>"
                f"<td>{r.get('contribution_pct', 0)*100:.2f}%</td>"
                f"<td style='color:{color}'>{pnl*100:+.2f}%</td>"
                f"<td>{r.get('entry_date', '')}</td>"
                f"<td>{int(r.get('holding_days', 0))}</td></tr>"
            )
        holdings_sections += f"""
        <h3>{n} — Current Holdings ({len(h)})</h3>
        <table>
          <thead><tr>
            <th>Symbol</th><th>Shares</th><th>Avg Cost</th><th>Last Price</th>
            <th>Notional</th><th>Weight</th><th>PnL</th>
            <th>Entry</th><th>Days</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
        """

    period_str = f"{period_start.strftime('%Y-%m-%d')} → {period_end.strftime('%Y-%m-%d')}"
    common_years = list(stats.values())[0]["years"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Strategy Comparison: L6 / OM25 v3 / TL25 v3</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
         background: #f5f5f5; color: #1a1a1a; margin: 0; padding: 20px; line-height: 1.55; }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  h1 {{ font-size: 28px; margin: 0 0 5px; }}
  h2 {{ font-size: 20px; color: #1a1a1a; margin: 30px 0 15px; padding-bottom: 8px; border-bottom: 2px solid #e0e0e0; }}
  h3 {{ font-size: 16px; color: #555; margin: 24px 0 12px; }}
  .meta {{ color: #666; font-size: 14px; margin-bottom: 25px; }}
  .meta span {{ display: inline-block; margin-right: 16px; padding: 4px 12px; background: #e0e0e0; border-radius: 4px; }}
  .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); padding: 24px; margin-bottom: 24px; }}
  .headline-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }}
  .headline-cell {{ padding: 16px; background: #fafafa; border-radius: 6px; }}
  .headline-cell.l6 {{ border-left: 4px solid #1976d2; }}
  .headline-cell.om25 {{ border-left: 4px solid #43a047; }}
  .headline-cell.tl25 {{ border-left: 4px solid #6a1b9a; }}
  .headline-cell .name {{ font-weight: 700; font-size: 16px; }}
  .headline-cell .kpi {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; font-size: 13px; }}
  .headline-cell .kpi .label {{ color: #888; }}
  .headline-cell .kpi .value {{ font-weight: 600; text-align: right; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #fafafa; font-weight: 600; color: #555; text-transform: uppercase; font-size: 11px; letter-spacing: 0.4px; }}
  td {{ font-variant-numeric: tabular-nums; }}
  tr:hover td {{ background: #fafafa; }}
  td.best {{ background: #e8f5e9; font-weight: 600; }}
  img {{ max-width: 100%; display: block; }}
  .footer {{ color: #999; font-size: 12px; text-align: center; margin: 30px 0; }}
  .config-list {{ list-style: none; padding: 0; columns: 2; }}
  .config-list li {{ padding: 3px 0; font-size: 12px; }}
  .note {{ font-size: 12px; color: #888; margin-top: 6px; }}
</style>
</head>
<body>
<div class="container">
  <h1>Strategy Comparison: L6 Momentum vs OM25 v3 vs TL25 v3</h1>
  <div class="meta">
    <span>Period: {period_str}</span>
    <span>{common_years:.2f} years</span>
    <span>Starting capital: ₹1,000,000 (rebased)</span>
    <span>Risk-free: 5% (Sharpe/Sortino)</span>
  </div>

  <div class="card">
    <h2>Headline Performance</h2>
    <div class="headline-grid">
      <div class="headline-cell l6">
        <div class="name" style="color:#1976d2">L6 Momentum</div>
        <div class="kpi">
          <div class="label">CAGR</div><div class="value">{stats['L6 Momentum']['cagr']*100:.2f}%</div>
          <div class="label">Sharpe</div><div class="value">{stats['L6 Momentum']['sharpe']:.2f}</div>
          <div class="label">Max DD</div><div class="value" style="color:#c62828">{stats['L6 Momentum']['max_dd']*100:.2f}%</div>
          <div class="label">Final value</div><div class="value">{fmt_inr(stats['L6 Momentum']['final_value'])}</div>
        </div>
      </div>
      <div class="headline-cell om25">
        <div class="name" style="color:#43a047">OM25 v3</div>
        <div class="kpi">
          <div class="label">CAGR</div><div class="value">{stats['OM25 v3']['cagr']*100:.2f}%</div>
          <div class="label">Sharpe</div><div class="value">{stats['OM25 v3']['sharpe']:.2f}</div>
          <div class="label">Max DD</div><div class="value" style="color:#c62828">{stats['OM25 v3']['max_dd']*100:.2f}%</div>
          <div class="label">Final value</div><div class="value">{fmt_inr(stats['OM25 v3']['final_value'])}</div>
        </div>
      </div>
      <div class="headline-cell tl25">
        <div class="name" style="color:#6a1b9a">TL25 v3</div>
        <div class="kpi">
          <div class="label">CAGR</div><div class="value">{stats['TL25 v3']['cagr']*100:.2f}%</div>
          <div class="label">Sharpe</div><div class="value">{stats['TL25 v3']['sharpe']:.2f}</div>
          <div class="label">Max DD</div><div class="value" style="color:#c62828">{stats['TL25 v3']['max_dd']*100:.2f}%</div>
          <div class="label">Final value</div><div class="value">{fmt_inr(stats['TL25 v3']['final_value'])}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>Strategy Configurations</h2>
    <table>
      <thead><tr><th>Aspect</th><th>L6 Momentum</th><th>OM25 v3</th><th>TL25 v3</th></tr></thead>
      <tbody>
        <tr><th>Universe</th><td>NSE 500 (499)</td><td>Nifty 250 (250)</td><td>NSE 500 (499)</td></tr>
        <tr><th>Signal</th><td>6mo return / realized vol</td><td>Upside-capture × Capture-ratio</td><td>Persistence + Drawdown + Momentum (3-comp)</td></tr>
        <tr><th>Cadence</th><td>Weekly (Thu signal → Mon exec)</td><td>Bi-weekly entry + weekly DD check</td><td>Bi-weekly entry + weekly rank + weekly DD</td></tr>
        <tr><th>Top-N</th><td>24</td><td>25</td><td>25</td></tr>
        <tr><th>Exit buffer</th><td>—</td><td>20</td><td>20</td></tr>
        <tr><th>Min hold</th><td>8 days</td><td>None</td><td>None</td></tr>
        <tr><th>Stop</th><td>None</td><td>20% DD from peak</td><td>20% DD from peak</td></tr>
        <tr><th>Regime tilt</th><td>—</td><td>NIFTY 100 100-DMA + 3d confirm</td><td>None (pure trend)</td></tr>
        <tr><th>Sizing</th><td>Equal 1/N, 7.5% cap</td><td>Equal 1/N, 7.5% cap</td><td>Equal 1/N, 7.5% cap</td></tr>
        <tr><th>Slippage</th><td>20 bps</td><td>20 bps</td><td>20 bps</td></tr>
      </tbody>
    </table>
  </div>

  <div class="card">
    <h2>Equity Curve (₹100 indexed)</h2>
    <img src="data:image/png;base64,{equity_chart}" alt="equity overlay">
    <p class="note">Each strategy rebased to ₹100 at {args.start}. Log scale.</p>
  </div>

  <div class="card">
    <h2>Risk &amp; Return Metrics</h2>
    <table>
      <thead><tr><th>Metric</th>{summary_header}</tr></thead>
      <tbody>{summary_rows}</tbody>
    </table>
    <p class="note">Green highlight = best across strategies. Sharpe/Sortino use rf=5%; daily VaR/CVaR at 95%.</p>
  </div>

  <div class="card">
    <h2>vs Nifty 100 — Beta · Alpha · Capture</h2>
    <table>
      <thead><tr><th>Metric</th>{vs_header}</tr></thead>
      <tbody>{vs_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Drawdowns</h2>
    <img src="data:image/png;base64,{dd_chart}" alt="drawdowns">
  </div>

  <div class="card">
    <h2>Rolling 1-Year Sharpe</h2>
    <img src="data:image/png;base64,{rs_chart}" alt="rolling sharpe">
  </div>

  <div class="card">
    <h2>Year-by-Year Returns &amp; Drawdowns</h2>
    <table>
      <thead><tr><th>Year</th>{yr_header}</tr></thead>
      <tbody>{yr_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Trailing Returns</h2>
    <table>
      <thead><tr><th>Period</th>{summary_header}</tr></thead>
      <tbody>{tr_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Trade Quality</h2>
    <table>
      <thead><tr><th>Metric</th>{summary_header}</tr></thead>
      <tbody>{tq_rows}</tbody>
    </table>
    <p class="note">All trade metrics computed from FIFO round-trip matching across the slice with 20 bps slippage applied to entry and exit.</p>
  </div>

  <div class="card">
    <h2>Monthly Returns Heatmaps</h2>
    <h3 style="color:#1976d2">L6 Momentum</h3>
    <img src="data:image/png;base64,{heatmap_charts['L6 Momentum']}" alt="L6 monthly">
    <h3 style="color:#43a047">OM25 v3</h3>
    <img src="data:image/png;base64,{heatmap_charts['OM25 v3']}" alt="OM25 monthly">
    <h3 style="color:#6a1b9a">TL25 v3</h3>
    <img src="data:image/png;base64,{heatmap_charts['TL25 v3']}" alt="TL25 monthly">
  </div>

  <div class="card">
    <h2>Current Holdings (as of {period_end.strftime('%Y-%m-%d')})</h2>
    {holdings_sections}
  </div>

  <div class="footer">Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}
    · Comparative report across L6 momentum, OM25 v3, TL25 v3
    · Common slice: {args.start} → {period_end.strftime('%Y-%m-%d')}</div>
</div>
</body>
</html>"""

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html)
    print(f"[wrote] {args.output}")
    for name, st in stats.items():
        print(f"  {name:14s} CAGR={st['cagr']*100:.2f}%  Sharpe={st['sharpe']:.2f}  "
              f"MaxDD={st['max_dd']*100:.2f}%  Final={fmt_inr(st['final_value'])}")


if __name__ == "__main__":
    main()
