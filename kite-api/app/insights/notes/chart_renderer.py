"""Branded chart renderer for the Daily Quant Note.

Produces 1080×1350 PNG (Instagram/WhatsApp portrait, mobile-first).
Charts are designed to be legible at WhatsApp thumbnail resolution
(375px wide) — large labels, minimal axis clutter, no more than 2-3
series per panel.

Three primitive renderers, each takes a matplotlib Axes:
  render_stress_timeseries(ax, reading, lookback_days)
  render_sector_leaderboard(ax, reading, window)
  render_analog_fan(ax, reading)

Two composed images (used by templates):
  make_postclose_image(reading) — 2-panel stress + sectors
  make_weekly_image(reading)    — 3-panel adds analog fan at bottom

Both return raw PNG bytes for the note_assembler / API to send.
"""
from __future__ import annotations

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # required for headless image generation
import matplotlib.dates as mdates
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.insights import regime as regime_mod
from app.insights.reading import MarketReading
from app.insights.stress import compute_stress_panel


# Marketworks brand palette (chosen for legibility + light-mode WhatsApp default)
BRAND_DARK = "#0F2940"
BRAND_ACCENT = "#3D8BFD"
GRID = "#E1E5EA"
TEXT = "#1A2330"
MUTED = "#6B7785"

# Regime → fill color for the stress chart's background bands
REGIME_COLORS = {
    regime_mod.TREND_BULL: "#D8F0E0",  # very light green
    regime_mod.DRIFT:      "#F2F4F6",  # near-white grey
    regime_mod.STRETCHED:  "#FFE4B5",  # soft amber
    regime_mod.STRESS:     "#FCD9D9",  # soft red
}


def _setup_axes(ax, ylabel: str | None = None):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=11)
    ax.grid(axis="y", color=GRID, linewidth=0.7, alpha=0.6)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT, fontsize=12)


# ---------- primitive renderers ----------

def render_stress_timeseries(ax, reading: MarketReading,
                              lookback_days: int = 252) -> None:
    """Stress score 0-100 over the last N trading days, with regime
    background shading and the current value annotated."""
    panel = compute_stress_panel()
    regime_panel = regime_mod.compute_regime_panel()
    asof = reading.date

    # Window: last `lookback_days` trading days ending at asof
    valid = panel.index[panel.index <= asof]
    if len(valid) < 10:
        return
    end = valid[-1]
    start_pos = max(0, len(valid) - lookback_days)
    start = valid[start_pos]
    window_idx = valid[start_pos:]

    scores = panel.loc[window_idx, "score"]
    regimes = regime_panel.loc[window_idx, "regime"] if not regime_panel.empty else None

    # Regime shading
    if regimes is not None and not regimes.empty:
        runs = (regimes != regimes.shift()).cumsum()
        for _, group in regimes.groupby(runs):
            r = group.iloc[0]
            color = REGIME_COLORS.get(r)
            if color:
                ax.axvspan(group.index[0], group.index[-1],
                           color=color, alpha=0.6, linewidth=0)

    # Stress line
    ax.plot(scores.index, scores.values, color=BRAND_DARK, linewidth=2.2)
    ax.fill_between(scores.index, 0, scores.values, color=BRAND_DARK, alpha=0.05)

    # Current value annotation
    current_score = scores.iloc[-1]
    ax.scatter([end], [current_score], color=BRAND_DARK, s=70, zorder=5,
               edgecolor="white", linewidth=2)
    ax.annotate(
        f"{current_score:.0f}",
        xy=(end, current_score),
        xytext=(8, 6), textcoords="offset points",
        fontsize=16, fontweight="bold", color=BRAND_DARK,
    )

    # Horizontal reference lines for stress bands
    for y, label in [(20, "calm"), (60, "elevated"), (80, "panic")]:
        ax.axhline(y, color=GRID, linewidth=0.8, linestyle="--", alpha=0.7)
        ax.text(scores.index[0], y + 1, label, color=MUTED, fontsize=9,
                va="bottom", ha="left")

    _setup_axes(ax, ylabel="Stress")
    ax.set_ylim(0, 100)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
    ax.set_title(
        "Market stress over the past 12 months",
        loc="left", color=TEXT, fontsize=14, fontweight="bold", pad=12,
    )


def render_sector_leaderboard(ax, reading: MarketReading, window: str = "60d") -> None:
    """Horizontal bar chart of sector RS for `window`, sorted descending."""
    board = reading.sector_leaderboard_60d if window == "60d" else list(reading.sector_rs.values())
    if window != "60d":
        rank_attr = f"rank_{window}"
        board = sorted(board, key=lambda s: getattr(s, rank_attr) or 9999)

    # Extract values for bars
    names = [s.sector.replace("NIFTY_", "") for s in board]
    values = []
    breadths = []
    for s in board:
        rs = getattr(s, f"rs_{window}")
        values.append(rs * 100 if rs is not None else 0)
        breadths.append(s.pct_above_200dma)

    # Color by sign
    colors = [BRAND_ACCENT if v >= 0 else "#E07A6C" for v in values]

    y_pos = np.arange(len(names))[::-1]
    bars = ax.barh(y_pos, values, color=colors, height=0.7)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=11, color=TEXT)

    # Value label at bar tip
    max_abs = max((abs(v) for v in values), default=1)
    offset = max_abs * 0.02
    for i, (bar, v, b) in enumerate(zip(bars, values, breadths)):
        # RS value
        x = bar.get_width() + (offset if v >= 0 else -offset)
        ha = "left" if v >= 0 else "right"
        ax.text(x, bar.get_y() + bar.get_height() / 2,
                f"{v:+.1f}%", va="center", ha=ha, fontsize=10, color=TEXT)
        # Breadth chip (right-justified outside the chart on positive bars,
        # or to the left of negative bars)
        if b is not None:
            chip = f"{int(b*100)}%"
            chip_x = max_abs * 1.20 if v >= 0 else -max_abs * 1.20
            ax.text(chip_x, bar.get_y() + bar.get_height() / 2,
                    chip, va="center", ha="center", fontsize=9, color=MUTED)

    _setup_axes(ax)
    ax.axvline(0, color=TEXT, linewidth=0.8)
    ax.tick_params(axis="x", labelsize=10)
    ax.set_xlim(-max_abs * 1.3, max_abs * 1.3)
    ax.set_title(
        f"Sector relative strength vs Nifty 50 (3-month) · breadth at right",
        loc="left", color=TEXT, fontsize=12, fontweight="bold", pad=10,
    )


def render_analog_fan(ax, reading: MarketReading) -> None:
    """Fan chart: forward-return distribution across analogs at multiple
    horizons. Shows p5/p25/median/p75/p95 of the 20 closest analogs."""
    dist = reading.analog_distribution
    if not dist:
        ax.text(0.5, 0.5, "No analog distribution available",
                ha="center", va="center", color=MUTED, transform=ax.transAxes)
        return

    horizons = sorted(dist.keys())
    medians = [dist[h].median for h in horizons]
    p25s = [dist[h].p25 for h in horizons]
    p75s = [dist[h].p75 for h in horizons]
    p5s = [dist[h].p5 for h in horizons]
    p95s = [dist[h].p95 for h in horizons]

    # Convert to pct for display
    medians_pct = [v * 100 if v is not None else 0 for v in medians]
    p25s_pct = [v * 100 if v is not None else 0 for v in p25s]
    p75s_pct = [v * 100 if v is not None else 0 for v in p75s]
    p5s_pct = [v * 100 if v is not None else 0 for v in p5s]
    p95s_pct = [v * 100 if v is not None else 0 for v in p95s]

    ax.fill_between(horizons, p5s_pct, p95s_pct, color=BRAND_ACCENT, alpha=0.15,
                    label="5-95% range")
    ax.fill_between(horizons, p25s_pct, p75s_pct, color=BRAND_ACCENT, alpha=0.30,
                    label="25-75% range")
    ax.plot(horizons, medians_pct, color=BRAND_DARK, linewidth=2.2, marker="o",
            label="median")
    ax.axhline(0, color=TEXT, linewidth=0.8)

    _setup_axes(ax, ylabel="Nifty fwd return")
    ax.set_xticks(horizons)
    ax.set_xticklabels([f"{h}d" for h in horizons])
    ax.set_xlabel("Trading days forward", color=MUTED, fontsize=11)
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.set_title(
        "Historical analog forward-return distribution (20 closest matches)",
        loc="left", color=TEXT, fontsize=12, fontweight="bold", pad=10,
    )


# ---------- composed images ----------

def _draw_header_footer(fig, reading: MarketReading,
                        title: str, subtitle: str | None = None) -> None:
    """Add brand header bar + footer (date, dashboard URL) to the figure."""
    # Header bar
    header = patches.Rectangle((0, 0.945), 1, 0.055,
                                transform=fig.transFigure,
                                color=BRAND_DARK, zorder=10, linewidth=0)
    fig.patches.append(header)
    fig.text(0.05, 0.972, "MARKETWORKS · DAILY QUANT NOTE",
             color="white", fontsize=14, fontweight="bold",
             va="center", ha="left")
    fig.text(0.95, 0.972, reading.date.strftime("%a, %d %b %Y"),
             color="white", fontsize=11, va="center", ha="right")

    # Title area below header
    fig.text(0.05, 0.910, title, color=TEXT, fontsize=18, fontweight="bold",
             va="top", ha="left")
    if subtitle:
        fig.text(0.05, 0.875, subtitle, color=MUTED, fontsize=12,
                 va="top", ha="left")

    # Footer
    fig.text(0.05, 0.018,
             "Not investment advice · Past patterns do not guarantee future outcomes",
             color=MUTED, fontsize=9, va="center", ha="left")
    fig.text(0.95, 0.018, "marketworks.in/insights",
             color=MUTED, fontsize=9, va="center", ha="right")


def make_postclose_image(reading: MarketReading) -> bytes:
    """2-panel post-close image: stress timeseries (top) + sector bars (bottom).

    Returns raw PNG bytes (1080×1350)."""
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor="white")

    # Header / title content
    headline_subtitle = (
        f"Regime: {reading.regime.regime.replace('_', ' ').title()} · "
        f"Stress: {reading.stress.score:.0f}/100"
    )
    _draw_header_footer(fig, reading,
                        title="Today's Market Pulse",
                        subtitle=headline_subtitle)

    # 2-panel layout — leave room for header (top) + footer (bottom)
    gs = fig.add_gridspec(
        2, 1, height_ratios=[1.0, 1.4],
        left=0.08, right=0.95, top=0.84, bottom=0.06, hspace=0.32,
    )
    ax_stress = fig.add_subplot(gs[0])
    ax_sector = fig.add_subplot(gs[1])

    render_stress_timeseries(ax_stress, reading, lookback_days=252)
    render_sector_leaderboard(ax_sector, reading, window="60d")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches=None, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def make_weekly_image(reading: MarketReading) -> bytes:
    """3-panel weekly digest image: stress + sectors + analog fan."""
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor="white")

    headline_subtitle = (
        f"Regime: {reading.regime.regime.replace('_', ' ').title()} · "
        f"Stress: {reading.stress.score:.0f}/100 · Week ending {reading.date.strftime('%d %b')}"
    )
    _draw_header_footer(fig, reading,
                        title="Weekly Market Digest",
                        subtitle=headline_subtitle)

    gs = fig.add_gridspec(
        3, 1, height_ratios=[1.0, 1.4, 1.0],
        left=0.08, right=0.95, top=0.84, bottom=0.06, hspace=0.40,
    )
    render_stress_timeseries(fig.add_subplot(gs[0]), reading, lookback_days=252)
    render_sector_leaderboard(fig.add_subplot(gs[1]), reading, window="60d")
    render_analog_fan(fig.add_subplot(gs[2]), reading)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches=None, facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ---------- convenience for CLI workflows ----------

def save_postclose_image(reading: MarketReading, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(make_postclose_image(reading))
    return path


def save_weekly_image(reading: MarketReading, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(make_weekly_image(reading))
    return path
