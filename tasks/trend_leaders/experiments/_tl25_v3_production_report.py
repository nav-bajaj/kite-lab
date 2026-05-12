"""TL25 v3 production-config backtest from 2009-01-01 + comprehensive HTML report.

V3 LOCKED-IN config (post 2026 OOS retune):
  Universe:        NSE 500
  Cadence:         Bi-weekly entry, weekly rank-exit + weekly DD-stop checks
  Score:           0.40 × Persistence + 0.20 × Drawdown-Control + 0.40 × Momentum
  Eligibility:     Close>200DMA & 50DMA>200DMA & 200DMA rising over 20d
  Windows:         persistence 252d, drawdown 126d squared, momentum 63d
  Top-N:           25, exit_buffer 20 (drop below rank 45)
  Stop:            20% fixed DD from peak (weekly check), no DMA exit
  Sizing:          Equal 1/N, max 7.5%, drift after entry
  Slippage:        20 bps (OHLC/4 next-day pricing)
  Regime tilt:     None
"""
from __future__ import annotations

import base64
import io
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score, V3_LOCKED


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
START_DATE = pd.Timestamp("2017-01-01")  # OOS start — IS was 2009-09 → 2016-12

INDICES = {
    "Nifty 50":            ROOT / "indices_data_historical/NIFTY_50.csv",
    "Nifty 100":           ROOT / "indices_data_historical/NIFTY_100.csv",
    "Nifty LargeMid 250":  ROOT / "indices_data_historical/NIFTY_LARGEMID250.csv",
    "Nifty 500":           ROOT / "indices_data_historical/NIFTY_500.csv",
}
INDEX_COLORS = {
    "TL25":                "#6a1b9a",
    "Nifty 50":            "#888888",
    "Nifty 100":           "#bbbbbb",
    "Nifty LargeMid 250":  "#fb8c00",
    "Nifty 500":           "#43a047",
}


def fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def compute_stats(values: pd.Series, dates: pd.Series) -> dict:
    if len(values) < 2 or values.iloc[0] <= 0:
        return {}
    rets = values.pct_change().dropna()
    yrs = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1e-9)
    cagr = (values.iloc[-1] / values.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    rf = 0.05
    excess_ret = cagr - rf
    sharpe = excess_ret / vol if vol > 0 else 0
    downside = rets[rets < 0].std() * math.sqrt(252)
    sortino = excess_ret / downside if downside > 0 else 0
    cum = values / values.cummax()
    mdd = cum.min() - 1
    calmar = cagr / abs(mdd) if mdd != 0 else 0
    gains = rets[rets > 0].sum()
    losses = abs(rets[rets < 0].sum())
    omega = gains / losses if losses > 0 else 0
    var95 = rets.quantile(0.05)
    cvar95 = rets[rets <= var95].mean()
    tail = abs(rets.quantile(0.95) / var95) if var95 != 0 else 0
    dd_series = ((values / values.cummax()) - 1) * 100
    ulcer = math.sqrt((dd_series ** 2).mean())
    skew = rets.skew()
    kurt = rets.kurt()
    hit_daily = (rets > 0).mean()
    best = rets.max()
    worst = rets.min()
    return dict(
        cagr=cagr, vol=vol, sharpe=sharpe, sortino=sortino,
        max_dd=mdd, calmar=calmar, omega=omega, ulcer=ulcer,
        var95=var95, cvar95=cvar95, tail_ratio=tail,
        skew=skew, kurt=kurt, hit_daily=hit_daily,
        best_day=best, worst_day=worst,
        total_ret=values.iloc[-1] / values.iloc[0] - 1,
        years=yrs,
    )


def compute_vs_index(port_rets: pd.Series, idx_rets: pd.Series) -> dict:
    df = pd.concat([port_rets, idx_rets], axis=1, keys=["p", "i"]).dropna()
    if len(df) < 30:
        return {}
    p, i = df["p"], df["i"]
    cov = np.cov(p, i, ddof=0)
    beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 0
    rf_d = 0.05 / 252
    alpha_ann = (p.mean() - rf_d) * 252 - beta * ((i.mean() - rf_d) * 252)
    diff = p - i
    te = diff.std() * math.sqrt(252)
    ir = (diff.mean() * 252) / te if te > 0 else 0
    corr = p.corr(i)
    up_mask = i > 0
    dn_mask = i < 0
    up_cap = (p[up_mask].mean() / i[up_mask].mean()) if up_mask.sum() > 0 and i[up_mask].mean() > 0 else 0
    dn_cap = (p[dn_mask].mean() / i[dn_mask].mean()) if dn_mask.sum() > 0 and i[dn_mask].mean() < 0 else 0
    return dict(beta=beta, alpha_ann=alpha_ann, ir=ir, te=te,
                corr=corr, up_capture=up_cap, dn_capture=dn_cap, n_obs=len(df))


def yearly_returns(values: pd.Series, dates: pd.Series) -> pd.DataFrame:
    s = pd.Series(values.values, index=pd.DatetimeIndex(dates))
    rows = []
    for y, gp in s.groupby(s.index.year):
        if len(gp) < 5: continue
        ret = gp.iloc[-1] / gp.iloc[0] - 1
        cum = gp / gp.cummax()
        dd = cum.min() - 1
        rows.append({"year": y, "ret": ret, "dd": dd})
    return pd.DataFrame(rows).set_index("year")


def monthly_heatmap_data(values: pd.Series, dates: pd.Series) -> pd.DataFrame:
    s = pd.Series(values.values, index=pd.DatetimeIndex(dates))
    monthly = s.resample("ME").last().pct_change().dropna()
    mat = pd.DataFrame(index=range(monthly.index.year.min(), monthly.index.year.max() + 1),
                        columns=range(1, 13), dtype=float)
    for date, val in monthly.items():
        mat.loc[date.year, date.month] = val
    return mat


def main():
    print(f"[load] panels...", flush=True)
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_panel = close_panel.pct_change().rolling(20).std()
    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= START_DATE]
    entry_dates = biweekly_fri[biweekly_fri >= START_DATE]

    universe = load_universe(ROOT / V3_LOCKED["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"[compute] TL25 panels (eligibility, persistence, drawdown, momentum)...", flush=True)
    panels = build_tl25_panels(
        close_uni,
        dma_short=V3_LOCKED["dma_short"],
        dma_long=V3_LOCKED["dma_long"],
        dma_persist_ref=V3_LOCKED["dma_persist_ref"],
        persistence_window=V3_LOCKED["persistence_window"],
        drawdown_window=V3_LOCKED["drawdown_window"],
        drawdown_concavity=V3_LOCKED["drawdown_concavity"],
        momentum_window=V3_LOCKED["momentum_window"],
    )
    score_fn = make_tl25_score(
        panels,
        w_persistence=V3_LOCKED["w_persistence"],
        w_drawdown=V3_LOCKED["w_drawdown"],
        w_momentum=V3_LOCKED["w_momentum"],
    )

    print(f"[run] TL25 v3 from {START_DATE.date()} ...", flush=True)
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_panel,
        top_n=V3_LOCKED["top_n"], exit_buffer=V3_LOCKED["exit_buffer"],
        max_weight=V3_LOCKED["max_weight"], slippage=V3_LOCKED["slippage"],
        atr_mult=V3_LOCKED["atr_mult"], atr_min_floor=V3_LOCKED["atr_min_floor"],
        use_trailing_stop=V3_LOCKED["use_trailing_stop"],
        use_dma_exit=V3_LOCKED["use_dma_exit"],
        weekly_rank_check=V3_LOCKED["weekly_rank_check"],
        regime_panel=V3_LOCKED["regime_panel"],
        bear_exposure=V3_LOCKED["bear_exposure"],
    )
    eq = res["equity"].copy()
    trades = res["trades"].copy()
    exits = res["exits"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.sort_values("date").reset_index(drop=True)
    trades["date"] = pd.to_datetime(trades["date"])
    trades = trades.sort_values("date").reset_index(drop=True)

    # ======== Index series ========
    print(f"[load] indices...", flush=True)
    idx_series = {}
    for name, path in INDICES.items():
        if not path.exists():
            continue
        idf = pd.read_csv(path, parse_dates=["date"])
        idf["date"] = pd.to_datetime(idf["date"]).dt.tz_localize(None).dt.normalize()
        idf = idf.sort_values("date").set_index("date")["close"].astype(float)
        idx_series[name] = idf

    port_dates = eq["date"]
    port_pv = eq["pv"].astype(float)
    port_dd = (port_pv / port_pv.cummax() - 1) * 100
    port_rets = port_pv.pct_change()
    port_rets.index = port_dates

    norm_port = 100.0 * port_pv / port_pv.iloc[0]
    norm_idx = {}
    for name, s in idx_series.items():
        aligned = s.reindex(port_dates).ffill()
        first_valid = aligned.first_valid_index()
        if first_valid is None:
            continue
        first_val = aligned.loc[first_valid]
        norm_idx[name] = (100.0 * aligned / first_val)

    # ======== Stats ========
    print(f"[stats]...", flush=True)
    stats_port = compute_stats(norm_port, port_dates)
    stats_idx = {}
    for name, s in norm_idx.items():
        s_clean = s.dropna()
        if len(s_clean) < 30:
            continue
        d_clean = pd.Series(s_clean.index)
        s_clean_reset = pd.Series(s_clean.values)
        stats_idx[name] = compute_stats(s_clean_reset, d_clean)

    vs_idx = {}
    for name, s in idx_series.items():
        i_rets = s.reindex(port_dates).ffill().pct_change()
        i_rets.index = port_dates
        vs_idx[name] = compute_vs_index(port_rets, i_rets)

    # ======== Charts ========
    print(f"[chart] equity ...", flush=True)
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(port_dates, norm_port, label="TL25",
            color=INDEX_COLORS["TL25"], linewidth=2.4)
    for name, s in norm_idx.items():
        ax.plot(s.index, s.values, label=name,
                color=INDEX_COLORS.get(name, "#666"),
                linewidth=1.0, alpha=0.85)
    ax.set_yscale("log")
    ax.set_title(f"TL25 vs Indices (₹100 indexed at start, log scale)",
                 fontsize=14, fontweight="bold")
    ax.set_ylabel("Value")
    ax.legend(loc="upper left", framealpha=0.95)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.autofmt_xdate()
    equity_chart = fig_to_b64(fig)
    plt.close(fig)

    print(f"[chart] drawdown ...", flush=True)
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.fill_between(port_dates, port_dd.values, 0,
                    color="#6a1b9a", alpha=0.20)
    ax.plot(port_dates, port_dd.values, label="TL25",
            color=INDEX_COLORS["TL25"], linewidth=1.8)
    for name, s in norm_idx.items():
        idx_dd = (s / s.cummax() - 1) * 100
        ax.plot(s.index, idx_dd.values, label=name,
                color=INDEX_COLORS.get(name, "#666"),
                linewidth=0.9, alpha=0.85)
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

    print(f"[chart] rolling Sharpe ...", flush=True)
    fig, ax = plt.subplots(figsize=(13, 4))
    rs = (port_rets.rolling(252).mean() * 252) / (port_rets.rolling(252).std() * np.sqrt(252))
    ax.plot(rs.index, rs.values, color=INDEX_COLORS["TL25"], linewidth=1.8, label="TL25")
    for name in ["Nifty 100", "Nifty 500"]:
        if name in idx_series:
            ir = idx_series[name].reindex(port_dates).ffill().pct_change()
            ir.index = port_dates
            rs2 = (ir.rolling(252).mean() * 252) / (ir.rolling(252).std() * np.sqrt(252))
            ax.plot(rs2.index, rs2.values, color=INDEX_COLORS.get(name, "#666"),
                    linewidth=1.0, alpha=0.85, label=name)
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

    print(f"[chart] monthly heatmap ...", flush=True)
    mh = monthly_heatmap_data(norm_port, port_dates)
    fig, ax = plt.subplots(figsize=(13, max(3.5, 0.45 * len(mh))))
    vals = (mh.values * 100).astype(float)
    im = ax.imshow(vals, aspect="auto", cmap="RdYlGn", vmin=-25, vmax=25)
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
                        ha="center", va="center", fontsize=9,
                        color="black" if abs(v) < 12 else "white")
    ax.set_title("TL25 Monthly Returns (%)", fontsize=14, fontweight="bold")
    plt.colorbar(im, ax=ax, fraction=0.02)
    heatmap_chart = fig_to_b64(fig)
    plt.close(fig)

    # ======== OOS sub-window table ========
    eq_indexed = eq.set_index("date")["pv"]
    def window_stats(start, end, label):
        sub = eq_indexed.loc[(eq_indexed.index >= start) & (eq_indexed.index <= end)]
        if len(sub) < 5:
            return {"window": label, "n": len(sub)}
        d = pd.Series(sub.index); v = pd.Series(sub.values)
        s = compute_stats(v, d)
        s["window"] = label
        s["yrs"] = (sub.index[-1] - sub.index[0]).days / 365.25
        return s

    windows = [
        ("OOS_A (2017-19)", "2017-01-01", "2019-12-31"),
        ("OOS_B (2020-22)", "2020-01-01", "2022-12-31"),
        ("OOS_C (2023-26)", "2023-01-01", str(port_dates.iloc[-1].date())),
        ("OOS_full",        "2017-01-01", str(port_dates.iloc[-1].date())),
    ]
    win_rows = []
    for label, start, end in windows:
        win_rows.append(window_stats(pd.Timestamp(start), pd.Timestamp(end), label))

    # ======== Yearly table ========
    yr_om = yearly_returns(norm_port, port_dates)
    yr_idx_dict = {}
    for name, s in norm_idx.items():
        s_clean = s.dropna()
        if len(s_clean) < 30: continue
        d_clean = pd.Series(s_clean.index)
        s_clean_reset = pd.Series(s_clean.values)
        yr_idx_dict[name] = yearly_returns(s_clean_reset, d_clean)

    yr_table = pd.DataFrame()
    yr_table["TL25"] = (yr_om["ret"] * 100).round(2)
    yr_table["TL25 DD"] = (yr_om["dd"] * 100).round(1)
    for col in INDICES:
        if col in yr_idx_dict:
            yr_table[col] = (yr_idx_dict[col]["ret"] * 100).round(2)
            yr_table[f"vs {col}"] = (yr_table["TL25"] - yr_table[col]).round(2)

    # ======== Current holdings ========
    print(f"[holdings & recent PnL]...", flush=True)
    held = {}
    for _, tr in trades.iterrows():
        sym = tr["symbol"]; side = tr["side"]
        sh = tr["shares"]; price = tr["price"]
        if side == "BUY":
            if sym not in held:
                held[sym] = {"shares": 0, "cost_basis": 0,
                              "entry_date": tr["date"], "entry_price": price}
            held[sym]["shares"] += sh
            held[sym]["cost_basis"] += sh * price * (1 + 0.002)
        else:
            if sym in held:
                if held[sym]["shares"] > 0:
                    cost_per_share = held[sym]["cost_basis"] / held[sym]["shares"]
                else:
                    cost_per_share = 0
                held[sym]["shares"] -= sh
                held[sym]["cost_basis"] -= sh * cost_per_share
                if held[sym]["shares"] <= 0:
                    held.pop(sym, None)

    last_date = port_dates.iloc[-1]
    holdings_rows = []
    total_value = 0
    for sym, info in held.items():
        if info["shares"] <= 0: continue
        last_close = close_panel.loc[last_date, sym] if sym in close_panel.columns else None
        if last_close is None or pd.isna(last_close): continue
        notional = info["shares"] * last_close
        avg_cost = info["cost_basis"] / info["shares"] if info["shares"] > 0 else 0
        pnl = (last_close / avg_cost - 1) if avg_cost > 0 else 0
        days = (last_date - info["entry_date"]).days
        holdings_rows.append({
            "symbol": sym, "shares": info["shares"], "avg_cost": avg_cost,
            "last_price": last_close, "notional": notional,
            "pnl_pct": pnl, "entry_date": info["entry_date"].date(),
            "days_held": days,
        })
        total_value += notional

    pv_now = port_pv.iloc[-1]
    cash_now = pv_now - total_value
    holdings_df = pd.DataFrame(holdings_rows).sort_values("notional", ascending=False)
    if not holdings_df.empty:
        holdings_df["weight_pct"] = (holdings_df["notional"] / pv_now * 100).round(2)

    last10 = eq.tail(11).copy()
    last10["daily_pnl_inr"] = last10["pv"].diff()
    last10["daily_pnl_pct"] = last10["pv"].pct_change() * 100
    last10 = last10.tail(10)
    last10_total_pnl = last10["daily_pnl_inr"].sum()
    last10_total_pct = (last10["pv"].iloc[-1] / last10["pv"].iloc[0] - 1) * 100

    # ======== Trade-quality metrics ========
    closed = exits.copy() if not exits.empty else pd.DataFrame()
    trade_stats = {}
    if not closed.empty and "pnl_pct" in closed.columns:
        pnls = closed["pnl_pct"].dropna()
        winners = pnls[pnls > 0]
        losers = pnls[pnls <= 0]
        trade_stats = dict(
            n_closed=len(pnls),
            win_rate=len(winners) / len(pnls) if len(pnls) else 0,
            avg_pnl=pnls.mean(),
            median_pnl=pnls.median(),
            avg_winner=winners.mean() if len(winners) else 0,
            avg_loser=losers.mean() if len(losers) else 0,
            best_trade=pnls.max(),
            worst_trade=pnls.min(),
            payoff=(winners.mean() / abs(losers.mean())) if len(winners) and len(losers) and losers.mean() != 0 else 0,
            avg_hold=closed["hold_days"].mean() if "hold_days" in closed.columns else 0,
        )

    # ======== Build HTML ========
    print(f"[render] HTML ...", flush=True)

    def fmt_pct(v, sign=False):
        if v is None or pd.isna(v): return "—"
        return f"{v*100:+.2f}%" if sign else f"{v*100:.2f}%"
    def fmt_num(v, d=2):
        if v is None or pd.isna(v): return "—"
        return f"{v:.{d}f}"
    def fmt_inr(v):
        if v is None or pd.isna(v): return "—"
        return f"₹{v:,.0f}"

    cols_show = ["TL25"] + [c for c in INDICES if c in stats_idx]
    stats_header = "".join(f"<th>{c}</th>" for c in cols_show)
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
    ]
    stats_rows = ""
    for label, key, fmt in metric_defs:
        cells = ""
        for col in cols_show:
            src = stats_port if col == "TL25" else stats_idx.get(col, {})
            cells += f"<td>{fmt(src.get(key))}</td>"
        stats_rows += f"<tr><th>{label}</th>{cells}</tr>"

    vs_rows = ""
    for col in INDICES:
        v = vs_idx.get(col, {})
        if not v: continue
        vs_rows += (
            f"<tr><th>{col}</th>"
            f"<td>{fmt_num(v.get('beta'))}</td>"
            f"<td>{fmt_pct(v.get('alpha_ann'), sign=True)}</td>"
            f"<td>{fmt_num(v.get('ir'))}</td>"
            f"<td>{fmt_pct(v.get('te'))}</td>"
            f"<td>{fmt_num(v.get('corr'))}</td>"
            f"<td>{fmt_num(v.get('up_capture'))}</td>"
            f"<td>{fmt_num(v.get('dn_capture'))}</td>"
            f"</tr>"
        )

    # IS/OOS window table
    win_header = "<th>Window</th><th>Years</th><th>CAGR</th><th>Vol</th><th>Sharpe</th><th>Sortino</th><th>Max DD</th><th>Calmar</th>"
    win_rows_html = ""
    for w in win_rows:
        if "cagr" not in w:
            continue
        bg = "#e8f5e9" if w["window"] == "OOS_full" else ""
        style = f"background:{bg};" if bg else ""
        win_rows_html += (
            f"<tr style='{style}'>"
            f"<th>{w['window']}</th>"
            f"<td>{w['yrs']:.2f}</td>"
            f"<td>{w['cagr']*100:+.2f}%</td>"
            f"<td>{w['vol']*100:.2f}%</td>"
            f"<td>{w['sharpe']:.2f}</td>"
            f"<td>{w['sortino']:.2f}</td>"
            f"<td style='color:#c62828'>{w['max_dd']*100:.2f}%</td>"
            f"<td>{w['calmar']:.2f}</td>"
            f"</tr>"
        )

    yr_cols_header = "".join(f"<th>{c}</th>" for c in yr_table.columns)
    yr_rows = ""
    for y in yr_table.index:
        cells = ""
        for col in yr_table.columns:
            v = yr_table.loc[y, col]
            if pd.isna(v):
                cells += f"<td>—</td>"
            else:
                color = "#2e7d32" if v > 0 else "#c62828" if v < 0 else "#666"
                if col.startswith("vs "):
                    cells += f"<td class='delta' style='color:{color}'>{v:+.2f}pp</td>"
                elif col == "TL25 DD":
                    cells += f"<td style='color:#c62828'>{v:.1f}%</td>"
                else:
                    cells += f"<td style='color:{color}'>{v:+.2f}%</td>"
        yr_rows += f"<tr><th>{y}</th>{cells}</tr>"

    holdings_table_rows = ""
    if not holdings_df.empty:
        for _, h in holdings_df.iterrows():
            color = "#2e7d32" if h["pnl_pct"] > 0 else "#c62828"
            holdings_table_rows += (
                f"<tr>"
                f"<td><strong>{h['symbol']}</strong></td>"
                f"<td>{int(h['shares']):,}</td>"
                f"<td>₹{h['avg_cost']:,.2f}</td>"
                f"<td>₹{h['last_price']:,.2f}</td>"
                f"<td>₹{h['notional']:,.0f}</td>"
                f"<td>{h['weight_pct']:.2f}%</td>"
                f"<td style='color:{color}'>{h['pnl_pct']*100:+.2f}%</td>"
                f"<td>{h['entry_date']}</td>"
                f"<td>{h['days_held']}</td>"
                f"</tr>"
            )

    last10_rows = ""
    for _, r in last10.iterrows():
        d_pnl = r["daily_pnl_inr"]
        d_pct = r["daily_pnl_pct"]
        color = "#2e7d32" if d_pnl > 0 else "#c62828" if d_pnl < 0 else "#666"
        last10_rows += (
            f"<tr>"
            f"<td>{r['date'].strftime('%Y-%m-%d (%a)')}</td>"
            f"<td>{fmt_inr(r['pv'])}</td>"
            f"<td style='color:{color}'>{'₹+' if d_pnl > 0 else '₹'}{d_pnl:,.0f}</td>"
            f"<td style='color:{color}'>{d_pct:+.2f}%</td>"
            f"</tr>"
        )

    exit_breakdown_rows = ""
    if not exits.empty and "reason" in exits.columns:
        for r, n in exits["reason"].value_counts().items():
            sub = exits[exits["reason"] == r]
            avg_pnl = (sub["pnl_pct"].mean() * 100) if "pnl_pct" in sub.columns else 0
            hit = (sub["pnl_pct"] > 0).mean() * 100 if "pnl_pct" in sub.columns else 0
            avg_hold = sub["hold_days"].mean() if "hold_days" in sub.columns else 0
            exit_breakdown_rows += (
                f"<tr><td>{r}</td><td>{n}</td><td>{n/len(exits)*100:.1f}%</td>"
                f"<td>{avg_pnl:+.2f}%</td><td>{hit:.1f}%</td><td>{avg_hold:.0f}</td></tr>"
            )

    trade_q_html = ""
    if trade_stats:
        trade_q_html = f"""
    <div class="summary-grid">
      <div class="summary-cell">
        <div class="label">Closed Trades</div>
        <div class="value">{trade_stats['n_closed']}</div>
      </div>
      <div class="summary-cell {'green' if trade_stats['win_rate'] >= 0.45 else 'amber'}">
        <div class="label">Win Rate</div>
        <div class="value">{trade_stats['win_rate']*100:.1f}%</div>
      </div>
      <div class="summary-cell {'green' if trade_stats['avg_pnl'] > 0 else 'red'}">
        <div class="label">Avg PnL per Trade</div>
        <div class="value">{trade_stats['avg_pnl']*100:+.2f}%</div>
      </div>
      <div class="summary-cell">
        <div class="label">Median PnL</div>
        <div class="value">{trade_stats['median_pnl']*100:+.2f}%</div>
      </div>
      <div class="summary-cell green">
        <div class="label">Avg Winner</div>
        <div class="value">{trade_stats['avg_winner']*100:+.2f}%</div>
      </div>
      <div class="summary-cell red">
        <div class="label">Avg Loser</div>
        <div class="value">{trade_stats['avg_loser']*100:+.2f}%</div>
      </div>
      <div class="summary-cell">
        <div class="label">Payoff Ratio</div>
        <div class="value">{trade_stats['payoff']:.2f}</div>
      </div>
      <div class="summary-cell">
        <div class="label">Avg Holding Days</div>
        <div class="value">{trade_stats['avg_hold']:.1f}</div>
      </div>
    </div>
    """

    n_holdings = len(holdings_df)
    cash_pct = (cash_now / pv_now * 100) if pv_now > 0 else 0
    period_str = f"{port_dates.iloc[0].strftime('%Y-%m-%d')} → {port_dates.iloc[-1].strftime('%Y-%m-%d')}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>TL25 v3 Production Backtest Report (OOS)</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "SF Pro Text", "Segoe UI", Roboto, sans-serif;
         background: #f5f5f5; color: #1a1a1a; margin: 0; padding: 20px; line-height: 1.55; }}
  .container {{ max-width: 1400px; margin: 0 auto; }}
  h1 {{ font-size: 28px; margin: 0 0 5px; }}
  h2 {{ font-size: 20px; color: #6a1b9a; margin: 30px 0 15px; padding-bottom: 8px; border-bottom: 2px solid #e0e0e0; }}
  .meta {{ color: #666; font-size: 14px; margin-bottom: 25px; }}
  .meta span {{ display: inline-block; margin-right: 16px; padding: 4px 12px; background: #e0e0e0; border-radius: 4px; }}
  .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); padding: 24px; margin-bottom: 24px; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }}
  .summary-cell {{ padding: 16px; background: #fafafa; border-radius: 6px; border-left: 3px solid #6a1b9a; }}
  .summary-cell .label {{ font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }}
  .summary-cell .value {{ font-size: 24px; font-weight: 600; color: #1a1a1a; margin-top: 4px; }}
  .summary-cell.green {{ border-left-color: #2e7d32; }}
  .summary-cell.red {{ border-left-color: #c62828; }}
  .summary-cell.amber {{ border-left-color: #f57c00; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
  th {{ background: #fafafa; font-weight: 600; color: #555; text-transform: uppercase; font-size: 11px; letter-spacing: 0.4px; }}
  td {{ font-variant-numeric: tabular-nums; }}
  tr:hover td {{ background: #fafafa; }}
  .table-sm td, .table-sm th {{ padding: 6px 10px; font-size: 12px; }}
  .delta {{ font-weight: 600; }}
  img {{ max-width: 100%; display: block; }}
  .config-list {{ list-style: none; padding: 0; columns: 2; }}
  .config-list li {{ padding: 4px 0; font-size: 13px; }}
  .config-list strong {{ color: #6a1b9a; }}
  .footer {{ color: #999; font-size: 12px; text-align: center; margin: 30px 0; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 16px; }}
  .note {{ font-size: 12px; color: #888; margin-top: 6px; }}
</style>
</head>
<body>
<div class="container">
  <h1>TL25 v3 Production Backtest — OOS Only</h1>
  <div class="meta">
    <span>OOS Period: {period_str}</span>
    <span>{stats_port['years']:.2f} years</span>
    <span>Universe: NSE 500</span>
    <span>Cadence: Bi-weekly entry · Weekly rank-exit</span>
    <span style="background:#e8f5e9">Out-of-Sample (tuned on 2009-09 → 2016-12)</span>
  </div>

  <div class="card">
    <h2>Headline Performance</h2>
    <div class="summary-grid">
      <div class="summary-cell green">
        <div class="label">CAGR</div>
        <div class="value">{stats_port['cagr']*100:.2f}%</div>
      </div>
      <div class="summary-cell green">
        <div class="label">Sharpe Ratio</div>
        <div class="value">{stats_port['sharpe']:.2f}</div>
      </div>
      <div class="summary-cell red">
        <div class="label">Max Drawdown</div>
        <div class="value">{stats_port['max_dd']*100:.2f}%</div>
      </div>
      <div class="summary-cell">
        <div class="label">Total Return</div>
        <div class="value">{stats_port['total_ret']*100:.0f}%</div>
      </div>
    </div>
  </div>

  <div class="card">
    <h2>TL25 v3 Configuration (Locked May 2026)</h2>
    <ul class="config-list">
      <li><strong>Universe:</strong> NSE 500 ({len(cols)} symbols)</li>
      <li><strong>Cadence:</strong> Bi-weekly entry + weekly rank-exit + weekly DD-stop checks</li>
      <li><strong>Score weights:</strong> 0.40 × Persistence + 0.20 × Drawdown-Control + 0.40 × Momentum</li>
      <li><strong>Persistence:</strong> % of 252d where Close &gt; 100 DMA</li>
      <li><strong>Drawdown-Control:</strong> (Close / 126d rolling high)²</li>
      <li><strong>Momentum:</strong> 63-day return, percentile-ranked among eligible</li>
      <li><strong>Eligibility:</strong> Close&gt;200DMA &amp; 50DMA&gt;200DMA &amp; 200DMA rising 20d</li>
      <li><strong>Top-N:</strong> 25 stocks · Exit buffer: 20 (drop below rank 45)</li>
      <li><strong>Drawdown stop:</strong> 20% from peak (weekly check, no DMA exit)</li>
      <li><strong>Sizing:</strong> Equal 1/N, 7.5% max per stock, drift after entry</li>
      <li><strong>Slippage:</strong> 20 bps (OHLC/4 next-day pricing)</li>
      <li><strong>Total trades:</strong> {(trades['side']=='BUY').sum()} buys / {(trades['side']=='SELL').sum()} sells</li>
    </ul>
  </div>

  <div class="card">
    <h2>Equity Curve vs Indices</h2>
    <img src="data:image/png;base64,{equity_chart}" alt="equity curve">
    <p class="note">Each line indexed to 100 at its first valid date in the TL25 period.
       Nifty LargeMid 250 inception: 2021. Nifty 500 data starts 2015 in our panel.</p>
  </div>

  <div class="card">
    <h2>OOS Sub-Window Breakdown</h2>
    <table>
      <thead><tr>{win_header}</tr></thead>
      <tbody>{win_rows_html}</tbody>
    </table>
    <p class="note">OOS_A/B/C are the three out-of-sample sub-windows (each ~3 years, spanning different market regimes). OOS_full (highlighted green) is the combined OOS period — this is what you'd actually have earned holding the strategy since 2017. Strategy was tuned on 2009-09 → 2016-12 (not shown). Pass criteria: OOS_full Sharpe ≥1.0, all sub-window Sharpes ≥0.7, OOS DD ≥-45%.</p>
  </div>

  <div class="card">
    <h2>Risk &amp; Return Metrics</h2>
    <table>
      <thead><tr><th>Metric</th>{stats_header}</tr></thead>
      <tbody>{stats_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>TL25 vs Each Index — Beta, Alpha, Capture</h2>
    <table>
      <thead><tr>
        <th>Index</th>
        <th>Beta</th>
        <th>Alpha (ann)</th>
        <th>Information Ratio</th>
        <th>Tracking Error</th>
        <th>Correlation</th>
        <th>Up-Capture</th>
        <th>Down-Capture</th>
      </tr></thead>
      <tbody>{vs_rows}</tbody>
    </table>
    <p class="note">All figures use daily returns over the overlapping period. Up/Down-capture &gt; 1 means TL25 captures more than 100% of index up/down day returns.</p>
  </div>

  <div class="card">
    <h2>Drawdowns</h2>
    <img src="data:image/png;base64,{dd_chart}" alt="drawdowns">
  </div>

  <div class="card">
    <h2>Year-by-Year Returns vs Indices</h2>
    <table class="table-sm">
      <thead><tr><th>Year</th>{yr_cols_header}</tr></thead>
      <tbody>{yr_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Rolling 1-Year Sharpe</h2>
    <img src="data:image/png;base64,{rs_chart}" alt="rolling sharpe">
  </div>

  <div class="card">
    <h2>TL25 Monthly Returns Heatmap</h2>
    <img src="data:image/png;base64,{heatmap_chart}" alt="monthly heatmap">
  </div>

  <div class="card">
    <h2>Trade Quality</h2>
    {trade_q_html}
    <p class="note">All closed-trade metrics are net-of-slippage (effective exit price ÷ effective entry price − 1).</p>
  </div>

  <div class="card">
    <h2>Current Holdings (as of {last_date.strftime('%Y-%m-%d')})</h2>
    <div class="kpi-row">
      <div class="summary-cell">
        <div class="label">Holdings count</div>
        <div class="value">{n_holdings}</div>
      </div>
      <div class="summary-cell">
        <div class="label">Total invested</div>
        <div class="value">{fmt_inr(total_value)}</div>
      </div>
      <div class="summary-cell {'green' if cash_pct < 5 else 'amber'}">
        <div class="label">Cash %</div>
        <div class="value">{cash_pct:.2f}%</div>
      </div>
    </div>
    <table>
      <thead><tr>
        <th>Symbol</th><th>Shares</th><th>Avg Cost</th><th>Last Price</th>
        <th>Notional</th><th>Weight</th><th>Position PnL</th>
        <th>Entry Date</th><th>Days Held</th>
      </tr></thead>
      <tbody>{holdings_table_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Last 10 Trading Days PnL</h2>
    <div class="kpi-row">
      <div class="summary-cell {'green' if last10_total_pnl > 0 else 'red'}">
        <div class="label">10-day total PnL</div>
        <div class="value">{'+' if last10_total_pnl > 0 else ''}{fmt_inr(last10_total_pnl)}</div>
      </div>
      <div class="summary-cell {'green' if last10_total_pct > 0 else 'red'}">
        <div class="label">10-day total %</div>
        <div class="value">{last10_total_pct:+.2f}%</div>
      </div>
      <div class="summary-cell">
        <div class="label">Current portfolio value</div>
        <div class="value">{fmt_inr(pv_now)}</div>
      </div>
    </div>
    <table>
      <thead><tr><th>Date</th><th>Portfolio Value</th><th>Daily PnL (₹)</th><th>Daily PnL (%)</th></tr></thead>
      <tbody>{last10_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Exit Breakdown</h2>
    <table>
      <thead><tr>
        <th>Reason</th><th>Count</th><th>Share</th><th>Avg PnL</th><th>Hit Rate</th><th>Avg Hold (days)</th>
      </tr></thead>
      <tbody>{exit_breakdown_rows}</tbody>
    </table>
    <p class="note">rank = biweekly rank-out at rebalance · rank_weekly = rank-out on non-rebal Fridays · atr_stop = 20% DD stop from peak.</p>
  </div>

  <div class="footer">Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}  ·  TL25 v3 production locked-in config</div>
</div>
</body>
</html>"""

    out_dir = ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"tl25_v3_production_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.html"
    out_path.write_text(html)

    artif = ROOT / "tasks/oos_retune_2026/winner_artifacts"
    artif.mkdir(parents=True, exist_ok=True)
    eq.to_csv(artif / "tl25_v3_production_equity.csv", index=False)
    trades.to_csv(artif / "tl25_v3_production_trades.csv", index=False)
    exits.to_csv(artif / "tl25_v3_production_exits.csv", index=False)
    holdings_df.to_csv(artif / "tl25_v3_production_current_holdings.csv", index=False)

    print(f"\n[done]  CAGR={stats_port['cagr']*100:.2f}%  "
          f"Sharpe={stats_port['sharpe']:.2f}  "
          f"MaxDD={stats_port['max_dd']*100:.2f}%  "
          f"Holdings={n_holdings}  Cash={cash_pct:.2f}%")
    print(f"[wrote] {out_path}")


if __name__ == "__main__":
    main()
