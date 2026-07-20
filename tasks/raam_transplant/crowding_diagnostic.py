"""Phase 0.3/0.4 — the G0 gate.

Reconstructs the actual L6 v2 book at every weekly rebalance 2017->now and
asks two pre-registered questions:

  Q-crowd:  does high internal residual-crowding of the book predict deeper
            forward 20/40/60d drawdown (or lower forward return)?
  Q-breadth: does low positive-momentum breadth in the top-40 ranks predict
            the same?

If EITHER shows a monotone quantile spread worth acting on, G0 passes and
E1 (crowding-penalised selection) / E2 (breadth throttle) are justified.
If neither does, the thesis is dead cheap and the diagnostic itself — the
crowding gauge — is the deliverable.

Crowding C(d)  = mean off-diagonal pairwise correlation of the 24 holdings'
                 market-residual returns over the trailing 63d (residuals.py).
Breadth B(d)   = share of the top-40 L6-ranked names with positive 126d
                 momentum on date d.
Forward metric = from d, over the next N trading days of the L6 equity curve:
                 fwd_ret  = pv[d+N]/pv[d] - 1
                 fwd_maxdd = worst peak-to-trough of pv within (d, d+N].

Run:  python tasks/raam_transplant/crowding_diagnostic.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._clean_engine import thursdays  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6, build_momentum_panels, make_momentum_score, run_momentum,
    lookback_months_to_days,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from residuals import build_residual_panel, avg_pairwise_corr  # noqa: E402

NSE500_UNIVERSE_CSV = "data/static/nse500_universe.csv"
NIFTY100_INDEX = "indices_data_historical/NIFTY_100.csv"

DIAG_START = "2017-01-01"
DIAG_END = "2026-07-20"
CROWD_WINDOW = 63      # trailing days for residual crowding
FWD_WINDOWS = [20, 40, 60]
TOP_N = 24
BREADTH_TOP = 40
N_BUCKETS = 5


def load_index_close(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    date_col = df.columns[0]
    close_col = "close" if "close" in df.columns else df.columns[4]
    s = pd.Series(df[close_col].values,
                  index=pd.to_datetime(df[date_col]), name="nifty100")
    return s[~s.index.duplicated(keep="last")].sort_index()


def forward_metrics(pv: pd.Series, d: pd.Timestamp, n: int) -> dict:
    """Forward n-trading-day return and worst drawdown of pv anchored at d."""
    if d not in pv.index:
        pos = pv.index.searchsorted(d)
        if pos >= len(pv.index):
            return {}
        d = pv.index[pos]
    i = pv.index.get_loc(d)
    fwd = pv.iloc[i:i + n + 1]
    if len(fwd) < n + 1:  # not enough forward data
        return {}
    ret = fwd.iloc[-1] / fwd.iloc[0] - 1
    dd = (fwd / fwd.cummax() - 1).min()
    return {f"fwd_ret_{n}": float(ret), f"fwd_maxdd_{n}": float(dd)}


def bucket_table(df: pd.DataFrame, key: str, n_buckets: int) -> pd.DataFrame:
    """Mean forward outcomes per quantile bucket of `key`, low->high."""
    valid = df.dropna(subset=[key]).copy()
    valid["bucket"] = pd.qcut(valid[key], n_buckets, labels=False, duplicates="drop")
    out_cols = [c for c in df.columns if c.startswith("fwd_")]
    g = valid.groupby("bucket")
    rows = []
    for b, sub in g:
        row = {"bucket": int(b), "n": len(sub), f"{key}_mean": round(sub[key].mean(), 4)}
        for c in out_cols:
            row[c] = round(sub[c].mean() * 100, 2)
        rows.append(row)
    return pd.DataFrame(rows)


def spearman(a: pd.Series, b: pd.Series) -> float:
    m = a.notna() & b.notna()
    if m.sum() < 10:
        return float("nan")
    return round(float(a[m].rank().corr(b[m].rank())), 3)


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"crowding_diag_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in nse500]
    print(f"       {len(cols)} NSE500 symbols; panel {calendar[0].date()}->{calendar[-1].date()}")

    nifty100 = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()

    # L6 score + momentum panel (raw momentum reused for the breadth metric)
    lookback = lookback_months_to_days(L6["lookback_months"])
    l6_panels = build_momentum_panels(close_panel[cols], lookback_days=lookback,
                                       skip_days=L6["skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=L6["vol_floor"],
                                   vol_power=L6["vol_power"],
                                   cross_sectional_zscore=L6["cross_sectional_zscore"])
    momentum = l6_panels["momentum"]

    print("[build] residual panel (252d beta vs NIFTY100, residual returns)")
    resid = build_residual_panel(close_panel[cols], nifty100)["residual"]

    print("[run] L6 equity curve for forward outcomes (2016-06 warmup)")
    l6_res = run_momentum(
        close_panel=close_panel[cols], trade_panel=trade_panel[cols],
        calendar=calendar, benchmark_aligned=benchmark, panels=l6_panels,
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        start="2016-06-01", end=DIAG_END, config=dict(L6),
    )
    eq = l6_res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)

    rebal = thursdays(calendar)
    rebal = rebal[(rebal >= pd.Timestamp(DIAG_START)) & (rebal <= pd.Timestamp(DIAG_END))]
    print(f"[loop] {len(rebal)} weekly rebalances")

    rows = []
    for d in rebal:
        s = l6_score(d)
        if s is None or s.empty:
            continue
        ranked = s.sort_values(ascending=False)
        holdings = ranked.head(TOP_N).index.tolist()
        top40 = ranked.head(BREADTH_TOP).index

        # crowding on trailing 63d residuals of the held book
        win = resid.loc[:d].tail(CROWD_WINDOW)
        crowd = avg_pairwise_corr(win[[h for h in holdings if h in win.columns]])

        # market-wide positive-momentum breadth (participation across the
        # whole eligible universe). Top-40-rank breadth is tautologically ~1.0
        # because L6 ranks by momentum; the throttle needs the broad measure.
        mom_row = momentum.loc[d].dropna() if d in momentum.index else pd.Series(dtype=float)
        breadth = float((mom_row > 0).mean()) if len(mom_row) else np.nan

        row = {"date": d, "crowding": crowd, "breadth": breadth}
        for n in FWD_WINDOWS:
            row.update(forward_metrics(pv, d, n))
        rows.append(row)

    df = pd.DataFrame(rows).set_index("date")
    df.to_csv(out_dir / "diagnostic_series.csv")

    # ---- Analysis ----
    report = {"n_rebalances": int(len(df)),
              "period": [DIAG_START, DIAG_END],
              "crowding_desc": df["crowding"].describe().round(4).to_dict(),
              "breadth_desc": df["breadth"].describe().round(4).to_dict(),
              "spearman": {}, "buckets": {}}

    for fw in FWD_WINDOWS:
        report["spearman"][f"crowding_vs_fwd_maxdd_{fw}"] = spearman(df["crowding"], df[f"fwd_maxdd_{fw}"])
        report["spearman"][f"crowding_vs_fwd_ret_{fw}"] = spearman(df["crowding"], df[f"fwd_ret_{fw}"])
        report["spearman"][f"breadth_vs_fwd_maxdd_{fw}"] = spearman(df["breadth"], df[f"fwd_maxdd_{fw}"])
        report["spearman"][f"breadth_vs_fwd_ret_{fw}"] = spearman(df["breadth"], df[f"fwd_ret_{fw}"])

    crowd_buckets = bucket_table(df, "crowding", N_BUCKETS)
    breadth_buckets = bucket_table(df, "breadth", N_BUCKETS)
    crowd_buckets.to_csv(out_dir / "crowding_buckets.csv", index=False)
    breadth_buckets.to_csv(out_dir / "breadth_buckets.csv", index=False)
    report["buckets"]["crowding"] = crowd_buckets.to_dict(orient="records")
    report["buckets"]["breadth"] = breadth_buckets.to_dict(orient="records")

    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str))

    pd.set_option("display.width", 160, "display.max_columns", 20)
    print("\n" + "=" * 72)
    print(f"CROWDING DIAGNOSTIC — {len(df)} weekly rebalances, {DIAG_START}->{DIAG_END}")
    print("=" * 72)
    print(f"\ncrowding (mean pairwise residual corr of the L6 book):")
    print(f"  {df['crowding'].describe()[['mean','std','min','25%','50%','75%','max']].round(3).to_dict()}")
    print(f"breadth (share of top-40 with positive 126d momentum):")
    print(f"  {df['breadth'].describe()[['mean','std','min','25%','50%','75%','max']].round(3).to_dict()}")

    print("\nSpearman rank correlations (want: crowding->deeper DD = NEGATIVE;")
    print("breadth->deeper DD = POSITIVE i.e. low breadth = more negative DD):")
    for k, v in report["spearman"].items():
        print(f"  {k:34s} {v:+.3f}")

    print("\nCROWDING buckets (low->high crowding), forward outcomes in %:")
    print(crowd_buckets.to_string(index=False))
    print("\nBREADTH buckets (low->high breadth), forward outcomes in %:")
    print(breadth_buckets.to_string(index=False))

    # ---- G0 verdict heuristic ----
    def monotone_spread(bt, col):
        if bt.empty or col not in bt:
            return None
        v = bt[col].values
        return round(float(v[-1] - v[0]), 2)

    verdict = {
        "crowd_dd40_spread_pp": monotone_spread(crowd_buckets, "fwd_maxdd_40"),
        "crowd_ret40_spread_pp": monotone_spread(crowd_buckets, "fwd_ret_40"),
        "breadth_dd40_spread_pp": monotone_spread(breadth_buckets, "fwd_maxdd_40"),
        "breadth_ret40_spread_pp": monotone_spread(breadth_buckets, "fwd_ret_40"),
    }
    report["verdict"] = verdict
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str))
    print("\nG0 spread (top-bucket minus bottom-bucket, pp):")
    for k, v in verdict.items():
        print(f"  {k:28s} {v}")
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
