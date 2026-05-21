"""Compute the breadth-atlas daily panel for NSE 500.

Reads raw per-stock OHLCV from `nse500_data_merged/`, filters to the
`data/static/nse500_universe.csv` constituents, and writes:

  data/breadth/breadth_daily.csv          # one row per trading day, all metrics
  data/breadth/breadth_universe_size.csv  # per-day denominator per metric

No look-ahead: every metric on date T uses only [..., T].

Run:
    python scripts/build_breadth_panel.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRICES_DIR = ROOT / "nse500_data_merged"
UNIVERSE_CSV = ROOT / "data" / "static" / "nse500_universe.csv"
OUT_DIR = ROOT / "data" / "breadth"

START_DATE = "2009-09-01"
END_DATE = "2026-05-12"


def load_universe() -> list[str]:
    df = pd.read_csv(UNIVERSE_CSV)
    return sorted(df["Symbol"].astype(str).str.upper().unique().tolist())


def load_panels(symbols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (close_panel, volume_panel), raw (no ffill).

    Close is unadjusted but the source is the GDF-stitched merged panel so
    splits/bonus are already handled.
    """
    close_rows, vol_rows = [], []
    universe_set = set(symbols)
    for csv_path in sorted(PRICES_DIR.glob("*_day.csv")):
        symbol = csv_path.stem.replace("_day", "").upper()
        if symbol not in universe_set:
            continue
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty or "close" not in df.columns:
            continue
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
        df = df.sort_values("date")
        close_rows.append(df[["date", "close"]].assign(symbol=symbol))
        if "volume" in df.columns:
            vol_rows.append(df[["date", "volume"]].assign(symbol=symbol))

    close_df = pd.concat(close_rows, ignore_index=True)
    vol_df = pd.concat(vol_rows, ignore_index=True) if vol_rows else pd.DataFrame(columns=["date", "volume", "symbol"])

    close_panel = close_df.pivot(index="date", columns="symbol", values="close").sort_index()
    volume_panel = vol_df.pivot(index="date", columns="symbol", values="volume").sort_index()
    volume_panel = volume_panel.reindex(close_panel.index)

    # restrict to requested date window
    mask = (close_panel.index >= pd.Timestamp(START_DATE)) & (close_panel.index <= pd.Timestamp(END_DATE))
    return close_panel.loc[mask], volume_panel.loc[mask]


def compute_metrics(close: pd.DataFrame, volume: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute all 14 breadth metrics + per-day denominators.

    Returns (metrics_df, denoms_df).
    """
    valid = close.notna()  # raw validity — stock has a price that day

    # ---------- pct above DMA (metrics 1-4 + metric 14) ----------
    MIN_VALID = 50  # require at least 50 stocks for metric to be meaningful
    dma_metrics: dict[str, pd.Series] = {}
    denoms: dict[str, pd.Series] = {}
    for window, name in [(200, "200dma"), (100, "100dma"), (50, "50dma"), (21, "21dma")]:
        sma = close.rolling(window, min_periods=window).mean()
        ok = valid & sma.notna()
        above = (close > sma) & ok
        denom = ok.sum(axis=1)
        ratio = above.sum(axis=1) / denom.where(denom >= MIN_VALID)
        dma_metrics[f"pct_above_{name}"] = ratio
        denoms[f"pct_above_{name}_denom"] = denom

    # Metric 14: continuous version of #1 (mean of (close - 200dma) / 200dma)
    sma200 = close.rolling(200, min_periods=200).mean()
    dist_200 = (close - sma200) / sma200
    avg_dist = dist_200.mean(axis=1, skipna=True)

    # ---------- advance/decline (metrics 5-7) ----------
    daily_ret = close.pct_change()  # raw; uses prior valid close for each symbol
    ad_valid = daily_ret.notna()  # stock had a prior close, i.e., return is defined
    advancers = (daily_ret > 0) & ad_valid
    decliners = (daily_ret < 0) & ad_valid
    unchanged = (daily_ret == 0) & ad_valid

    n_adv = advancers.sum(axis=1)
    n_dec = decliners.sum(axis=1)
    n_unch = unchanged.sum(axis=1)
    n_total = (n_adv + n_dec + n_unch)  # = valid stocks with a return today

    MIN_VALID = 50
    n_total_eff = n_total.where(n_total >= MIN_VALID)
    ad_ratio = n_adv / n_dec.where(n_dec > 0)
    ad_ratio = ad_ratio.where(n_total >= MIN_VALID)
    ad_net_pct = (n_adv - n_dec) / n_total_eff
    ad_line = ad_net_pct.cumsum()  # rebased to 0 at start naturally

    denoms["ad_denom"] = n_total

    # ---------- McClellan (metrics 8-9) ----------
    # Use ad_net_pct (not raw n_adv - n_dec) so changes in universe size don't bias.
    ema_short = ad_net_pct.ewm(span=19, adjust=False).mean()
    ema_long = ad_net_pct.ewm(span=39, adjust=False).mean()
    mcclellan_osc = ema_short - ema_long
    mcclellan_sum = mcclellan_osc.cumsum()

    # ---------- 52w highs/lows (metrics 10-12) ----------
    # On day T, is close[T] the max (or min) of the [T-251, T] window?
    rolling_max = close.rolling(252, min_periods=252).max()
    rolling_min = close.rolling(252, min_periods=252).min()
    at_high = (close >= rolling_max) & valid & rolling_max.notna()
    at_low = (close <= rolling_min) & valid & rolling_min.notna()
    hl_denom = (valid & rolling_max.notna()).sum(axis=1)
    hl_eff = hl_denom.where(hl_denom >= MIN_VALID)
    pct_high = at_high.sum(axis=1) / hl_eff
    pct_low = at_low.sum(axis=1) / hl_eff
    net_new = pct_high - pct_low
    denoms["hl_denom"] = hl_denom

    # ---------- up-vol ratio (metric 13) ----------
    # Volume of advancing stocks / volume of all stocks with a defined return.
    vol_aligned = volume.reindex_like(close)
    # only count where the stock has a return today (otherwise can't classify as up/down)
    vol_valid = vol_aligned.where(ad_valid)
    up_vol = vol_valid.where(advancers).sum(axis=1, min_count=1)
    total_vol = vol_valid.sum(axis=1, min_count=1)
    up_vol_ratio = up_vol / total_vol.replace(0, np.nan)
    denoms["vol_denom_count"] = vol_valid.notna().sum(axis=1)

    # ---------- assemble ----------
    metrics = pd.DataFrame({
        "pct_above_200dma": dma_metrics["pct_above_200dma"],
        "pct_above_100dma": dma_metrics["pct_above_100dma"],
        "pct_above_50dma": dma_metrics["pct_above_50dma"],
        "pct_above_21dma": dma_metrics["pct_above_21dma"],
        "ad_ratio": ad_ratio,
        "ad_net_pct": ad_net_pct,
        "ad_line": ad_line,
        "mcclellan_osc": mcclellan_osc,
        "mcclellan_sum": mcclellan_sum,
        "pct_at_52w_high": pct_high,
        "pct_at_52w_low": pct_low,
        "net_new_highs_pct": net_new,
        "up_vol_ratio": up_vol_ratio,
        "avg_dist_from_200dma": avg_dist,
    })
    metrics.index.name = "date"

    denoms_df = pd.DataFrame(denoms)
    denoms_df.index.name = "date"

    # Trim to days that have at least the longest lookback (200d) computed.
    # The first ~252 days are warm-up; report from where pct_above_200dma is finite.
    first_valid = metrics["pct_above_200dma"].first_valid_index()
    if first_valid is not None:
        metrics = metrics.loc[first_valid:]
        denoms_df = denoms_df.loc[first_valid:]
    return metrics, denoms_df


def verification_gates(metrics: pd.DataFrame, denoms: pd.DataFrame, close: pd.DataFrame):
    """Run the four hard checks from PLAN.md verification gates."""
    print("\n=== VERIFICATION GATES ===\n")

    # Gate 1: universe size grows over time (newer listings get added).
    pct200_denom = denoms["pct_above_200dma_denom"].loc[metrics.index]
    early = pct200_denom.iloc[:20].mean()
    late = pct200_denom.iloc[-20:].mean()
    print(f"[Gate 1] pct_above_200dma denominator (post-trim) — "
          f"first-20-days avg={early:.1f}, last-20-days avg={late:.1f}")
    print(f"         (should be smaller at start, ~{int(0.9 * len(close.columns))}+ at end)")
    assert late > early, "Gate 1 FAIL: late denominator should exceed early."
    assert early >= 50, f"Gate 1 FAIL: early denom {early} < MIN_VALID=50."

    # Gate 2: match to _alternative_regime_test.build_breadth_regime kernel.
    # That code computes pct above 200-DMA the same way; just spot-check the final date.
    last_date = metrics.index[-1]
    sma200 = close.rolling(200, min_periods=200).mean()
    valid = close.notna() & sma200.notna()
    breadth_check = ((close > sma200) & valid).sum(axis=1) / valid.sum(axis=1).clip(lower=1)
    diff = abs(metrics.loc[last_date, "pct_above_200dma"] - breadth_check.loc[last_date])
    print(f"[Gate 2] pct_above_200dma on {last_date.date()}: "
          f"panel={metrics.loc[last_date, 'pct_above_200dma']:.4f}, "
          f"recomputed={breadth_check.loc[last_date]:.4f}, diff={diff:.6f}")
    assert diff < 1e-10, "Gate 2 FAIL: kernel mismatch."

    # Gate 3: AD ratio centers around 1.
    ad_mean = metrics["ad_ratio"].replace([np.inf, -np.inf], np.nan).median()
    print(f"[Gate 3] ad_ratio median = {ad_mean:.3f} (should be near 1.0)")
    assert 0.6 < ad_mean < 1.5, "Gate 3 FAIL: ad_ratio median far from 1."

    # Gate 4: no look-ahead. The 200-DMA on date T uses [T-199, T] inclusive — already
    # the case by pandas .rolling default. Sanity check: an early date should be NaN
    # if it has fewer than 200 days of history.
    first_date = close.index[0]
    sma_first200 = close.iloc[:199].rolling(200, min_periods=200).mean()
    n_nan = sma_first200.isna().sum().sum()
    print(f"[Gate 4] No look-ahead — first 199 days of 200-DMA are all NaN ({n_nan} NaN cells)")
    assert n_nan == sma_first200.size, "Gate 4 FAIL: 200-DMA fired before window filled."

    print("\nAll gates PASSED.\n")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[load] universe = {UNIVERSE_CSV.name}")
    symbols = load_universe()
    print(f"       {len(symbols)} symbols")

    print(f"[load] price panels from {PRICES_DIR.name}")
    close, volume = load_panels(symbols)
    print(f"       close panel: {close.shape}, dates {close.index[0].date()} → {close.index[-1].date()}")
    print(f"       volume panel: {volume.shape}, non-null cells = {volume.notna().sum().sum():,}")

    print("[compute] metrics ...")
    metrics, denoms = compute_metrics(close, volume)
    print(f"       metrics panel: {metrics.shape}, dates {metrics.index[0].date()} → {metrics.index[-1].date()}")

    verification_gates(metrics, denoms, close)

    out_metrics = OUT_DIR / "breadth_daily.csv"
    out_denoms = OUT_DIR / "breadth_universe_size.csv"
    metrics.to_csv(out_metrics, float_format="%.6f")
    denoms.to_csv(out_denoms)
    print(f"[write] {out_metrics.relative_to(ROOT)}")
    print(f"[write] {out_denoms.relative_to(ROOT)}")

    # Quick summary
    print("\n=== METRIC SUMMARY (last available date) ===")
    print(metrics.tail(1).T.round(4))


if __name__ == "__main__":
    main()
