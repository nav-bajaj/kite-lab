"""Build the investor PDF report for the dip25_ts20 simulation.

Reads investor_curve.csv / investor_ledger.csv / investor_holdings.csv /
investor_summary.json (from investor_sim.py) and writes
investor_report.pdf.

Run:  .venv/bin/python tasks/dip_vs_breakout_calls/build_report.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[1]

# dataviz reference palette (light mode)
INK = "#0b0b0b"
INK2 = "#52514e"
SURFACE = "#fcfcfb"
GRID = "#e7e6e2"
S1 = "#2a78d6"          # strategy (blue, slot 1)
S2 = "#eb6834"          # benchmark (orange, slot 2)
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
})
A4 = (8.27, 11.69)


def rupees(x, dec=1):
    if abs(x) >= 1e7:
        return f"₹{x/1e7:.{dec}f}Cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:.{dec}f}L"
    return f"₹{x:,.0f}"


def indian(x):
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


def main():
    curve = pd.read_csv(DIR / "investor_curve.csv", parse_dates=["date"]).set_index("date")
    ledger = pd.read_csv(DIR / "investor_ledger.csv", parse_dates=["entry_date", "exit_date"])
    holdings = pd.read_csv(DIR / "investor_holdings.csv")
    summary = json.loads((DIR / "investor_summary.json").read_text())

    bench_raw = pd.read_csv(ROOT / "indices_data/NIFTY_500.csv",
                            parse_dates=["date"]).set_index("date")["close"]
    bench = bench_raw.reindex(curve.index).ffill()
    bench = bench / bench.iloc[0] * 2_000_000

    eq = curve.equity
    ret_d = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    b_cagr = (bench.iloc[-1] / bench.iloc[0]) ** (1 / years) - 1
    dd = eq / eq.cummax() - 1
    b_dd = (bench / bench.cummax() - 1).min()
    sharpe = (cagr - 0.05) / (ret_d.std() * np.sqrt(252))
    wins = ledger[ledger.pnl_pct > 0]
    losses = ledger[ledger.pnl_pct <= 0]
    pf = wins.pnl_rs.sum() / abs(losses.pnl_rs.sum())

    pdf_path = DIR / "investor_report.pdf"
    with PdfPages(pdf_path) as pdf:

        # ---------- page 1: overview ----------
        fig = new_page(pdf, "Dip-Timed Momentum Feed — Investor Simulation",
                       "₹20,00,000 deployed 01 Jan 2023 → 19 Aug 2026 · NSE 500 · max 25 positions")
        stats = [
            ("Final value (net of tax)", rupees(eq.iloc[-1], 2)),
            ("Total return", f"+{eq.iloc[-1]/eq.iloc[0]-1:.0%}"),
            ("CAGR (net of tax)", f"{cagr:.1%}"),
            ("Nifty 500 CAGR", f"{b_cagr:.1%}"),
            ("Max drawdown", f"{dd.min():.1%}"),
            ("Tax paid", rupees(summary["total_tax"], 2)),
            ("Calls closed / open", f"{len(ledger)} / {len(holdings)}"),
            ("Win rate", f"{(ledger.pnl_pct > 0).mean():.0%}"),
        ]
        for k, (label, val) in enumerate(stats):
            x = 0.06 + (k % 4) * 0.235
            y = 0.895 - (k // 4) * 0.052
            fig.text(x, y, val, fontsize=13, weight="bold", color=INK)
            fig.text(x, y - 0.020, label, fontsize=7, color=INK2)

        ax = fig.add_axes([0.08, 0.42, 0.86, 0.33])
        ax.plot(eq.index, eq / 1e5, color=S1, lw=1.8, label="Strategy (net of tax)")
        ax.plot(bench.index, bench / 1e5, color=S2, lw=1.8, label="Nifty 500 (₹20L, untaxed)")
        ax.text(eq.index[-1], eq.iloc[-1] / 1e5, f"  {rupees(eq.iloc[-1],1)}",
                color=S1, fontsize=8.5, weight="bold", va="center")
        ax.text(bench.index[-1], bench.iloc[-1] / 1e5, f"  {rupees(bench.iloc[-1],1)}",
                color=S2, fontsize=8.5, weight="bold", va="center")
        for t in FYT():
            if eq.index[0] < t < eq.index[-1]:
                ax.axvline(t, color=GRID, lw=0.8, ls="--")
        ax.set_ylabel("Portfolio value (₹ lakh)")
        ax.set_xlim(eq.index[0], eq.index[-1] + pd.Timedelta(days=170))
        ax.legend(frameon=False, loc="upper left", fontsize=8)
        ax.set_title("Growth of ₹20,00,000 (dashed lines: FY ends / tax dates)",
                     fontsize=9, color=INK2, loc="left")

        axd = fig.add_axes([0.08, 0.245, 0.86, 0.12])
        axd.fill_between(dd.index, dd * 100, 0, color=S1, alpha=0.25, lw=0)
        axd.plot(dd.index, dd * 100, color=S1, lw=1.2)
        axd.set_ylabel("Drawdown %")
        axd.set_xlim(ax.get_xlim())

        fig.text(0.06, 0.175, "Strategy rules", fontsize=9, weight="bold", color=INK)
        fig.text(0.06, 0.155,
                 "Entry: a stock in the top quartile of the NSE 500 by 126-day risk-adjusted momentum falls more than 5% over 5\n"
                 "sessions. Slots (max 25) are filled by momentum rank; each position is 4% of portfolio equity at entry, integer shares.\n"
                 "Fills at next-day average price (OHLC/4) with 0.2% slippage each way. Exit: momentum rank decays below the 35th\n"
                 "percentile, or a 20% trailing stop from the peak close. No leverage; idle cash earns nothing. Tax: 25% flat on net\n"
                 "realized gains at each March 31, losses carried forward. Validity: entry cohort passed the house 6-check protocol\n"
                 "(+1.0pp excess at 20d, +3.5pp at 60d vs same-date universe baseline). See tasks/dip_vs_breakout_calls/.",
                 fontsize=7.5, color=INK2, va="top")
        pdf.savefig(fig); plt.close(fig)

        # ---------- page 2: monthly & FY ----------
        fig = new_page(pdf, "Returns Detail", "Monthly portfolio returns and financial-year summary")
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

        fy_rows = [[t["fy_end"], indian(t["realized"]), indian(t["tax"]),
                    indian(t["loss_cf_after"]), indian(t["equity_after"])]
                   for t in summary["tax_events"]]
        fy_rows.append(["Apr–Aug 2026 (accrued)",
                        indian(summary["pending_fy_realized"]), "—", "—",
                        indian(eq.iloc[-1])])
        ax2 = fig.add_axes([0.06, 0.42, 0.88, 0.17])
        ax2.axis("off")
        tbl2 = ax2.table(cellText=fy_rows,
                         colLabels=["FY end", "Realized P&L (₹)", "Tax paid (₹)",
                                    "Loss carried fwd (₹)", "Equity after (₹)"],
                         cellLoc="center", loc="upper center")
        style_table(tbl2, fontsize=8)
        ax2.set_title("Financial-year summary — 25% flat on net realized gains, losses carried forward",
                      fontsize=9, color=INK2, loc="left")

        # call P&L histogram
        ax3 = fig.add_axes([0.08, 0.09, 0.55, 0.24])
        bins = np.arange(-30, 121, 5)
        ax3.hist(np.clip(ledger.pnl_pct * 100, -29.9, 119.9), bins=bins,
                 color=S1, edgecolor=SURFACE, linewidth=1.5)
        ax3.axvline(0, color=INK2, lw=0.8)
        ax3.set_xlabel("Closed-call P&L (%, clipped at −30/+120)")
        ax3.set_ylabel("Calls")
        ax3.set_title("Distribution of the 227 closed calls", fontsize=9,
                      color=INK2, loc="left")
        stats2 = [
            ("Avg win", f"+{wins.pnl_pct.mean():.1%}"),
            ("Avg loss", f"{losses.pnl_pct.mean():.1%}"),
            ("Profit factor", f"{pf:.2f}"),
            ("Median hold", f"{int(ledger.hold_td.median())} sessions"),
            ("Best call", f"{ledger.pnl_pct.max():+.0%} ({ledger.loc[ledger.pnl_pct.idxmax(), 'symbol']})"),
            ("Worst call", f"{ledger.pnl_pct.min():+.0%} ({ledger.loc[ledger.pnl_pct.idxmin(), 'symbol']})"),
            ("Exit: momentum decay", f"{(ledger.reason=='momentum_decay').mean():.0%}"),
            ("Exit: trailing stop", f"{(ledger.reason=='trailing_stop').mean():.0%}"),
        ]
        for k, (label, val) in enumerate(stats2):
            y = 0.30 - k * 0.028
            fig.text(0.68, y, label, fontsize=8, color=INK2)
            fig.text(0.94, y, val, fontsize=8, weight="bold", color=INK, ha="right")
        pdf.savefig(fig); plt.close(fig)

        # ---------- page 3: holdings ----------
        fig = new_page(pdf, "Current Holdings — 19 Aug 2026",
                       f"{len(holdings)} open positions · market value "
                       f"{rupees(holdings.value_rs.sum(),2)} · cash {rupees(summary['cash'])}")
        h = holdings.copy()
        cells = [[r.symbol, r.entry_date, f"{r.shares:,}",
                  f"{r.entry_px:,.1f}", f"{r.last_close:,.1f}",
                  indian(r.value_rs), indian(r.pnl_rs), f"{r.pnl_pct*100:+.1f}%",
                  f"{r.hold_td}", f"{r.mom_rank:.2f}", f"{r.peak_dist*100:+.1f}%"]
                 for r in h.itertuples()]
        ax = fig.add_axes([0.05, 0.16, 0.9, 0.74])
        ax.axis("off")
        tbl = ax.table(cellText=cells,
                       colLabels=["Symbol", "Entry", "Shares", "Entry ₹",
                                  "Last ₹", "Value ₹", "P&L ₹", "P&L %",
                                  "Hold (td)", "Mom rank", "vs peak"],
                       cellLoc="center", loc="upper center")
        style_table(tbl, fontsize=7)
        tbl.scale(1, 1.6)
        for (r, c), cell in tbl.get_celld().items():
            if r > 0 and c in (6, 7):
                v = h.iloc[r - 1].pnl_rs
                cell.set_text_props(color=GOOD if v > 0 else BAD)
        fig.text(0.06, 0.10,
                 "Mom rank = current cross-sectional momentum percentile (exit below 0.35). "
                 "vs peak = distance from peak close since entry (trailing stop at −20%).",
                 fontsize=7.5, color=INK2)
        pdf.savefig(fig); plt.close(fig)

        # ---------- pages 4+: ledger ----------
        led = ledger.sort_values("entry_date", ascending=False).reset_index(drop=True)
        per_page = 47
        npages = math_ceil(len(led) / per_page)
        for pg in range(npages):
            chunk = led.iloc[pg * per_page:(pg + 1) * per_page]
            fig = new_page(pdf, f"Closed-Call Ledger ({pg + 1}/{npages})",
                           "All 227 closed calls, most recent first · prices are effective (slippage included)")
            cells = [[r.symbol, str(r.entry_date.date()), str(r.exit_date.date()),
                      f"{r.shares:,}", f"{r.entry_px:,.1f}", f"{r.exit_px:,.1f}",
                      indian(r.pnl_rs), f"{r.pnl_pct*100:+.1f}%", f"{r.hold_td}",
                      "decay" if r.reason == "momentum_decay" else "trail"]
                     for r in chunk.itertuples()]
            ax = fig.add_axes([0.05, 0.03, 0.9, 0.89])
            ax.axis("off")
            tbl = ax.table(cellText=cells,
                           colLabels=["Symbol", "Entry", "Exit", "Shares",
                                      "Entry ₹", "Exit ₹", "P&L ₹",
                                      "P&L %", "Hold", "Exit type"],
                           cellLoc="center", loc="upper center")
            style_table(tbl, fontsize=6.6)
            tbl.scale(1, 1.06)
            for (r, c), cell in tbl.get_celld().items():
                if r > 0 and c in (6, 7):
                    v = chunk.iloc[r - 1].pnl_rs
                    cell.set_text_props(color=GOOD if v > 0 else BAD)
            pdf.savefig(fig); plt.close(fig)

        # ---------- final page: notes ----------
        fig = new_page(pdf, "Methodology & Disclosures", None)
        fig.text(0.06, 0.90,
                 "This is a research backtest, not a live track record.\n\n"
                 "Data. Daily OHLCV for the current NSE 500 constituents, corporate-action adjusted; 33 symbols with\n"
                 "unadjusted corporate-action gaps were excluded (list in tasks/dip_vs_breakout_calls/PLAN.md). Because the\n"
                 "universe is today's membership, results carry survivorship bias — stocks delisted or relegated during the\n"
                 "window are absent. A production engine would use effective-dated membership.\n\n"
                 "Execution. Signals are computed at each close; fills occur the next session at the OHLC/4 average price with\n"
                 "0.2% slippage each way. Position size is 4% of portfolio equity at entry, whole shares only, max 25 positions,\n"
                 "no leverage. Idle cash earns nothing (a liquid fund would add ≈"
                 "0.3-0.6pp/yr on observed cash balances).\n\n"
                 "Costs & taxes. Slippage only; brokerage, STT, stamp duty and other charges are not modeled and would\n"
                 "reduce returns by roughly 0.3-0.5pp per round trip at discount-broker rates. Tax is applied as specified:\n"
                 "25% flat on net realized gains at each March 31 with loss carry-forward; ₹"
                 "1,54,096 of gains realized after\n"
                 "March 2026 remain untaxed in the final figure. Actual STCG/LTCG treatment differs from this flat assumption.\n\n"
                 "Validity. The entry cohort passed the house validity protocol (all six checks): +1.02pp excess vs the same-date\n"
                 "universe baseline at 20 days, +3.45pp at 60 days, direction lift positive at every horizon, persistent across\n"
                 "sample halves (2012-2026, n=978). The exit rules shape realized P&L on top of that entry edge.\n\n"
                 "Interpretation. 2023's H2 rally and 2024's dip-rich tape were favourable regimes for this strategy; the flat\n"
                 "stretch in FY2026 (realized +₹2.2L on a ₹40L book) is representative of quieter tapes. Past performance,\n"
                 "simulated or otherwise, does not guarantee future results.",
                 fontsize=8.5, color=INK2, va="top", linespacing=1.5)
        pdf.savefig(fig); plt.close(fig)

    print(f"wrote {pdf_path}")


def FYT():
    return [pd.Timestamp(f"{y}-03-31") for y in (2023, 2024, 2025, 2026)]


def math_ceil(x):
    return int(np.ceil(x))


if __name__ == "__main__":
    main()
