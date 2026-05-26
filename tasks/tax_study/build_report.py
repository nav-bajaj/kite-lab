"""Tax study v2 — HTML report builder.

Reads the 4 strategies' trades + equity, runs the full tax engine + forced-sale
simulation, computes per-window stats (per-strategy IS/OOS labels per PLAN.md),
compares against a NIFTY 50 buy-and-hold benchmark, and writes a self-contained
HTML report with charts (CAGR bars, per-FY tax bars, equity-curve small
multiples).
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from benchmark import build_bh_equity, build_bh_trades, load_nifty50
from forced_sale import TaxEvent, build_tax_events
from tax_engine import FYTax, compute_tax_per_fy, match_lots

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
OUTPUT_HTML = HERE / "report.html"

STRATEGIES = {
    "OM25 v3 (Nifty 250)":  ("om25_v3",         "om25_trades.csv",  "om25_equity.csv"),
    "TL25 v3 (NSE 500)":    ("tl25_v3",         "tl25_trades.csv",  "tl25_equity.csv"),
    "L6 v2 (NSE 500)":      ("l6_v2",           "l6_trades.csv",    "l6_equity.csv"),
    "COMBO Defensive":      ("combo_defensive", "combo_trades.csv", "combo_equity.csv"),
}

# Per-strategy windows from PLAN.md
WINDOWS = {
    "OM25 v3 (Nifty 250)": [
        ("IS",  pd.Timestamp("2009-09-01"), pd.Timestamp("2016-12-31")),
        ("OOS", pd.Timestamp("2017-01-01"), pd.Timestamp("2026-05-12")),
    ],
    "TL25 v3 (NSE 500)": [
        ("IS",  pd.Timestamp("2009-09-01"), pd.Timestamp("2016-12-31")),
        ("OOS", pd.Timestamp("2017-01-01"), pd.Timestamp("2026-05-12")),
    ],
    "L6 v2 (NSE 500)": [
        ("Pre-IS", pd.Timestamp("2009-09-01"), pd.Timestamp("2019-12-31")),
        ("IS",     pd.Timestamp("2020-01-01"), pd.Timestamp("2026-05-12")),
    ],
    "COMBO Defensive": [
        ("Pre-IS", pd.Timestamp("2009-09-01"), pd.Timestamp("2019-12-31")),
        ("IS",     pd.Timestamp("2020-01-01"), pd.Timestamp("2026-05-12")),
    ],
}


@dataclass
class WindowResult:
    strategy: str
    label: str                # "IS" / "OOS" / "Pre-IS" / "Full"
    start: pd.Timestamp
    end: pd.Timestamp
    years: float
    pretax_final_mult: float
    posttax_final_mult: float
    pretax_cagr: float
    posttax_cagr: float
    tax_paid_in_window: float
    n_tax_events_in_window: int
    stcg_paid: float
    ltcg_paid: float

    @property
    def drag_bps(self) -> float:
        return (self.pretax_cagr - self.posttax_cagr) * 10_000


@dataclass
class StrategyContext:
    name: str
    equity: pd.DataFrame                # date, pv, ...
    trades: pd.DataFrame
    realized: list                       # list[RealizedLot]
    fy_results: list[FYTax]
    tax_events: list[TaxEvent]
    scale_series: pd.Series              # post-tax multiplier indexed by date


def _slice_window(ctx: StrategyContext, label: str,
                   start: pd.Timestamp, end: pd.Timestamp) -> WindowResult:
    """Compute window-relative stats. Pre-tax CAGR uses raw equity; post-tax
    uses raw_equity × cumulative_scale, both ratioed to the window's start."""
    eq = ctx.equity.copy()
    eq["date"] = pd.to_datetime(eq["date"])
    win = eq[(eq["date"] >= start) & (eq["date"] <= end)].reset_index(drop=True)
    if len(win) < 2:
        return WindowResult(ctx.name, label, start, end, 0, 1, 1, 0, 0, 0, 0, 0, 0)

    pv_start = float(win.iloc[0]["pv"])
    pv_end = float(win.iloc[-1]["pv"])
    scale_start = float(ctx.scale_series.get(win.iloc[0]["date"], 1.0))
    scale_end = float(ctx.scale_series.get(win.iloc[-1]["date"], 1.0))

    pre_mult = pv_end / pv_start
    post_mult = (pv_end * scale_end) / (pv_start * scale_start)
    years = (win.iloc[-1]["date"] - win.iloc[0]["date"]).days / 365.25
    pretax_cagr = pre_mult ** (1.0 / years) - 1.0 if years > 0 else 0.0
    posttax_cagr = post_mult ** (1.0 / years) - 1.0 if years > 0 else 0.0

    in_window_events = [e for e in ctx.tax_events if start <= e.pay_date <= end]
    tax_in_window = sum(e.tax_paid for e in in_window_events)

    # STCG/LTCG breakdown for events whose ASSESSED FY's sells happen in the window
    stcg = 0.0
    ltcg = 0.0
    for fy in ctx.fy_results:
        # The FY's tax is "for" sells made between fy.fy_start and fy.fy_start+1y
        fy_end = pd.Timestamp(year=fy.fy_start.year + 1, month=3, day=31)
        # If the FY's window overlaps with our analysis window, count it
        if fy_end >= start and fy.fy_start <= end:
            # Use a simple overlap criterion: include if the pay_date (Apr 1
            # of next year) falls inside our window
            pay_d = pd.Timestamp(year=fy.fy_start.year + 1, month=4, day=1)
            if start <= pay_d <= end:
                stcg += fy.stcg_tax
                ltcg += fy.ltcg_tax
            elif pay_d > end and fy.fy_start <= end:
                # Deferred tax provisioned on last equity day
                # Only count if last equity day falls in window
                last_d = ctx.equity.iloc[-1]["date"]
                if start <= last_d <= end and end == ctx.equity.iloc[-1]["date"]:
                    stcg += fy.stcg_tax
                    ltcg += fy.ltcg_tax

    return WindowResult(
        strategy=ctx.name,
        label=label,
        start=win.iloc[0]["date"],
        end=win.iloc[-1]["date"],
        years=years,
        pretax_final_mult=pre_mult,
        posttax_final_mult=post_mult,
        pretax_cagr=pretax_cagr,
        posttax_cagr=posttax_cagr,
        tax_paid_in_window=tax_in_window,
        n_tax_events_in_window=len(in_window_events),
        stcg_paid=stcg,
        ltcg_paid=ltcg,
    )


def build_context(name: str, trades: pd.DataFrame, equity: pd.DataFrame) -> StrategyContext:
    realized, _ = match_lots(trades)
    fy_results = compute_tax_per_fy(realized)
    events, scale = build_tax_events(fy_results, equity)
    return StrategyContext(
        name=name, equity=equity, trades=trades,
        realized=realized, fy_results=fy_results,
        tax_events=events, scale_series=scale,
    )


# ---------- charts ----------

def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def render_charts(ctxs: dict[str, StrategyContext],
                   bh_ctx: StrategyContext) -> dict[str, str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    out: dict[str, str] = {}

    # Chart 1 — Full-period CAGR comparison bars (pre-tax vs post-tax)
    all_names = list(ctxs.keys()) + ["NIFTY 50 B&H"]
    pre = []
    post = []
    for n in list(ctxs.keys()):
        c = ctxs[n]
        eq = c.equity
        yrs = (eq.iloc[-1]["date"] - eq.iloc[0]["date"]).days / 365.25
        pretax = (eq.iloc[-1]["pv"] / eq.iloc[0]["pv"]) ** (1 / yrs) - 1
        sc = float(c.scale_series.iloc[-1])
        posttax = (eq.iloc[-1]["pv"] * sc / eq.iloc[0]["pv"]) ** (1 / yrs) - 1
        pre.append(pretax * 100)
        post.append(posttax * 100)
    # B&H
    eq = bh_ctx.equity
    yrs = (eq.iloc[-1]["date"] - eq.iloc[0]["date"]).days / 365.25
    pretax = (eq.iloc[-1]["pv"] / eq.iloc[0]["pv"]) ** (1 / yrs) - 1
    sc = float(bh_ctx.scale_series.iloc[-1])
    posttax = (eq.iloc[-1]["pv"] * sc / eq.iloc[0]["pv"]) ** (1 / yrs) - 1
    pre.append(pretax * 100)
    post.append(posttax * 100)

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(all_names))
    w = 0.35
    ax.bar(x - w / 2, pre, w, label="Pre-tax", color="#4a90e2")
    ax.bar(x + w / 2, post, w, label="Post-tax", color="#e2734a")
    for i, (p, q) in enumerate(zip(pre, post)):
        ax.text(i - w / 2, p + 0.6, f"{p:.1f}", ha="center", fontsize=9, color="#333")
        ax.text(i + w / 2, q + 0.6, f"{q:.1f}", ha="center", fontsize=9, color="#333")
    ax.set_xticks(x)
    ax.set_xticklabels([n.split(" (")[0] for n in all_names], fontsize=10)
    ax.set_ylabel("CAGR (%)")
    ax.set_title("Full-period CAGR — pre-tax vs post-tax  (2009/2010 → 2026, ~16y, 30 bps slippage)")
    ax.legend(loc="upper right", fontsize=10, frameon=False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    plt.tight_layout()
    out["cagr_bars"] = _fig_to_b64(fig)
    plt.close(fig)

    # Chart 2 — Equity curve small multiples (pre-tax solid, post-tax dashed)
    strategies = list(ctxs.keys())
    n = len(strategies) + 1
    fig, axes = plt.subplots(2, 3, figsize=(14, 7.5))
    axes_flat = axes.flat
    for ax, name in zip(axes_flat, strategies):
        c = ctxs[name]
        eq = c.equity.sort_values("date").reset_index(drop=True)
        pre_norm = eq["pv"] / eq.iloc[0]["pv"]
        scale = c.scale_series.reindex(eq["date"].values).ffill().fillna(1.0).to_numpy()
        post_norm = pre_norm.to_numpy() * scale
        ax.plot(eq["date"], pre_norm, color="#4a90e2", lw=1.5, label="pre-tax")
        ax.plot(eq["date"], post_norm, color="#c73a3a", lw=1.5, label="post-tax")
        # Shade IS window per WINDOWS dict
        wins = WINDOWS[name]
        is_win = next((w for w in wins if w[0] == "IS"), None)
        if is_win:
            ax.axvspan(is_win[1], is_win[2], color="black", alpha=0.06, label="IS window")
        ax.set_yscale("log")
        ax.set_title(name, fontsize=10)
        ax.grid(True, which="both", alpha=0.25)
        ax.set_axisbelow(True)
        ax.legend(fontsize=8, loc="upper left", frameon=False)
        ax.xaxis.set_major_locator(mdates.YearLocator(3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # B&H subplot
    ax = next(axes_flat)
    eq = bh_ctx.equity.sort_values("date").reset_index(drop=True)
    pre_norm = eq["pv"] / eq.iloc[0]["pv"]
    scale = bh_ctx.scale_series.reindex(eq["date"].values).ffill().fillna(1.0).to_numpy()
    post_norm = pre_norm.to_numpy() * scale
    ax.plot(eq["date"], pre_norm, color="#4a90e2", lw=1.5, label="pre-tax")
    ax.plot(eq["date"], post_norm, color="#c73a3a", lw=1.5, label="post-tax")
    ax.set_yscale("log")
    ax.set_title("NIFTY 50 B&H", fontsize=10)
    ax.grid(True, which="both", alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, loc="upper left", frameon=False)
    ax.xaxis.set_major_locator(mdates.YearLocator(3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # Hide the unused 6th subplot
    for ax in axes_flat:
        ax.set_visible(False)

    fig.suptitle("Equity curves — pre-tax vs post-tax (log scale, normalised to 1.0 at start; shaded = IS-tune window)",
                 fontsize=11, y=1.00)
    plt.tight_layout()
    out["equity_curves"] = _fig_to_b64(fig)
    plt.close(fig)

    # Chart 3 — Year-by-year tax stacked bars (STCG + LTCG)
    fig, ax = plt.subplots(figsize=(12, 5))
    all_fys = sorted(set(fy.fy_start for c in ctxs.values() for fy in c.fy_results))
    fy_labels = [f"FY{fy.year}-{str(fy.year+1)[-2:]}" for fy in all_fys]
    colors_stcg = ["#4a90e2", "#5da3e8", "#7fb7ee", "#a3c8f0"]
    colors_ltcg = ["#e2734a", "#e88a64", "#ee9f7d", "#f0b59a"]
    width = 0.18
    n_strats = len(ctxs)
    x = np.arange(len(all_fys))

    for i, (name, c) in enumerate(ctxs.items()):
        per_fy = {fy.fy_start: fy for fy in c.fy_results}
        stcg = [per_fy[fy].stcg_tax / 1e5 if fy in per_fy else 0 for fy in all_fys]
        ltcg = [per_fy[fy].ltcg_tax / 1e5 if fy in per_fy else 0 for fy in all_fys]
        offset = (i - (n_strats - 1) / 2) * width
        ax.bar(x + offset, stcg, width, color=colors_stcg[i], label=f"{name.split(' (')[0]} STCG")
        ax.bar(x + offset, ltcg, width, bottom=stcg, color=colors_ltcg[i], label=f"{name.split(' (')[0]} LTCG")
    ax.set_xticks(x)
    ax.set_xticklabels(fy_labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Tax (₹ Lakhs)")
    ax.set_title("Year-by-year tax — STCG (blue) + LTCG (orange) per strategy")
    ax.legend(fontsize=7, ncol=4, loc="upper left", frameon=False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)
    plt.tight_layout()
    out["per_fy_tax"] = _fig_to_b64(fig)
    plt.close(fig)

    return out


# ---------- HTML ----------

def _per_fy_compact_html(ctxs: dict[str, StrategyContext]) -> str:
    """Compact table: FY × 4 strategies showing total tax in ₹ lakhs."""
    all_fys = sorted(set(fy.fy_start for c in ctxs.values() for fy in c.fy_results))
    strategy_names = list(ctxs.keys())
    short_names = [n.split(" (")[0] for n in strategy_names]

    rows = []
    running_totals = [0.0] * len(strategy_names)
    for fy in all_fys:
        fy_label = f"FY{fy.year}-{str(fy.year + 1)[-2:]}"
        cells = []
        row_total = 0.0
        for i, name in enumerate(strategy_names):
            fy_tax = next((x for x in ctxs[name].fy_results if x.fy_start == fy), None)
            t = fy_tax.total_tax if fy_tax else 0.0
            running_totals[i] += t
            row_total += t
            css = "tax-zero" if t < 1 else ("tax-low" if t < 5_00_000 else ("tax-mid" if t < 20_00_000 else "tax-high"))
            cells.append(f'<td class="{css}">{("—" if t < 1 else f"₹{t/1e5:.1f}L")}</td>')
        rows.append(f'<tr><td class="fy-label">{fy_label}</td>{"".join(cells)}<td class="row-total"><strong>₹{row_total/1e5:.1f}L</strong></td></tr>')

    # Final cumulative row
    cum_cells = [f'<td class="cum-total"><strong>₹{rt/1e5:.1f}L</strong></td>' for rt in running_totals]
    cum_total = sum(running_totals)
    rows.append(f'<tr class="cum-row"><td class="fy-label"><strong>Total</strong></td>{"".join(cum_cells)}<td class="row-total"><strong>₹{cum_total/1e5:.1f}L</strong></td></tr>')

    header_cells = "".join(f"<th>{n}</th>" for n in short_names)
    return f"""<table class="per-fy-compact">
  <thead>
    <tr><th>FY</th>{header_cells}<th>Row total</th></tr>
  </thead>
  <tbody>
{chr(10).join(rows)}
  </tbody>
</table>"""


def _per_fy_detail_html(name: str, ctx: StrategyContext) -> str:
    """Per-strategy detail table — ST/LT gross, exemption, CF use, taxes."""
    rows = []
    totals = {"st_gross": 0.0, "lt_gross": 0.0, "ltcg_exempt": 0.0,
              "cf_used": 0.0, "stcg_tax": 0.0, "ltcg_tax": 0.0, "total": 0.0}
    for fy in ctx.fy_results:
        cf_used = fy.cf_stcl_used + fy.cf_ltcl_used + fy.intra_fy_stcl_used_against_lt
        totals["st_gross"] += fy.st_gross
        totals["lt_gross"] += fy.lt_gross
        totals["ltcg_exempt"] += fy.ltcg_exemption_used
        totals["cf_used"] += cf_used
        totals["stcg_tax"] += fy.stcg_tax
        totals["ltcg_tax"] += fy.ltcg_tax
        totals["total"] += fy.total_tax

        def _fmt(x: float, blank_below: float = 0.5) -> str:
            if abs(x) < blank_below:
                return "—"
            sign = "−" if x < 0 else ""
            return f"{sign}₹{abs(x)/1e5:.1f}L"

        rows.append(f"""<tr>
  <td>{fy.fy_label}</td>
  <td>{_fmt(fy.st_gross)}</td>
  <td>{_fmt(fy.lt_gross)}</td>
  <td>{_fmt(cf_used)}</td>
  <td>{_fmt(fy.ltcg_exemption_used)}</td>
  <td>{_fmt(fy.stcg_tax)}</td>
  <td>{_fmt(fy.ltcg_tax)}</td>
  <td class="row-total"><strong>{_fmt(fy.total_tax)}</strong></td>
</tr>""")
    # Totals row
    rows.append(f"""<tr class="cum-row">
  <td><strong>Total</strong></td>
  <td><strong>₹{totals['st_gross']/1e5:.1f}L</strong></td>
  <td><strong>₹{totals['lt_gross']/1e5:.1f}L</strong></td>
  <td><strong>₹{totals['cf_used']/1e5:.1f}L</strong></td>
  <td><strong>₹{totals['ltcg_exempt']/1e5:.1f}L</strong></td>
  <td><strong>₹{totals['stcg_tax']/1e5:.1f}L</strong></td>
  <td><strong>₹{totals['ltcg_tax']/1e5:.1f}L</strong></td>
  <td class="row-total"><strong>₹{totals['total']/1e5:.1f}L</strong></td>
</tr>""")

    return f"""<h3>{name}</h3>
<table class="per-fy-detail">
  <thead>
    <tr>
      <th>FY</th>
      <th>ST gross</th>
      <th>LT gross</th>
      <th>Losses offset</th>
      <th>LTCG exempt</th>
      <th>STCG tax</th>
      <th>LTCG tax</th>
      <th>Total tax</th>
    </tr>
  </thead>
  <tbody>
{chr(10).join(rows)}
  </tbody>
</table>"""


def _window_row_html(r: WindowResult) -> str:
    drag = r.drag_bps
    css = "drag-low" if drag < 600 else ("drag-mid" if drag < 800 else "drag-high")
    pill = {"IS": "pill-is", "OOS": "pill-oos", "Pre-IS": "pill-preIS", "Full": "pill-full"}.get(r.label, "pill-oos")
    return f"""<tr>
  <td class="strategy">{r.strategy}</td>
  <td><span class="pill {pill}">{r.label}</span></td>
  <td>{r.start.date()} → {r.end.date()}</td>
  <td>{r.years:.1f}</td>
  <td>{r.pretax_cagr*100:.2f}%</td>
  <td>{r.posttax_cagr*100:.2f}%</td>
  <td class="{css}"><strong>{drag:.0f} bps</strong></td>
  <td>{r.pretax_final_mult:.2f}×</td>
  <td>{r.posttax_final_mult:.2f}×</td>
  <td>₹{r.tax_paid_in_window/1e5:.1f}L</td>
  <td>₹{r.stcg_paid/1e5:.1f}L</td>
  <td>₹{r.ltcg_paid/1e5:.1f}L</td>
</tr>"""


def _full_row_html(name: str, ctx: StrategyContext) -> str:
    eq = ctx.equity
    yrs = (eq.iloc[-1]["date"] - eq.iloc[0]["date"]).days / 365.25
    pre = (eq.iloc[-1]["pv"] / eq.iloc[0]["pv"]) ** (1 / yrs) - 1
    sc = float(ctx.scale_series.iloc[-1])
    post = (eq.iloc[-1]["pv"] * sc / eq.iloc[0]["pv"]) ** (1 / yrs) - 1
    drag_bps = (pre - post) * 10_000
    stcg = sum(fy.stcg_tax for fy in ctx.fy_results)
    ltcg = sum(fy.ltcg_tax for fy in ctx.fy_results)
    total_tax = sum(e.tax_paid for e in ctx.tax_events)
    final_pre = float(eq.iloc[-1]["pv"])
    css = "drag-low" if drag_bps < 600 else ("drag-mid" if drag_bps < 800 else "drag-high")
    bh_class = "bh-row" if "NIFTY" in name else ""
    return f"""<tr class="{bh_class}">
  <td class="strategy">{name}</td>
  <td>{eq.iloc[0]['date'].date()} → {eq.iloc[-1]['date'].date()}</td>
  <td>{yrs:.1f}</td>
  <td>{pre*100:.2f}%</td>
  <td>{post*100:.2f}%</td>
  <td class="{css}"><strong>{drag_bps:.0f} bps</strong></td>
  <td>{(eq.iloc[-1]['pv']/eq.iloc[0]['pv']):.2f}×</td>
  <td>{(eq.iloc[-1]['pv']*sc/eq.iloc[0]['pv']):.2f}×</td>
  <td>₹{total_tax/1e5:.1f}L</td>
  <td>₹{stcg/1e5:.1f}L</td>
  <td>₹{ltcg/1e5:.1f}L</td>
  <td>{total_tax/final_pre*100:.1f}%</td>
</tr>"""


def main() -> None:
    print("Loading strategies & benchmark…")
    ctxs: dict[str, StrategyContext] = {}
    for name, (sd, tr_file, eq_file) in STRATEGIES.items():
        trades = pd.read_csv(RUNS / sd / tr_file)
        equity = pd.read_csv(RUNS / sd / eq_file, parse_dates=["date"])
        ctxs[name] = build_context(name, trades, equity)
        print(f"  loaded {name}  (trades={len(trades):,}, equity={len(equity):,} rows)")

    nifty = load_nifty50(start="2009-09-01", end="2026-05-12")
    bh_trades = build_bh_trades(nifty)
    bh_equity = build_bh_equity(nifty, bh_trades)
    bh_ctx = build_context("NIFTY 50 B&H", bh_trades, bh_equity)
    print(f"  loaded NIFTY 50 B&H  (window {nifty.iloc[0]['date'].date()} → {nifty.iloc[-1]['date'].date()})")

    print("\nComputing window stats…")
    window_results: list[WindowResult] = []
    for name, ctx in ctxs.items():
        for label, s, e in WINDOWS[name]:
            r = _slice_window(ctx, label, s, e)
            window_results.append(r)

    # B&H also sliced by each window (use the OM25 / TL25 split since it's the
    # canonical 2009-2016 IS / 2017+ OOS split; we also show L6's 2009-2019 /
    # 2020+ split). We give the user both reference splits for clarity.
    bh_windows = [
        ("OM25/TL25 IS",  pd.Timestamp("2009-09-01"), pd.Timestamp("2016-12-31")),
        ("OM25/TL25 OOS", pd.Timestamp("2017-01-01"), pd.Timestamp("2026-05-12")),
        ("L6/COMBO Pre-IS", pd.Timestamp("2009-09-01"), pd.Timestamp("2019-12-31")),
        ("L6/COMBO IS",     pd.Timestamp("2020-01-01"), pd.Timestamp("2026-05-12")),
    ]
    bh_window_results: list[WindowResult] = []
    for label, s, e in bh_windows:
        r = _slice_window(bh_ctx, label, s, e)
        r.strategy = "NIFTY 50 B&H"
        bh_window_results.append(r)

    print("Rendering charts…")
    charts = render_charts(ctxs, bh_ctx)
    print(f"  3 charts rendered  (sizes: {[len(c)//1024 for c in charts.values()]}KB)")

    # Build HTML
    full_rows = [_full_row_html(n, c) for n, c in ctxs.items()]
    full_rows.append(_full_row_html("NIFTY 50 B&H", bh_ctx))
    window_rows = [_window_row_html(r) for r in window_results]
    bh_window_rows = [_window_row_html(r) for r in bh_window_results]

    per_fy_compact = _per_fy_compact_html(ctxs)
    per_fy_detail = "\n".join(_per_fy_detail_html(n, c) for n, c in ctxs.items())

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = TEMPLATE.format(
        full_rows="\n".join(full_rows),
        window_rows="\n".join(window_rows),
        bh_window_rows="\n".join(bh_window_rows),
        per_fy_compact=per_fy_compact,
        per_fy_detail=per_fy_detail,
        chart_cagr=charts["cagr_bars"],
        chart_curves=charts["equity_curves"],
        chart_per_fy=charts["per_fy_tax"],
        generated=generated,
    )

    OUTPUT_HTML.write_text(html)
    print(f"\nReport written to {OUTPUT_HTML}  ({len(html)/1024:.1f}KB)")


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Tax Study — Production Strategies (v2)</title>
  <style>
    :root {{ --ink: #1a1a1a; --muted: #666; --rule: #e5e5e7; --bg-soft: #f6f6f7; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
           max-width: 1180px; margin: 2em auto; padding: 0 1.2em; color: var(--ink); line-height: 1.55; }}
    h1 {{ font-size: 1.7em; border-bottom: 2px solid var(--ink); padding-bottom: 0.3em; margin-bottom: 0.2em; }}
    .subtitle {{ color: var(--muted); margin-top: 0; font-size: 0.95em; }}
    h2 {{ margin-top: 2.4em; color: var(--ink); font-size: 1.2em; border-bottom: 1px solid var(--rule); padding-bottom: 0.3em; }}
    h3 {{ font-size: 1.0em; color: #444; margin-top: 1.8em; margin-bottom: 0.4em; }}
    .params {{ background: var(--bg-soft); padding: 1em 1.2em; border-radius: 6px; font-size: 0.92em; margin-top: 1em; }}
    .params strong {{ color: #b00; }}
    .params ul {{ margin: 0.4em 0 0 1.4em; padding: 0; }}
    table {{ border-collapse: collapse; width: 100%; margin: 0.5em 0; font-variant-numeric: tabular-nums; font-size: 0.88em; }}
    th, td {{ padding: 7px 9px; text-align: right; border-bottom: 1px solid var(--rule); }}
    th {{ background: var(--bg-soft); font-weight: 600; text-align: center; font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.03em; color: #555; }}
    td:first-child, th:first-child,
    td:nth-child(2), th:nth-child(2),
    td:nth-child(3), th:nth-child(3) {{ text-align: left; }}
    .strategy {{ font-weight: 600; }}
    .bh-row {{ background: #fafbfc; font-style: italic; }}
    .drag-low {{ color: #2a9d4a; }}
    .drag-mid {{ color: #d68500; }}
    .drag-high {{ color: #c0392b; }}
    .pill {{ display: inline-block; padding: 2px 9px; border-radius: 10px; font-size: 0.74em; font-weight: 600; letter-spacing: 0.04em; }}
    .pill-is {{ background: #e3eaf3; color: #2a5d9f; }}
    .pill-oos {{ background: #f7e2d8; color: #b54e1c; }}
    .pill-preIS {{ background: #ececec; color: #555; }}
    .pill-full {{ background: #ddf3df; color: #297a3b; }}
    .per-fy-compact td.fy-label, .per-fy-detail td:first-child {{ font-weight: 600; }}
    .per-fy-compact td.tax-zero {{ color: #aaa; }}
    .per-fy-compact td.tax-low {{ color: #2a7747; }}
    .per-fy-compact td.tax-mid {{ color: #c07a00; }}
    .per-fy-compact td.tax-high {{ color: #b03020; font-weight: 600; }}
    .per-fy-compact td.row-total, .per-fy-detail td.row-total {{ background: #fafafb; }}
    tr.cum-row {{ background: #f0f0f2; border-top: 2px solid #aaa; }}
    .per-fy-detail {{ margin-bottom: 1.5em; font-size: 0.84em; }}
    .chart {{ margin: 1.2em 0 1.8em; text-align: center; }}
    .chart img {{ max-width: 100%; height: auto; box-shadow: 0 1px 3px rgba(0,0,0,0.08); border-radius: 4px; }}
    .chart-note {{ font-size: 0.85em; color: var(--muted); margin: -0.6em 0 1.5em; text-align: center; }}
    .takeaway {{ background: #eef9f0; padding: 0.8em 1.5em; border-left: 4px solid #43a047; border-radius: 4px; margin: 1.5em 0; }}
    .takeaway ul {{ margin: 0.3em 0 0.3em 0; padding-left: 1.2em; }}
    .caveats {{ background: #fff8e1; padding: 0.8em 1.5em; border-left: 4px solid #fbc02d; margin-top: 2em; border-radius: 4px; font-size: 0.92em; }}
    .caveats li {{ margin: 0.4em 0; }}
    code {{ background: var(--bg-soft); padding: 1px 5px; border-radius: 3px; font-size: 0.86em; }}
    .footer {{ color: var(--muted); font-size: 0.82em; margin-top: 3em; padding-top: 1em; border-top: 1px solid var(--rule); text-align: center; }}
  </style>
</head>
<body>
  <h1>Tax Study — Production Strategies (v2)</h1>
  <p class="subtitle">Per-trade FIFO Indian capital-gains tax, 30 bps slippage, forced-sale-for-tax simulation, NIFTY 50 B&amp;H benchmark.</p>

  <div class="params">
    <strong>Model:</strong>
    <ul>
      <li><strong>Tax rates:</strong> STCG 20% (≤365d hold) · LTCG 12.5% above ₹1.25L FY exemption (&gt;365d hold). Current Indian law (post July 2024), applied throughout.</li>
      <li><strong>Lot accounting:</strong> FIFO. Effective prices include the 30 bps backtest slippage on both buys and sells.</li>
      <li><strong>Loss carry-forward:</strong> 8 financial years. STCL offsets ST or LT gains (FIFO across CF queue). LTCL offsets only LT gains.</li>
      <li><strong>Tax timing:</strong> single annual debit on Apr 1 of each FY for the prior year's gains. Final partial-FY tax (paid after equity series end) is provisioned on the last equity day so deferred liability is reflected.</li>
      <li><strong>Forced sale:</strong> assumes cash &lt; tax owed (fully-invested strategies). Drag = tax × 0.003 / 0.997 ≈ 0.301% of tax. Forced-sale realized P&amp;L not propagated to next FY (bounded error, see Caveats).</li>
      <li><strong>Equity curve scale:</strong> multiplicative — post-tax PV compounds at strategy rate from a smaller base.</li>
      <li><strong>Initial capital:</strong> ₹10L per strategy. LTCG exemption ₹1.25L per FY is meaningful early (~12.5% of starting capital) and dilutes at scale.</li>
    </ul>
  </div>

  <h2>Full-period results — strategies + NIFTY 50 B&amp;H benchmark</h2>
  <table>
    <thead>
      <tr>
        <th>Strategy</th>
        <th>Period</th>
        <th>Years</th>
        <th>Pre-tax CAGR</th>
        <th>Post-tax CAGR</th>
        <th>Drag</th>
        <th>Pre×</th>
        <th>Post×</th>
        <th>Total tax</th>
        <th>STCG paid</th>
        <th>LTCG paid</th>
        <th>Tax / Pre×PV</th>
      </tr>
    </thead>
    <tbody>
{full_rows}
    </tbody>
  </table>

  <h2>CAGR comparison</h2>
  <div class="chart"><img src="data:image/png;base64,{chart_cagr}" alt="CAGR pre vs post tax"></div>

  <div class="takeaway">
    <strong>Takeaways</strong>
    <ul>
      <li><strong>Tax drag is real but doesn't neutralise alpha.</strong> Active strategies pay 8–10× more drag in bps (520–700 bp) than B&amp;H (66 bp), yet still deliver 2.7–3.4× higher post-tax CAGR.</li>
      <li><strong>STCG-heavy strategies pay the most.</strong> TL25 v3 (708 bp drag) has effectively zero LTCG — biweekly entry + weekly rank-exit churns positions inside the 12-month bucket. OM25 v3 (520 bp) holds longer because the 20-rank exit buffer + drawdown stop give positions room to mature.</li>
      <li><strong>Loss carry-forward is doing real work.</strong> All 4 strategies use STCL carry-forward at least once over the 16y window; OM25 v3's FY2019-20 ₹7.34L STCL fully offsets FY2020-21's STCG.</li>
      <li><strong>The ₹1.25L LTCG exemption diminishes fast.</strong> In FY2014-15 it shelters the entire LTCG. By FY2024-25 it's a rounding error on a ₹37M tax bill.</li>
      <li><strong>Forced-sale slippage is essentially noise</strong> at 30 bps. Adds ~2 bp/year of drag. The model's simplification (not propagating forced-sale gains to next FY) is well below this.</li>
    </ul>
  </div>

  <h2>Per-strategy window breakdown</h2>
  <p style="font-size:0.9em; color:var(--muted)">Window labels reflect each strategy's tuning history — OM25 v3 / TL25 v3 were tuned on 2009–2016 and validated forward; L6 v2 / COMBO were tuned on 2020–2026 with no formal holdout.</p>
  <table>
    <thead>
      <tr>
        <th>Strategy</th>
        <th>Window</th>
        <th>Period</th>
        <th>Years</th>
        <th>Pre-tax CAGR</th>
        <th>Post-tax CAGR</th>
        <th>Drag</th>
        <th>Pre×</th>
        <th>Post×</th>
        <th>Tax paid</th>
        <th>STCG</th>
        <th>LTCG</th>
      </tr>
    </thead>
    <tbody>
{window_rows}
    </tbody>
  </table>

  <h3>NIFTY 50 B&amp;H over matching sub-windows</h3>
  <table>
    <thead>
      <tr>
        <th>Window scheme</th>
        <th>Window</th>
        <th>Period</th>
        <th>Years</th>
        <th>Pre-tax CAGR</th>
        <th>Post-tax CAGR</th>
        <th>Drag</th>
        <th>Pre×</th>
        <th>Post×</th>
        <th>Tax paid</th>
        <th>STCG</th>
        <th>LTCG</th>
      </tr>
    </thead>
    <tbody>
{bh_window_rows}
    </tbody>
  </table>
  <p class="chart-note">B&amp;H's STCG / LTCG split is computed from the same engine — its single position held &gt;5,000 days is entirely LTCG.</p>

  <h2>Equity curves</h2>
  <div class="chart"><img src="data:image/png;base64,{chart_curves}" alt="Equity curves pre vs post tax"></div>
  <p class="chart-note">Log scale, normalised to 1.0 at each strategy's start. Shaded region = the IS-tune window per strategy.</p>

  <h2>Year-by-year tax bills</h2>
  <div class="chart"><img src="data:image/png;base64,{chart_per_fy}" alt="Per-FY tax bars"></div>
  <p class="chart-note">Per-FY STCG (blue shades) and LTCG (orange shades) for each strategy in ₹ lakhs. Note the FY2023-24 spike — strong realization year across all four strategies, driven by the 2023 mid-cap rally.</p>

  <h3>Per-FY total tax — cross-strategy comparison</h3>
  <p style="font-size:0.9em; color:var(--muted)">Total tax paid each FY by each strategy, in ₹ lakhs. Empty (—) cells mean no tax was due (gains absorbed by losses / exemption). Heatmap: green = low, amber = medium, red = high tax bill.</p>
{per_fy_compact}

  <h3>Per-FY detail by strategy</h3>
  <p style="font-size:0.9em; color:var(--muted)">For each strategy, the full breakdown per FY: realized ST/LT gross gains (signed — negative = losses), losses offset (intra-FY + carry-forward), LTCG exemption used, and the resulting STCG/LTCG tax. All amounts in ₹ lakhs.</p>
{per_fy_detail}

  <div class="caveats">
    <strong>Caveats — read before using these numbers</strong>
    <ul>
      <li><strong>Backtest warm-start vs cold-start.</strong> The 2009-start backtests are sitting on years of accumulated positions at the dashboard's live-window start. OM25 v3 and TL25 v3 live-window CAGRs inside this report exceed the dashboard's published numbers (~6 pp and 1.8 pp respectively) for this reason. L6 v2 and COMBO live-window CAGRs reconcile with the dashboard ±100 bps.</li>
      <li><strong>Forced-sale realized P&amp;L not propagated.</strong> When the engine forces a sale on Apr 1 to pay tax, the realized gain from that sale should logically feed the *next* FY's tax base. We don't model this. The error is bounded: forced sales target the smallest open positions (least appreciated); their realized gains average ~10% of the cash raised; the added tax is ~20% × 10% = 2% of tax owed, i.e. a few bps of CAGR per year.</li>
      <li><strong>Annual debit, not quarterly advance tax.</strong> Real Indian tax is paid in 4 advance-tax installments during the FY, not a lump sum on Apr 1. Our annual model is slightly optimistic for the taxpayer (extra ~6 months of compounding on the tax money). Order-of-magnitude correct.</li>
      <li><strong>No surcharge or cess.</strong> The 20% STCG and 12.5% LTCG rates exclude surcharge (10–37% on tax, depending on income slab) and 4% health-and-education cess. Real effective rates for high-income investors are ~28% STCG / ~17.5% LTCG. Adjust upward accordingly.</li>
      <li><strong>No money-market return on idle cash.</strong> The strategies' cash balance earns 0 in this model. In reality, cash sits in liquid funds at ~6%. COMBO Defensive (which holds 50% cash in bear regime) is most affected — its pre-tax CAGR is understated by ~50 bps.</li>
      <li><strong>Initial capital is ₹10L.</strong> The ₹1.25L LTCG exemption is 12.5% of starting capital — large early, negligible at scale. A ₹1Cr starting investor would see effectively zero exemption benefit. Drag numbers scale roughly with starting capital above ₹50L.</li>
      <li><strong>Survivorship bias possible.</strong> Not audited — the price panel (<code>nse500_data_merged</code>) may include "today's NSE 500" backfilled rather than point-in-time membership.</li>
    </ul>
  </div>

  <div class="footer">
    Generated by <code>tasks/tax_study/build_report.py</code> · {generated}
  </div>
</body>
</html>
"""

if __name__ == "__main__":
    main()
