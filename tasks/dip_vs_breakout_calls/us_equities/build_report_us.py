"""Build the investor PDF report for the US dip25_trend simulation.

Reads investor_us_curve.csv / investor_us_ledger.csv /
investor_us_holdings.csv / investor_us_summary.json (from
investor_sim_us.py) and writes investor_report_us.pdf.

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/us_equities/build_report_us.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[2]
TAG = os.environ.get("OUT_TAG", "")

INK = "#0b0b0b"
INK2 = "#52514e"
SURFACE = "#fcfcfb"
GRID = "#e7e6e2"
S1 = "#2a78d6"          # strategy
S2 = "#eb6834"          # benchmark
GOOD = "#008300"
BAD = "#e34948"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "font.size": 8.5,
    "text.parse_math": False,   # keep literal $ signs out of mathtext
})
A4 = (8.27, 11.69)


def dollars(x, dec=1):
    if abs(x) >= 1e6:
        return f"${x/1e6:.{dec}f}M"
    if abs(x) >= 1e3:
        return f"${x/1e3:.{dec}f}k"
    return f"${x:,.0f}"


def usd(x):
    s = f"{abs(x):,.0f}"
    return ("-" if x < 0 else "") + s


def style_table(tbl, header_cells=1, fontsize=7.2):
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(fontsize)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(GRID)
        cell.set_linewidth(0.5)
        if r < header_cells:
            cell.set_facecolor("#f1f0ec")
            cell.set_text_props(color=INK, weight="bold")
        else:
            cell.set_facecolor(SURFACE)


def new_page(pdf, title, subtitle=None):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.965, title, fontsize=13, weight="bold", color=INK)
    if subtitle:
        fig.text(0.06, 0.945, subtitle, fontsize=8.5, color=INK2)
    fig.text(0.94, 0.965, "Marketworks Research", fontsize=8, color=INK2,
             ha="right")
    fig.text(0.94, 0.948, "Backtest simulation — not live results",
             fontsize=7, color=BAD, ha="right")
    return fig


def year_ends(eq):
    return [pd.Timestamp(f"{y}-12-31")
            for y in range(eq.index[0].year, eq.index[-1].year)]


INTERPRETATIONS = {
    "": "The 2025-26 semiconductor/memory rally dominates the result: the top 5 open positions\n"
        "({top5_syms}) are {top5_share} of final equity, and 2026 YTD accounts for much of the\n"
        "total return.",
    "_2017": "This pre-AI-boom window spans four stress episodes — the Feb 2018 vol shock, the Q4 2018\n"
             "selloff, the Mar 2020 COVID crash (the -37% max drawdown), and the 2022 bear (the one losing year,\n"
             "-12.7%, with losses carried forward). The edge is concentrated in 2017/2019/2020; 2021 was nearly flat as\n"
             "mega-cap leadership churned the momentum ranks. A single call — TSLA, entered Nov 2019 — returned +770%\n"
             "and drives a large share of the window's profit; the top 5 open positions ({top5_syms}) are\n"
             "{top5_share} of final equity.",
}


def math_ceil(x):
    return int(np.ceil(x))


def main():
    curve = pd.read_csv(DIR / f"investor_us{TAG}_curve.csv", parse_dates=["date"]).set_index("date")
    ledger = pd.read_csv(DIR / f"investor_us{TAG}_ledger.csv", parse_dates=["entry_date", "exit_date"])
    holdings = pd.read_csv(DIR / f"investor_us{TAG}_holdings.csv")
    summary = json.loads((DIR / f"investor_us{TAG}_summary.json").read_text())

    bench_raw = pd.read_csv(ROOT / "data/benchmarks/spy.csv",
                            parse_dates=["date"]).set_index("date")["close"]
    bench = bench_raw[bench_raw.index >= curve.index[0]]
    bench = bench / bench.iloc[0] * 100_000
    bench = bench.reindex(curve.index)          # NaN after SPY data end -> line stops

    eq = curve.equity
    ret_d = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    b_last = bench.dropna()
    b_years = (b_last.index[-1] - b_last.index[0]).days / 365.25
    b_cagr = (b_last.iloc[-1] / b_last.iloc[0]) ** (1 / b_years) - 1
    spy_note = (f" (to {b_last.index[-1]:%b %y})"
                if b_last.index[-1] < eq.index[-1] - pd.Timedelta(days=7) else "")
    dd = eq / eq.cummax() - 1
    sharpe = (cagr - 0.05) / (ret_d.std() * np.sqrt(252))
    wins = ledger[ledger.pnl_pct > 0]
    losses = ledger[ledger.pnl_pct <= 0]
    pf = wins.pnl_usd.sum() / abs(losses.pnl_usd.sum())

    pdf_path = DIR / f"investor_report_us{TAG}.pdf"
    with PdfPages(pdf_path) as pdf:

        # ---------- page 1: overview ----------
        fig = new_page(pdf, "Dip-Timed Momentum Feed (US) — Investor Simulation",
                       f"$100,000 deployed {eq.index[0]:%d %b %Y} → {eq.index[-1]:%d %b %Y}"
                       " · S&P 500 ∪ Nasdaq 100 · max 25 positions")
        stats = [
            ("Final value (net of tax)", dollars(eq.iloc[-1], 0)),
            ("Total return", f"+{eq.iloc[-1]/eq.iloc[0]-1:.0%}"),
            ("CAGR (net of tax)", f"{cagr:.1%}"),
            (f"SPY CAGR{spy_note}", f"{b_cagr:.1%}"),
            ("Max drawdown", f"{dd.min():.1%}"),
            ("Tax paid", dollars(summary["total_tax"], 1)),
            ("Calls closed / open", f"{len(ledger)} / {len(holdings)}"),
            ("Win rate", f"{(ledger.pnl_pct > 0).mean():.0%}"),
        ]
        for k, (label, val) in enumerate(stats):
            x = 0.06 + (k % 4) * 0.235
            y = 0.895 - (k // 4) * 0.052
            fig.text(x, y, val, fontsize=13, weight="bold", color=INK)
            fig.text(x, y - 0.020, label, fontsize=7, color=INK2)

        ax = fig.add_axes([0.08, 0.42, 0.86, 0.33])
        ax.plot(eq.index, eq / 1e3, color=S1, lw=1.8, label="Strategy (net of tax)")
        ax.plot(bench.index, bench / 1e3, color=S2, lw=1.8,
                label="SPY ($100k, untaxed" +
                      (f", data to {b_last.index[-1]:%d %b %y})" if spy_note else ")"))
        ax.text(eq.index[-1], eq.iloc[-1] / 1e3, f"  {dollars(eq.iloc[-1],0)}",
                color=S1, fontsize=8.5, weight="bold", va="center")
        ax.text(b_last.index[-1], b_last.iloc[-1] / 1e3, f"  {dollars(b_last.iloc[-1],0)}",
                color=S2, fontsize=8.5, weight="bold", va="center")
        for t in year_ends(eq):
            if eq.index[0] < t < eq.index[-1]:
                ax.axvline(t, color=GRID, lw=0.8, ls="--")
        ax.set_ylabel("Portfolio value ($ thousand)")
        ax.set_xlim(eq.index[0], eq.index[-1] + pd.Timedelta(days=170))
        ax.legend(frameon=False, loc="upper left", fontsize=8)
        ax.set_title("Growth of $100,000 (dashed lines: calendar-year ends / tax dates)",
                     fontsize=9, color=INK2, loc="left")

        axd = fig.add_axes([0.08, 0.245, 0.86, 0.12])
        axd.fill_between(dd.index, dd * 100, 0, color=S1, alpha=0.25, lw=0)
        axd.plot(dd.index, dd * 100, color=S1, lw=1.2)
        axd.set_ylabel("Drawdown %")
        axd.set_xlim(ax.get_xlim())

        fig.text(0.06, 0.175, "Strategy rules", fontsize=9, weight="bold", color=INK)
        fig.text(0.06, 0.155,
                 "Entry: a stock in the top quartile of the S&P 500 ∪ Nasdaq 100 universe by 126-day risk-adjusted momentum,\n"
                 "trading above its 200-day average, falls more than 5% over 5 sessions. Slots (max 25) are filled by momentum\n"
                 "rank; each position is 4% of portfolio equity at entry, whole shares. Fills at next-day average price (OHLC/4)\n"
                 "with 0.2% slippage each way. Exit: momentum rank decays below the 35th percentile — no trailing stop (a 20%\n"
                 "trail subtracts ~4pp CAGR on US data; see RESULTS_US.md). Tax: 25% flat on net realized gains each Dec 31,\n"
                 "losses carried forward. No leverage; idle cash earns nothing. Config selected on Indian data, tested here\n"
                 "out-of-sample with no parameter retuning.",
                 fontsize=7.5, color=INK2, va="top")
        pdf.savefig(fig); plt.close(fig)

        # ---------- page 2: monthly & yearly ----------
        fig = new_page(pdf, "Returns Detail", "Monthly portfolio returns and calendar-year summary")
        me = eq.resample("ME").last()
        mret = me.pct_change()
        mret.iloc[0] = me.iloc[0] / eq.iloc[0] - 1
        col_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                      "Sep", "Oct", "Nov", "Dec", "Year"]
        rows, cell_txt, cell_col = [], [], []
        for y, g in mret.groupby(mret.index.year):
            row = [""] * 13
            for d, v in g.items():
                row[d.month - 1] = f"{v*100:+.1f}"
            ye = eq[eq.index.year == y]
            prior = eq[eq.index.year < y]
            yr = ye.iloc[-1] / (prior.iloc[-1] if len(prior) else eq.iloc[0]) - 1
            row[12] = f"{yr*100:+.1f}"
            rows.append(str(y))
            cell_txt.append(row)
            cell_col.append([GOOD if c.startswith("+") else BAD if c.startswith("-")
                             else INK2 for c in row])
        ax = fig.add_axes([0.06, 0.68, 0.88, 0.2])
        ax.axis("off")
        tbl = ax.table(cellText=cell_txt, rowLabels=rows, colLabels=col_labels,
                       cellLoc="center", loc="upper center")
        style_table(tbl)
        for (r, c), cell in tbl.get_celld().items():
            if r > 0 and c >= 0:
                cell.set_text_props(color=cell_col[r - 1][c])
                if c == 12:
                    cell.set_text_props(weight="bold", color=cell_col[r - 1][c])
        ax.set_title("Monthly returns (%) — net equity, after tax outflows", fontsize=9,
                     color=INK2, loc="left")

        yr_rows = [[t["year_end"], usd(t["realized"]), usd(t["tax"]),
                    usd(t["loss_cf_after"]), usd(t["equity_after"])]
                   for t in summary["tax_events"]]
        if abs(summary["pending_yr_realized"]) > 0.5:
            yr_rows.append([f"Jan–{eq.index[-1]:%b} {eq.index[-1].year} (accrued)",
                            usd(summary["pending_yr_realized"]), "—", "—",
                            usd(eq.iloc[-1])])
        ax2 = fig.add_axes([0.06, 0.42, 0.88, 0.17])
        ax2.axis("off")
        tbl2 = ax2.table(cellText=yr_rows,
                         colLabels=["Year end", "Realized P&L ($)", "Tax paid ($)",
                                    "Loss carried fwd ($)", "Equity after ($)"],
                         cellLoc="center", loc="upper center")
        style_table(tbl2, fontsize=8)
        ax2.set_title("Calendar-year summary — 25% flat on net realized gains, losses carried forward",
                      fontsize=9, color=INK2, loc="left")

        ax3 = fig.add_axes([0.08, 0.09, 0.55, 0.24])
        bins = np.arange(-30, 121, 5)
        ax3.hist(np.clip(ledger.pnl_pct * 100, -29.9, 119.9), bins=bins,
                 color=S1, edgecolor=SURFACE, linewidth=1.5)
        ax3.axvline(0, color=INK2, lw=0.8)
        ax3.set_xlabel("Closed-call P&L (%, clipped at −30/+120)")
        ax3.set_ylabel("Calls")
        ax3.set_title(f"Distribution of the {len(ledger)} closed calls", fontsize=9,
                      color=INK2, loc="left")
        stats2 = [
            ("Avg win", f"+{wins.pnl_pct.mean():.1%}"),
            ("Avg loss", f"{losses.pnl_pct.mean():.1%}"),
            ("Profit factor", f"{pf:.2f}"),
            ("Median hold", f"{int(ledger.hold_td.median())} sessions"),
            ("Best call", f"{ledger.pnl_pct.max():+.0%} ({ledger.loc[ledger.pnl_pct.idxmax(), 'symbol']})"),
            ("Worst call", f"{ledger.pnl_pct.min():+.0%} ({ledger.loc[ledger.pnl_pct.idxmin(), 'symbol']})"),
            ("Exit rule", "momentum decay (100%)"),
            ("Sharpe (house conv.)", f"{sharpe:.2f}"),
        ]
        for k, (label, val) in enumerate(stats2):
            y = 0.30 - k * 0.028
            fig.text(0.68, y, label, fontsize=8, color=INK2)
            fig.text(0.94, y, val, fontsize=8, weight="bold", color=INK, ha="right")
        pdf.savefig(fig); plt.close(fig)

        # ---------- page 3: holdings ----------
        fig = new_page(pdf, f"Current Holdings — {eq.index[-1]:%d %b %Y}",
                       f"{len(holdings)} open positions · market value "
                       f"{dollars(holdings.value_usd.sum(),1)} · cash {dollars(summary['cash'],2)}")
        h = holdings.copy()
        cells = [[r.symbol, r.entry_date, f"{r.shares:,}",
                  f"{r.entry_px:,.2f}", f"{r.last_close:,.2f}",
                  usd(r.value_usd), usd(r.pnl_usd), f"{r.pnl_pct*100:+.1f}%",
                  f"{r.hold_td}", f"{r.mom_rank:.2f}", f"{r.peak_dist*100:+.1f}%"]
                 for r in h.itertuples()]
        ax = fig.add_axes([0.05, 0.16, 0.9, 0.74])
        ax.axis("off")
        tbl = ax.table(cellText=cells,
                       colLabels=["Symbol", "Entry", "Shares", "Entry $",
                                  "Last $", "Value $", "P&L $", "P&L %",
                                  "Hold (td)", "Mom rank", "vs peak"],
                       cellLoc="center", loc="upper center")
        style_table(tbl, fontsize=7)
        tbl.scale(1, 1.6)
        for (r, c), cell in tbl.get_celld().items():
            if r > 0 and c in (6, 7):
                v = h.iloc[r - 1].pnl_usd
                cell.set_text_props(color=GOOD if v > 0 else BAD)
        fig.text(0.06, 0.10,
                 "Mom rank = current cross-sectional momentum percentile (exit below 0.35).\n"
                 "vs peak = distance from peak close since entry (informational — no trailing stop in this configuration).",
                 fontsize=7.5, color=INK2, va="top")
        pdf.savefig(fig); plt.close(fig)

        # ---------- pages 4+: ledger ----------
        led = ledger.sort_values("entry_date", ascending=False).reset_index(drop=True)
        per_page = 47
        npages = math_ceil(len(led) / per_page)
        for pg in range(npages):
            chunk = led.iloc[pg * per_page:(pg + 1) * per_page]
            fig = new_page(pdf, f"Closed-Call Ledger ({pg + 1}/{npages})",
                           f"All {len(led)} closed calls, most recent first · prices are effective (slippage included)")
            cells = [[r.symbol, str(r.entry_date.date()), str(r.exit_date.date()),
                      f"{r.shares:,}", f"{r.entry_px:,.2f}", f"{r.exit_px:,.2f}",
                      usd(r.pnl_usd), f"{r.pnl_pct*100:+.1f}%", f"{r.hold_td}",
                      "decay"]
                     for r in chunk.itertuples()]
            ax = fig.add_axes([0.05, 0.03, 0.9, 0.89])
            ax.axis("off")
            tbl = ax.table(cellText=cells,
                           colLabels=["Symbol", "Entry", "Exit", "Shares",
                                      "Entry $", "Exit $", "P&L $",
                                      "P&L %", "Hold", "Exit type"],
                           cellLoc="center", loc="upper center")
            style_table(tbl, fontsize=6.6)
            tbl.scale(1, 1.06)
            for (r, c), cell in tbl.get_celld().items():
                if r > 0 and c in (6, 7):
                    v = chunk.iloc[r - 1].pnl_usd
                    cell.set_text_props(color=GOOD if v > 0 else BAD)
            pdf.savefig(fig); plt.close(fig)

        # ---------- final page: notes ----------
        top5 = holdings.nlargest(5, "value_usd")
        top5_share = top5.value_usd.sum() / eq.iloc[-1]
        top5_syms = ", ".join(top5.symbol)
        pending = summary["pending_yr_realized"]
        if abs(pending) > 0.5:
            tax_note = (f"{dollars(pending,1)} of gains realized in {eq.index[-1].year} "
                        "remain untaxed in the final figure.")
        else:
            tax_note = ("All realized gains in the window are taxed; "
                        f"{dollars(summary['loss_cf'],1)} of losses remain as carry-forward "
                        "at the window end.") if summary["loss_cf"] > 0.5 else \
                       "All realized gains in the window are taxed at the final year-end."
        interp = INTERPRETATIONS.get(TAG, INTERPRETATIONS[""]).format(
            top5_share=f"{top5_share:.0%}", top5_syms=top5_syms)
        fig = new_page(pdf, "Methodology & Disclosures", None)
        fig.text(0.06, 0.90,
                 "This is a research backtest, not a live track record.\n\n"
                 "Data. Daily OHLCV for the current S&P 500 and Nasdaq 100 constituents (514 symbols), split/dividend\n"
                 "adjusted (EODHD). Because the universe is today's membership, results carry survivorship bias — and it is\n"
                 "stronger here than in the India study: constituents of major US indices are by construction the era's\n"
                 "winners. Stocks delisted or dropped during the window are absent. A production engine would use\n"
                 "effective-dated membership.\n\n"
                 "Execution. Signals are computed at each close; fills occur the next session at the OHLC/4 average price with\n"
                 "0.2% slippage each way. Position size is 4% of portfolio equity at entry, whole shares only, max 25 positions,\n"
                 "no leverage. Idle cash earns nothing. Commissions are not modeled (near zero at US retail brokers); SEC/TAF\n"
                 "fees and borrow costs are immaterial for a long-only book at this turnover.\n\n"
                 "Taxes. 25% flat on net realized gains each December 31 with loss carry-forward — a deliberate simplification\n"
                 "mirroring the India report, not US tax advice. Actual short/long-term capital-gains treatment depends on\n"
                 f"holding period and bracket. {tax_note}\n\n"
                 "Validity. The dip-entry cohort passed the house 6-check validity protocol on Indian data (NSE 500,\n"
                 "2012-2026). The protocol has NOT been run on the US panel; what is shown here is an out-of-sample\n"
                 "portfolio-level test of the India-selected rules with one deviation — the trailing stop is dropped, per the\n"
                 "US grid in RESULTS_US.md, which is itself a selection made on this same data (treat with corresponding\n"
                 "caution).\n\n"
                 f"Interpretation. {interp}\n"
                 "The strategy's concentration in whatever leads the tape is by design — momentum-rank slot\n"
                 "priority — but a different regime would produce materially different results. Past performance, simulated or\n"
                 "otherwise, does not guarantee future results.",
                 fontsize=8.5, color=INK2, va="top", linespacing=1.5)
        pdf.savefig(fig); plt.close(fig)

    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
