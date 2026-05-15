"""Breadth Atlas — generate report figures and tables.

Reads `data/breadth/breadth_daily.csv` (built by `build_breadth_panel.py`)
and produces:

  tasks/breadth_atlas/figures/
    distributions/<metric>.png         # Section 1
    dwell_time/heatmap.png             # Section 2
    dwell_time/run_length_cdf.png      # Section 2
    extremes/*.png                     # Section 3
    index_relationship/<metric>.png    # Section 5
    correlation/{pearson,spearman}.png # Section 6

  tasks/breadth_atlas/
    section1_distribution_stats.csv
    section1_yearly_means.csv
    section2_dwell_times.csv
    section3_extremes.csv
    section4_mean_reversion.csv
    section6_correlations.csv
    section6_pca.csv

Run:
    python scripts/breadth_atlas_report.py [--section <1|2|3|4|5|6|all>]
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PANEL_CSV = ROOT / "data" / "breadth" / "breadth_daily.csv"
OUT_DIR = ROOT / "tasks" / "breadth_atlas"
FIG_DIR = OUT_DIR / "figures"

METRIC_NAMES = [
    "pct_above_200dma", "pct_above_100dma", "pct_above_50dma", "pct_above_21dma",
    "ad_ratio", "ad_net_pct", "ad_line",
    "mcclellan_osc", "mcclellan_sum",
    "pct_at_52w_high", "pct_at_52w_low", "net_new_highs_pct",
    "up_vol_ratio", "avg_dist_from_200dma",
]

PCT_METRICS = {"pct_above_200dma", "pct_above_100dma", "pct_above_50dma", "pct_above_21dma",
               "pct_at_52w_high", "pct_at_52w_low", "up_vol_ratio"}
OSCILLATOR_METRICS = {"mcclellan_osc", "avg_dist_from_200dma", "ad_net_pct", "net_new_highs_pct"}


def load_panel() -> pd.DataFrame:
    df = pd.read_csv(PANEL_CSV, parse_dates=["date"]).set_index("date").sort_index()
    return df


# ============================================================
# Section 1 — Distribution profile
# ============================================================

def section1_distributions(df: pd.DataFrame):
    print("\n=== SECTION 1: Distribution profile ===")
    rows = []
    for m in METRIC_NAMES:
        s = df[m].replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            continue
        rows.append({
            "metric": m,
            "n": len(s),
            "min": s.min(),
            "max": s.max(),
            "mean": s.mean(),
            "median": s.median(),
            "std": s.std(),
            "skew": s.skew(),
            "kurtosis": s.kurtosis(),
            "p01": s.quantile(0.01),
            "p05": s.quantile(0.05),
            "p10": s.quantile(0.10),
            "p25": s.quantile(0.25),
            "p75": s.quantile(0.75),
            "p90": s.quantile(0.90),
            "p95": s.quantile(0.95),
            "p99": s.quantile(0.99),
        })
    stats = pd.DataFrame(rows).set_index("metric")
    out = OUT_DIR / "section1_distribution_stats.csv"
    stats.to_csv(out, float_format="%.6f")
    print(f"  wrote {out.relative_to(ROOT)}")
    print(stats[["min", "p05", "median", "p95", "max", "std"]].round(3))

    # Per-year means table
    df_yr = df.copy()
    df_yr["year"] = df_yr.index.year
    yearly = df_yr.groupby("year")[METRIC_NAMES].mean()
    yearly.to_csv(OUT_DIR / "section1_yearly_means.csv", float_format="%.6f")
    print(f"  wrote section1_yearly_means.csv ({len(yearly)} years × {len(METRIC_NAMES)} metrics)")

    # Histograms
    dist_dir = FIG_DIR / "distributions"
    dist_dir.mkdir(parents=True, exist_ok=True)
    for m in METRIC_NAMES:
        s = df[m].replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            continue
        fig, ax = plt.subplots(figsize=(7, 4))
        # clip ad_ratio for plotting to avoid extreme tails
        s_plot = s.clip(s.quantile(0.001), s.quantile(0.999)) if m == "ad_ratio" else s
        ax.hist(s_plot, bins=60, color="#4a7ab8", alpha=0.85, edgecolor="white")
        ax.axvline(s.median(), color="red", linestyle="--", alpha=0.7, label=f"median={s.median():.3f}")
        ax.axvline(s.quantile(0.05), color="orange", linestyle=":", alpha=0.7, label=f"p5={s.quantile(0.05):.3f}")
        ax.axvline(s.quantile(0.95), color="orange", linestyle=":", alpha=0.7, label=f"p95={s.quantile(0.95):.3f}")
        ax.set_title(f"{m}  (n={len(s):,})")
        ax.set_xlabel(m); ax.set_ylabel("days")
        ax.legend(loc="best", fontsize=8)
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(dist_dir / f"{m}.png", dpi=110)
        plt.close(fig)
    print(f"  wrote {len(METRIC_NAMES)} histograms → figures/distributions/")


# ============================================================
# Section 2 — Dwell-time analysis
# ============================================================

def bucketize(s: pd.Series, metric: str) -> pd.Series:
    if metric in PCT_METRICS:
        bins = [-0.0001, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0001]
        labels = ["0-10", "10-20", "20-30", "30-40", "40-50",
                  "50-60", "60-70", "70-80", "80-90", "90-100"]
        return pd.cut(s, bins=bins, labels=labels)
    # oscillator: z-score then sigma buckets
    z = (s - s.mean()) / s.std()
    bins = [-np.inf, -2, -1, 0, 1, 2, np.inf]
    labels = ["<-2σ", "-2 to -1σ", "-1 to 0σ", "0 to 1σ", "1 to 2σ", ">2σ"]
    return pd.cut(z, bins=bins, labels=labels)


def run_lengths(s: pd.Series) -> list[int]:
    """Consecutive run lengths of identical values in a Series."""
    lengths: list[int] = []
    if s.empty:
        return lengths
    prev, count = None, 0
    for v in s.values:
        if v == prev:
            count += 1
        else:
            if count > 0:
                lengths.append(count)
            prev = v
            count = 1
    if count > 0:
        lengths.append(count)
    return lengths


def section2_dwell_times(df: pd.DataFrame):
    print("\n=== SECTION 2: Dwell-time analysis ===")
    rows = []
    heatmap_data = {}
    for m in METRIC_NAMES:
        s = df[m].replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            continue
        buckets = bucketize(s, m)
        # steady-state probability
        share = buckets.value_counts(normalize=True, sort=False)
        # average run length per bucket
        # group consecutive runs
        runs: dict[str, list[int]] = {}
        prev = None; count = 0
        for v in buckets.values:
            v = str(v)
            if v == prev:
                count += 1
            else:
                if prev is not None and count > 0:
                    runs.setdefault(prev, []).append(count)
                prev = v; count = 1
        if prev is not None and count > 0:
            runs.setdefault(prev, []).append(count)

        years = (s.index[-1] - s.index[0]).days / 365.25
        for bucket in share.index:
            bucket_str = str(bucket)
            run_list = runs.get(bucket_str, [])
            avg_run = float(np.mean(run_list)) if run_list else 0.0
            max_run = max(run_list) if run_list else 0
            visits_per_year = len(run_list) / years if years > 0 else 0
            rows.append({
                "metric": m,
                "bucket": bucket_str,
                "pct_days": float(share[bucket]) * 100,
                "avg_run_length": avg_run,
                "max_run_length": max_run,
                "visits_per_year": visits_per_year,
            })
        heatmap_data[m] = share.reindex(buckets.cat.categories).fillna(0.0).values

    dwell = pd.DataFrame(rows)
    dwell.to_csv(OUT_DIR / "section2_dwell_times.csv", index=False, float_format="%.4f")
    print(f"  wrote section2_dwell_times.csv ({len(dwell)} rows)")

    # Heatmap (pct days per bucket per metric)
    dwell_dir = FIG_DIR / "dwell_time"
    dwell_dir.mkdir(parents=True, exist_ok=True)

    # Build a structured matrix: only metrics whose bucketing is comparable across rows.
    # We'll do two heatmaps: pct-metric heatmap and oscillator heatmap.
    pct_labels = ["0-10", "10-20", "20-30", "30-40", "40-50",
                  "50-60", "60-70", "70-80", "80-90", "90-100"]
    pct_rows = [m for m in METRIC_NAMES if m in PCT_METRICS]
    pct_mat = np.zeros((len(pct_rows), len(pct_labels)))
    for i, m in enumerate(pct_rows):
        sub = dwell[dwell["metric"] == m].set_index("bucket")["pct_days"]
        for j, lab in enumerate(pct_labels):
            pct_mat[i, j] = sub.get(lab, 0.0)

    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(pct_mat, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(pct_labels))); ax.set_xticklabels(pct_labels, rotation=45)
    ax.set_yticks(range(len(pct_rows))); ax.set_yticklabels(pct_rows)
    ax.set_title("Dwell time (% days) — percentage metrics")
    for i in range(len(pct_rows)):
        for j in range(len(pct_labels)):
            ax.text(j, i, f"{pct_mat[i,j]:.0f}", ha="center", va="center",
                    color="white" if pct_mat[i,j] < 20 else "black", fontsize=8)
    plt.colorbar(im, ax=ax, label="% days")
    fig.tight_layout()
    fig.savefig(dwell_dir / "heatmap_pct.png", dpi=110)
    plt.close(fig)

    # Oscillator heatmap
    osc_labels = ["<-2σ", "-2 to -1σ", "-1 to 0σ", "0 to 1σ", "1 to 2σ", ">2σ"]
    osc_rows = [m for m in METRIC_NAMES if m in OSCILLATOR_METRICS]
    osc_mat = np.zeros((len(osc_rows), len(osc_labels)))
    for i, m in enumerate(osc_rows):
        sub = dwell[dwell["metric"] == m].set_index("bucket")["pct_days"]
        for j, lab in enumerate(osc_labels):
            osc_mat[i, j] = sub.get(lab, 0.0)

    fig, ax = plt.subplots(figsize=(8, 3))
    im = ax.imshow(osc_mat, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(osc_labels))); ax.set_xticklabels(osc_labels)
    ax.set_yticks(range(len(osc_rows))); ax.set_yticklabels(osc_rows)
    ax.set_title("Dwell time (% days) — oscillators (z-score buckets)")
    for i in range(len(osc_rows)):
        for j in range(len(osc_labels)):
            ax.text(j, i, f"{osc_mat[i,j]:.0f}", ha="center", va="center",
                    color="white" if osc_mat[i,j] < 20 else "black", fontsize=9)
    plt.colorbar(im, ax=ax, label="% days")
    fig.tight_layout()
    fig.savefig(dwell_dir / "heatmap_osc.png", dpi=110)
    plt.close(fig)

    # Run-length CDF for the key percentage metric
    fig, ax = plt.subplots(figsize=(8, 4))
    for m in ["pct_above_200dma", "pct_above_100dma", "pct_above_50dma"]:
        s = df[m].dropna()
        b = bucketize(s, m)
        # combine low buckets (<= 20) as "deep bear" and find consecutive deep-bear stretches
        deep = b.isin(["0-10", "10-20"])
        lengths = run_lengths(deep)
        deep_lengths = [l for v, l in zip(
            [bool(x) for x in pd.Series(deep.values).groupby(
                (deep.values != np.roll(deep.values, 1)).cumsum()).first()],
            lengths) if v]
        if not deep_lengths:
            continue
        sorted_lens = np.sort(deep_lengths)
        cdf = np.arange(1, len(sorted_lens) + 1) / len(sorted_lens)
        ax.plot(sorted_lens, cdf, label=f"{m} (n={len(deep_lengths)})", marker="o", markersize=3, alpha=0.8)
    ax.set_xscale("log")
    ax.set_xlabel("Consecutive trading days in deep-breadth (<20%) stretch")
    ax.set_ylabel("CDF")
    ax.set_title("Deep-breadth dwell-time CDF — how long do oversold breadth episodes last?")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(dwell_dir / "run_length_cdf.png", dpi=110)
    plt.close(fig)
    print(f"  wrote dwell-time figures → figures/dwell_time/")


# ============================================================
# Section 3 — Extreme-event catalog
# ============================================================

def load_indices() -> dict:
    out = {}
    nifty100 = pd.read_csv(ROOT / "indices_data_historical" / "NIFTY_100.csv", parse_dates=["date"])
    nifty100["date"] = pd.to_datetime(nifty100["date"]).dt.tz_localize(None).dt.normalize()
    out["nifty100"] = nifty100.set_index("date")["close"].astype(float).sort_index()
    try:
        nifty500 = pd.read_csv(ROOT / "indices_data_historical" / "NIFTY_500.csv", parse_dates=["date"])
        nifty500["date"] = pd.to_datetime(nifty500["date"]).dt.tz_localize(None).dt.normalize()
        out["nifty500"] = nifty500.set_index("date")["close"].astype(float).sort_index()
    except FileNotFoundError:
        out["nifty500"] = None
    return out


def section3_extremes(df: pd.DataFrame):
    print("\n=== SECTION 3: Extreme-event catalog ===")
    indices = load_indices()
    n100 = indices["nifty100"]
    n500 = indices["nifty500"]
    n100_peak = n100.cummax()

    rows = []
    for m in METRIC_NAMES:
        s = df[m].replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            continue
        p05, p95 = s.quantile(0.05), s.quantile(0.95)
        # Two event types: low extremes (below p5) and high extremes (above p95)
        for which, tail in [("low", s < p05), ("high", s > p95)]:
            # Identify contiguous runs of True
            in_event = False
            ev_start = None
            for d, v in tail.items():
                if v and not in_event:
                    in_event = True
                    ev_start = d
                elif not v and in_event:
                    in_event = False
                    ev_end = d  # first day not in extreme
                    rows.append(make_event_row(m, which, ev_start, ev_end, s, n100, n500, n100_peak))
            if in_event:
                rows.append(make_event_row(m, which, ev_start, tail.index[-1], s, n100, n500, n100_peak))

    events = pd.DataFrame(rows)
    if not events.empty:
        events = events.sort_values(["metric", "which", "entry_date"]).reset_index(drop=True)
    events.to_csv(OUT_DIR / "section3_extremes.csv", index=False, float_format="%.4f")
    print(f"  wrote section3_extremes.csv ({len(events)} events across {events['metric'].nunique() if not events.empty else 0} metrics)")

    # Headline: longest events
    if not events.empty:
        longest = events.nlargest(15, "duration_days")[
            ["metric", "which", "entry_date", "exit_date", "duration_days",
             "n100_dd_during_pct", "n100_gain_during_pct"]
        ]
        print("\n  Top 15 longest extreme events:")
        print(longest.to_string(index=False))


def make_event_row(metric, which, entry_d, exit_d, s, n100, n500, n100_peak):
    entry_idx = pd.Timestamp(entry_d)
    exit_idx = pd.Timestamp(exit_d)
    duration = (exit_idx - entry_idx).days
    span = slice(entry_idx, exit_idx)
    n100_entry = n100.asof(entry_idx)
    n100_exit = n100.asof(exit_idx)
    n100_in = n100.loc[span] if not n100.loc[span].empty else pd.Series([n100_entry])
    n100_min = n100_in.min(); n100_max = n100_in.max()
    if n500 is not None:
        n500_entry = n500.asof(entry_idx)
        n500_exit = n500.asof(exit_idx)
    else:
        n500_entry = n500_exit = np.nan
    peak_at_entry = n100_peak.asof(entry_idx)
    dd_during = (n100_min / peak_at_entry - 1) * 100 if peak_at_entry and peak_at_entry > 0 else np.nan
    gain_during = (n100_max / n100_entry - 1) * 100 if n100_entry and n100_entry > 0 else np.nan
    return {
        "metric": metric,
        "which": which,
        "entry_date": entry_idx.date(),
        "exit_date": exit_idx.date(),
        "duration_days": duration,
        "value_at_entry": float(s.asof(entry_idx)),
        "value_at_exit": float(s.asof(exit_idx)) if not pd.isna(s.asof(exit_idx)) else np.nan,
        "n100_entry": float(n100_entry) if not pd.isna(n100_entry) else np.nan,
        "n100_exit": float(n100_exit) if not pd.isna(n100_exit) else np.nan,
        "n100_dd_during_pct": float(dd_during) if not pd.isna(dd_during) else np.nan,
        "n100_gain_during_pct": float(gain_during) if not pd.isna(gain_during) else np.nan,
        "n500_entry": float(n500_entry) if not pd.isna(n500_entry) else np.nan,
        "n500_exit": float(n500_exit) if not pd.isna(n500_exit) else np.nan,
    }


# ============================================================
# Section 4 — Mean-reversion characterization
# ============================================================

def hurst_exponent(s: pd.Series) -> float:
    """Rescaled-range Hurst exponent. Returns ~0.5 for random walk."""
    s = s.dropna().values
    if len(s) < 100:
        return np.nan
    lags = np.unique(np.round(np.logspace(1, np.log10(len(s) // 4), 12)).astype(int))
    rs_means = []
    for lag in lags:
        # split into chunks of size lag and compute R/S per chunk
        n_chunks = len(s) // lag
        rs_values = []
        for i in range(n_chunks):
            chunk = s[i*lag:(i+1)*lag]
            if len(chunk) < 4 or chunk.std() == 0:
                continue
            mean_chunk = chunk.mean()
            cumdev = (chunk - mean_chunk).cumsum()
            rng = cumdev.max() - cumdev.min()
            sd = chunk.std()
            if sd > 0:
                rs_values.append(rng / sd)
        if rs_values:
            rs_means.append(np.mean(rs_values))
        else:
            rs_means.append(np.nan)
    rs_means = np.array(rs_means)
    valid = ~np.isnan(rs_means) & (rs_means > 0)
    if valid.sum() < 4:
        return np.nan
    slope, _ = np.polyfit(np.log(lags[valid]), np.log(rs_means[valid]), 1)
    return float(slope)


def section4_mean_reversion(df: pd.DataFrame):
    print("\n=== SECTION 4: Mean-reversion characterization ===")
    rows = []
    for m in METRIC_NAMES:
        s = df[m].replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty or len(s) < 100:
            continue
        # AR(1)
        x_lag = s.shift(1).dropna()
        x_now = s.loc[x_lag.index]
        # demean
        x_lag_d = x_lag - x_lag.mean()
        x_now_d = x_now - x_now.mean()
        ar1 = float((x_lag_d * x_now_d).sum() / (x_lag_d ** 2).sum())
        # half-life (in trading days) — log(0.5) / log(|ar1|), guarded
        half_life = float(np.log(0.5) / np.log(abs(ar1))) if 0 < abs(ar1) < 1 else np.nan

        # Zero-crossing (only meaningful for oscillators)
        if m in OSCILLATOR_METRICS:
            centered = s - s.mean()
            sign = np.sign(centered)
            crossings = (sign.diff().abs() > 0).sum()
            cross_per_year = crossings / ((s.index[-1] - s.index[0]).days / 365.25)
        else:
            cross_per_year = np.nan

        hurst = hurst_exponent(s)

        rows.append({
            "metric": m,
            "ar1": ar1,
            "half_life_days": half_life,
            "hurst": hurst,
            "interpretation": (
                "mean-reverting" if not pd.isna(hurst) and hurst < 0.45 else
                "persistent/trending" if not pd.isna(hurst) and hurst > 0.65 else
                "random-walk-ish" if not pd.isna(hurst) else ""
            ),
            "zero_crossings_per_year": cross_per_year,
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / "section4_mean_reversion.csv", index=False, float_format="%.4f")
    print(f"  wrote section4_mean_reversion.csv")
    print(out[["metric", "ar1", "half_life_days", "hurst", "interpretation"]].round(3).to_string(index=False))


# ============================================================
# Section 5 — Index relationship
# ============================================================

def section5_index_relationship(df: pd.DataFrame):
    print("\n=== SECTION 5: Index relationship ===")
    indices = load_indices()
    n100 = indices["nifty100"]
    n500 = indices["nifty500"]

    idx_dir = FIG_DIR / "index_relationship"
    idx_dir.mkdir(parents=True, exist_ok=True)

    # Drawdown-from-peak for Nifty 100
    n100_dd = (n100 / n100.cummax() - 1) * 100  # negative in drawdown

    cond_rows = []
    for m in METRIC_NAMES:
        s = df[m].replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            continue

        # ---- panel of 4 charts ----
        fig, axes = plt.subplots(2, 2, figsize=(14, 9))

        # Chart 1: time-series overlay vs Nifty 100
        ax = axes[0, 0]
        ax.plot(s.index, s.values, color="#3a7", linewidth=0.8, label=m)
        ax.set_ylabel(m, color="#3a7")
        ax2 = ax.twinx()
        n100_aligned = n100.reindex(s.index).ffill()
        ax2.plot(n100_aligned.index, n100_aligned.values, color="black", linewidth=0.8, alpha=0.5, label="NIFTY 100")
        ax2.set_ylabel("NIFTY 100")
        ax.set_title(f"{m} vs NIFTY 100 (time-series overlay)")
        ax.grid(alpha=0.2)

        # Chart 2: scatter metric vs concurrent index level
        ax = axes[0, 1]
        align = pd.concat([s.rename("metric"), n100_aligned.rename("index")], axis=1).dropna()
        ax.scatter(align["metric"], align["index"], s=3, alpha=0.3, color="#26a")
        ax.set_xlabel(m); ax.set_ylabel("NIFTY 100 level")
        ax.set_title(f"{m} vs concurrent NIFTY 100 level")
        ax.grid(alpha=0.2)

        # Chart 3: scatter metric vs concurrent drawdown
        ax = axes[1, 0]
        dd_aligned = n100_dd.reindex(s.index).ffill()
        align2 = pd.concat([s.rename("metric"), dd_aligned.rename("dd")], axis=1).dropna()
        ax.scatter(align2["metric"], align2["dd"], s=3, alpha=0.3, color="#a26")
        ax.set_xlabel(m); ax.set_ylabel("NIFTY 100 drawdown-from-peak (%)")
        ax.set_title(f"{m} vs concurrent N100 drawdown")
        ax.grid(alpha=0.2)

        # Chart 4: conditional table — bucket metric, show concurrent stats
        ax = axes[1, 1]
        buckets = bucketize(s, m)
        joined = pd.concat([
            buckets.rename("bucket"),
            dd_aligned.rename("dd"),
            n100_aligned.pct_change(21).rename("ret21")
        ], axis=1).dropna()
        grouped = joined.groupby("bucket", observed=False).agg(
            n=("dd", "size"),
            mean_dd=("dd", "mean"),
            mean_21d_ret=("ret21", "mean"),
        )
        grouped["mean_21d_ret_pct"] = grouped["mean_21d_ret"] * 100
        # bar chart of mean_dd by bucket
        x = range(len(grouped))
        ax.bar(x, grouped["mean_dd"].values, color="#a52", alpha=0.85)
        ax.set_xticks(x); ax.set_xticklabels(grouped.index, rotation=45)
        ax.set_ylabel("mean concurrent DD-from-peak (%)")
        ax.set_title(f"{m} bucket → concurrent N100 DD")
        ax.grid(axis="y", alpha=0.2)

        for bucket, row in grouped.iterrows():
            cond_rows.append({
                "metric": m,
                "bucket": str(bucket),
                "n_days": int(row["n"]),
                "mean_n100_dd_pct": float(row["mean_dd"]),
                "mean_n100_21d_ret_pct": float(row["mean_21d_ret_pct"]),
            })

        fig.suptitle(f"Section 5 — {m}", fontsize=12)
        fig.tight_layout()
        fig.savefig(idx_dir / f"{m}.png", dpi=110)
        plt.close(fig)

    cond_df = pd.DataFrame(cond_rows)
    cond_df.to_csv(OUT_DIR / "section5_conditional.csv", index=False, float_format="%.4f")
    print(f"  wrote {len([m for m in METRIC_NAMES if df[m].notna().any()])} relationship plots → figures/index_relationship/")
    print(f"  wrote section5_conditional.csv ({len(cond_df)} bucket rows)")


# ============================================================
# Section 6 — Correlation matrix + PCA
# ============================================================

def section6_correlation(df: pd.DataFrame):
    print("\n=== SECTION 6: Cross-metric correlation + PCA ===")
    panel = df[METRIC_NAMES].replace([np.inf, -np.inf], np.nan).dropna(how="any")
    pearson = panel.corr(method="pearson")
    spearman = panel.corr(method="spearman")
    pearson.to_csv(OUT_DIR / "section6_pearson.csv", float_format="%.4f")
    spearman.to_csv(OUT_DIR / "section6_spearman.csv", float_format="%.4f")
    print(f"  wrote section6_pearson.csv + section6_spearman.csv")

    corr_dir = FIG_DIR / "correlation"
    corr_dir.mkdir(parents=True, exist_ok=True)
    for name, mat in [("pearson", pearson), ("spearman", spearman)]:
        fig, ax = plt.subplots(figsize=(8.5, 7.5))
        im = ax.imshow(mat.values, vmin=-1, vmax=1, cmap="RdBu_r")
        ax.set_xticks(range(len(mat.columns))); ax.set_xticklabels(mat.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(mat.index))); ax.set_yticklabels(mat.index)
        for i in range(len(mat.index)):
            for j in range(len(mat.columns)):
                ax.text(j, i, f"{mat.values[i,j]:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if abs(mat.values[i,j]) > 0.5 else "black")
        plt.colorbar(im, ax=ax, label=f"{name} ρ")
        ax.set_title(f"Cross-metric correlation ({name})")
        fig.tight_layout()
        fig.savefig(corr_dir / f"{name}.png", dpi=110)
        plt.close(fig)
    print(f"  wrote correlation heatmaps → figures/correlation/")

    # PCA — numpy/SVD implementation (no sklearn dependency)
    X = panel.values.astype(float)
    X_centered = X - X.mean(axis=0)
    X_scaled = X_centered / X_centered.std(axis=0, ddof=1)
    # SVD: U S V^T = X_scaled, columns of V are eigenvectors of cov
    U, S, Vt = np.linalg.svd(X_scaled, full_matrices=False)
    eigenvalues = (S ** 2) / (X_scaled.shape[0] - 1)
    explained = eigenvalues / eigenvalues.sum()
    cum = np.cumsum(explained)
    components = Vt  # rows are components
    loadings = pd.DataFrame(
        components.T,
        index=panel.columns,
        columns=[f"PC{i+1}" for i in range(len(explained))]
    )
    summary = pd.DataFrame({
        "component": [f"PC{i+1}" for i in range(len(explained))],
        "explained_var_pct": (explained * 100).round(2),
        "cumulative_pct": (cum * 100).round(2),
    })
    summary.to_csv(OUT_DIR / "section6_pca_variance.csv", index=False)
    loadings.to_csv(OUT_DIR / "section6_pca_loadings.csv", float_format="%.4f")
    n_for_90 = int((cum >= 0.90).argmax()) + 1
    print(f"  PCA: {n_for_90} components explain ≥90% of variance")
    print(summary.head(8).to_string(index=False))
    print("\n  Top loadings on PC1 (general-breadth axis):")
    pc1 = loadings["PC1"].abs().sort_values(ascending=False).head(5)
    for metric in pc1.index:
        print(f"    {metric:25s}  loading = {loadings.loc[metric, 'PC1']:+.3f}")
    print("\n  Top loadings on PC2 (orthogonal axis):")
    pc2 = loadings["PC2"].abs().sort_values(ascending=False).head(5)
    for metric in pc2.index:
        print(f"    {metric:25s}  loading = {loadings.loc[metric, 'PC2']:+.3f}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", choices=["1", "2", "3", "4", "5", "6", "all"], default="all")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    df = load_panel()
    print(f"[load] {PANEL_CSV.relative_to(ROOT)} — {df.shape[0]} dates × {df.shape[1]} metrics")
    print(f"       dates {df.index[0].date()} → {df.index[-1].date()}")

    if args.section in ("1", "all"):
        section1_distributions(df)
    if args.section in ("2", "all"):
        section2_dwell_times(df)
    if args.section in ("3", "all"):
        section3_extremes(df)
    if args.section in ("4", "all"):
        section4_mean_reversion(df)
    if args.section in ("5", "all"):
        section5_index_relationship(df)
    if args.section in ("6", "all"):
        section6_correlation(df)

    print("\nDONE.")


if __name__ == "__main__":
    main()
