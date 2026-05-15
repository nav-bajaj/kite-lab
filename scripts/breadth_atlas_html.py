"""Render the Breadth Atlas as a single self-contained HTML report.

Reads `REPORT.md` + section CSVs + figures from `tasks/breadth_atlas/` and
emits `tasks/breadth_atlas/REPORT.html` with:
- The narrative converted from markdown.
- All section figures embedded inline as base64 PNGs (no external deps).
- The headline tables rendered as HTML.
- A sticky table-of-contents sidebar.

Run:
    python scripts/breadth_atlas_html.py
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import pandas as pd
import markdown as md_lib

ROOT = Path(__file__).resolve().parents[1]
ATLAS_DIR = ROOT / "tasks" / "breadth_atlas"
FIG_DIR = ATLAS_DIR / "figures"
REPORT_MD = ATLAS_DIR / "REPORT.md"
OUT_HTML = ATLAS_DIR / "REPORT.html"

METRIC_NAMES = [
    "pct_above_200dma", "pct_above_100dma", "pct_above_50dma", "pct_above_21dma",
    "ad_ratio", "ad_net_pct", "ad_line",
    "mcclellan_osc", "mcclellan_sum",
    "pct_at_52w_high", "pct_at_52w_low", "net_new_highs_pct",
    "up_vol_ratio", "avg_dist_from_200dma",
]


def img_b64(p: Path) -> str:
    if not p.exists():
        return ""
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{data}"


def img_tag(p: Path, alt: str = "", cls: str = "fig") -> str:
    src = img_b64(p)
    if not src:
        return f'<div class="missing">[missing: {p.relative_to(ROOT)}]</div>'
    return f'<img class="{cls}" src="{src}" alt="{alt or p.stem}" loading="lazy"/>'


def df_to_html(df: pd.DataFrame, max_rows: int | None = None, formatters: dict | None = None) -> str:
    if max_rows is not None and len(df) > max_rows:
        df = df.head(max_rows)
    return df.to_html(
        classes="atlas-table",
        border=0,
        formatters=formatters,
        float_format=lambda x: f"{x:.4f}" if abs(x) < 1000 else f"{x:.1f}",
    )


def load_csv(name: str) -> pd.DataFrame | None:
    p = ATLAS_DIR / name
    if not p.exists():
        return None
    return pd.read_csv(p)


def build_section_extras() -> dict[str, str]:
    """Build HTML chunks for each section's tables + figures, keyed by section id."""

    out = {}

    # --- Section 1: distributions + per-year heatmap ---
    s1_stats = load_csv("section1_distribution_stats.csv")
    s1_yearly = load_csv("section1_yearly_means.csv")
    s1_html = ['<h3 class="extra">Tables</h3>']
    if s1_stats is not None:
        cols_to_show = ["metric", "min", "p05", "median", "p95", "max", "std", "skew", "kurtosis"]
        s1_html.append('<div class="table-wrap"><h4>Distribution stats (full sample)</h4>')
        s1_html.append(df_to_html(s1_stats[cols_to_show]))
        s1_html.append("</div>")
    if s1_yearly is not None:
        s1_html.append('<div class="table-wrap"><h4>Per-year means (structural drift)</h4>')
        s1_html.append(df_to_html(s1_yearly))
        s1_html.append("</div>")

    s1_html.append('<h3 class="extra">Distribution histograms (14)</h3>')
    s1_html.append('<div class="grid">')
    for m in METRIC_NAMES:
        s1_html.append(f'<div class="grid-cell"><div class="cap">{m}</div>')
        s1_html.append(img_tag(FIG_DIR / "distributions" / f"{m}.png", alt=m))
        s1_html.append('</div>')
    s1_html.append("</div>")
    out["section-1"] = "\n".join(s1_html)

    # --- Section 2: dwell-time heatmaps + CDF + table ---
    s2_dwell = load_csv("section2_dwell_times.csv")
    s2_html = ['<h3 class="extra">Heatmaps</h3>']
    s2_html.append(img_tag(FIG_DIR / "dwell_time" / "heatmap_pct.png", alt="dwell-time pct"))
    s2_html.append(img_tag(FIG_DIR / "dwell_time" / "heatmap_osc.png", alt="dwell-time osc"))
    s2_html.append('<h3 class="extra">Deep-breadth (<20%) run-length CDF</h3>')
    s2_html.append(img_tag(FIG_DIR / "dwell_time" / "run_length_cdf.png", alt="run length CDF"))
    if s2_dwell is not None:
        s2_html.append('<h3 class="extra">Full dwell-time table</h3>')
        s2_html.append('<div class="table-wrap scroll">')
        s2_html.append(df_to_html(s2_dwell))
        s2_html.append('</div>')
    out["section-2"] = "\n".join(s2_html)

    # --- Section 3: extremes catalog (top 30) ---
    s3 = load_csv("section3_extremes.csv")
    s3_html = []
    if s3 is not None:
        s3_html.append('<h3 class="extra">Top 30 longest extreme events</h3>')
        longest = s3.nlargest(30, "duration_days")
        s3_html.append('<div class="table-wrap scroll">')
        s3_html.append(df_to_html(longest))
        s3_html.append('</div>')

        s3_html.append('<h3 class="extra">Deepest concurrent NIFTY 100 drawdowns during extreme events</h3>')
        deepest = s3.nsmallest(30, "n100_dd_during_pct")
        s3_html.append('<div class="table-wrap scroll">')
        s3_html.append(df_to_html(deepest))
        s3_html.append('</div>')

        s3_html.append(f'<p class="note">Full catalog: {len(s3):,} events across {s3["metric"].nunique()} metrics — see <code>section3_extremes.csv</code>.</p>')
    out["section-3"] = "\n".join(s3_html)

    # --- Section 4: mean reversion table ---
    s4 = load_csv("section4_mean_reversion.csv")
    s4_html = []
    if s4 is not None:
        s4_html.append('<h3 class="extra">Mean-reversion characterization</h3>')
        s4_html.append('<div class="table-wrap">')
        s4_html.append(df_to_html(s4))
        s4_html.append('</div>')
    out["section-4"] = "\n".join(s4_html)

    # --- Section 5: index relationship plots (14, paginated visually) ---
    s5 = load_csv("section5_conditional.csv")
    s5_html = ['<h3 class="extra">Per-metric 4-panel charts (overlay, scatter vs index, scatter vs drawdown, conditional)</h3>']
    s5_html.append('<div class="stack">')
    for m in METRIC_NAMES:
        s5_html.append(f'<div class="stack-cell"><div class="cap">{m}</div>')
        s5_html.append(img_tag(FIG_DIR / "index_relationship" / f"{m}.png", alt=m, cls="fig wide"))
        s5_html.append('</div>')
    s5_html.append('</div>')
    if s5 is not None:
        s5_html.append('<h3 class="extra">Conditional table (bucket → mean concurrent N100 DD)</h3>')
        s5_html.append('<div class="table-wrap scroll">')
        s5_html.append(df_to_html(s5))
        s5_html.append('</div>')
    out["section-5"] = "\n".join(s5_html)

    # --- Section 6: correlation + PCA ---
    s6_html = ['<h3 class="extra">Pearson + Spearman correlation heatmaps</h3>']
    s6_html.append(img_tag(FIG_DIR / "correlation" / "pearson.png", alt="pearson"))
    s6_html.append(img_tag(FIG_DIR / "correlation" / "spearman.png", alt="spearman"))

    s6_var = load_csv("section6_pca_variance.csv")
    s6_load = load_csv("section6_pca_loadings.csv")
    if s6_var is not None:
        s6_html.append('<h3 class="extra">PCA — variance explained</h3>')
        s6_html.append('<div class="table-wrap">')
        s6_html.append(df_to_html(s6_var))
        s6_html.append('</div>')
    if s6_load is not None:
        s6_html.append('<h3 class="extra">PCA loadings (PC1 + PC2 — top axes)</h3>')
        cols = ["Unnamed: 0", "PC1", "PC2", "PC3", "PC4", "PC5", "PC6"]
        cols = [c for c in cols if c in s6_load.columns]
        s6_load_view = s6_load[cols].rename(columns={"Unnamed: 0": "metric"})
        s6_html.append('<div class="table-wrap">')
        s6_html.append(df_to_html(s6_load_view))
        s6_html.append('</div>')

    s6_pearson = load_csv("section6_pearson.csv")
    if s6_pearson is not None:
        s6_html.append('<h3 class="extra">Pearson correlation matrix (table form)</h3>')
        s6_html.append('<div class="table-wrap scroll">')
        s6_html.append(df_to_html(s6_pearson))
        s6_html.append('</div>')
    out["section-6"] = "\n".join(s6_html)

    return out


def render_html() -> str:
    md_text = REPORT_MD.read_text()
    body_html = md_lib.markdown(md_text, extensions=["tables", "fenced_code", "toc"])

    # Build section extras and inject after each section header.
    extras = build_section_extras()

    # Inject extras: insert each extras chunk before the next <h2> tag matching the section
    # title pattern. We'll use anchor-based injection: append extras as separate section blocks.
    # Simpler approach: append the extras after the body, in order, each in its own section.

    extras_html = '\n<hr/>\n<h2 id="figures-tables">Section figures &amp; tables</h2>\n'
    extras_html += '<p class="note">Each section\'s narrative is above; the figures, tables, and detailed catalogs sit below in matching order.</p>\n'
    for section_id, label in [
        ("section-1", "Section 1 — Distribution profile"),
        ("section-2", "Section 2 — Dwell-time analysis"),
        ("section-3", "Section 3 — Extreme-event catalog"),
        ("section-4", "Section 4 — Mean-reversion characterization"),
        ("section-5", "Section 5 — Index relationship"),
        ("section-6", "Section 6 — Cross-metric correlation + PCA"),
    ]:
        extras_html += f'\n<section id="{section_id}" class="section-block">\n'
        extras_html += f'<h2>{label}</h2>\n'
        extras_html += extras.get(section_id, "")
        extras_html += "\n</section>\n"

    # Build TOC
    toc = """
    <nav class="toc">
      <h3>Atlas</h3>
      <ul>
        <li><a href="#breadth-atlas-empirical-profile-of-nse-500-market-breadth">Top</a></li>
        <li><a href="#section-1-distribution-profile">1. Distribution</a></li>
        <li><a href="#section-2-dwell-time-analysis">2. Dwell-time</a></li>
        <li><a href="#section-3-extreme-event-catalog">3. Extremes</a></li>
        <li><a href="#section-4-mean-reversion-characterization">4. Mean reversion</a></li>
        <li><a href="#section-5-index-relationship-descriptive-only">5. Index relationship</a></li>
        <li><a href="#section-6-cross-metric-correlation-pca">6. Correlation + PCA</a></li>
        <li><a href="#headline-takeaways-the-30-second-read">Headlines</a></li>
        <li class="sep">— Figures —</li>
        <li><a href="#section-1">Section 1 figures</a></li>
        <li><a href="#section-2">Section 2 figures</a></li>
        <li><a href="#section-3">Section 3 figures</a></li>
        <li><a href="#section-4">Section 4 figures</a></li>
        <li><a href="#section-5">Section 5 figures</a></li>
        <li><a href="#section-6">Section 6 figures</a></li>
      </ul>
    </nav>
    """

    css = """
    :root {
      --bg: #fafafa;
      --panel: #ffffff;
      --text: #222;
      --muted: #666;
      --accent: #2a5;
      --border: #e1e1e1;
      --code-bg: #f3f3f3;
    }
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      background: var(--bg); color: var(--text);
      margin: 0; padding: 0;
      line-height: 1.55;
    }
    .layout { display: flex; max-width: 1500px; margin: 0 auto; }
    .toc {
      position: sticky; top: 0; align-self: flex-start;
      width: 220px; padding: 1.5rem 1rem; height: 100vh; overflow-y: auto;
      border-right: 1px solid var(--border);
      background: var(--panel); font-size: 0.88rem;
    }
    .toc h3 { margin: 0 0 0.5rem 0; }
    .toc ul { list-style: none; padding: 0; margin: 0; }
    .toc li { margin: 0.25rem 0; }
    .toc li.sep { color: var(--muted); font-size: 0.78rem; margin-top: 0.5rem; }
    .toc a { color: var(--text); text-decoration: none; }
    .toc a:hover { color: var(--accent); }
    main { flex: 1; padding: 2rem 2.5rem; max-width: 1100px; }
    h1, h2, h3, h4 { line-height: 1.25; }
    h1 { font-size: 1.7rem; border-bottom: 2px solid var(--border); padding-bottom: 0.5rem; }
    h2 { font-size: 1.35rem; margin-top: 2rem; padding-top: 0.5rem; border-top: 1px solid var(--border); }
    h3 { font-size: 1.08rem; }
    h3.extra { color: var(--accent); margin-top: 1.5rem; }
    code { background: var(--code-bg); padding: 0.1em 0.35em; border-radius: 3px; font-size: 0.92em; }
    pre { background: var(--code-bg); padding: 0.8rem; overflow-x: auto; border-radius: 4px; }
    pre code { background: none; padding: 0; }
    table.atlas-table, table { border-collapse: collapse; font-size: 0.85rem; margin: 0.7rem 0; }
    table.atlas-table th, table.atlas-table td, table th, table td {
      border: 1px solid var(--border); padding: 4px 9px; text-align: right;
    }
    table.atlas-table th, table th {
      background: #eef; text-align: center; font-weight: 600;
    }
    table.atlas-table td:first-child, table td:first-child {
      text-align: left; font-family: ui-monospace, Menlo, Consolas, monospace;
      font-size: 0.83rem;
    }
    .table-wrap { margin: 1rem 0; overflow-x: auto; }
    .table-wrap.scroll { max-height: 540px; overflow-y: auto; border: 1px solid var(--border); padding: 0.4rem; background: #fcfcfc; }
    .table-wrap h4 { margin: 0.2rem 0 0.4rem 0; color: var(--muted); }
    img.fig {
      max-width: 100%; height: auto; border: 1px solid var(--border);
      background: white; padding: 4px; border-radius: 4px;
      display: block; margin: 0.5rem 0;
    }
    img.fig.wide { max-width: 100%; }
    .grid {
      display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;
      margin: 1rem 0;
    }
    .grid-cell { background: white; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px; }
    .grid-cell .cap, .stack-cell .cap {
      font-family: ui-monospace, Menlo, Consolas, monospace;
      font-size: 0.85rem; color: var(--muted); margin-bottom: 0.3rem;
    }
    .stack { display: flex; flex-direction: column; gap: 1.2rem; margin: 1rem 0; }
    .stack-cell { background: white; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px; }
    .missing { color: #a33; font-style: italic; padding: 0.6rem; background: #fee; border-radius: 4px; }
    .note { color: var(--muted); font-style: italic; font-size: 0.9rem; }
    .section-block { margin-top: 2rem; }
    blockquote { color: var(--muted); border-left: 3px solid var(--accent); margin-left: 0; padding-left: 1rem; }
    hr { border: 0; border-top: 1px solid var(--border); margin: 2rem 0; }
    """

    full = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Breadth Atlas — NSE 500</title>
<style>{css}</style>
</head>
<body>
<div class="layout">
{toc}
<main>
{body_html}
{extras_html}
</main>
</div>
</body>
</html>
"""
    return full


def main():
    html = render_html()
    OUT_HTML.write_text(html)
    size_mb = OUT_HTML.stat().st_size / (1024 * 1024)
    print(f"[write] {OUT_HTML.relative_to(ROOT)}  ({size_mb:.1f} MB)")
    print(f"        open with: open {OUT_HTML}")


if __name__ == "__main__":
    main()
