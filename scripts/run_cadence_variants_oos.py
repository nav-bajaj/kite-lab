"""Run OM25 + TL25 across cadence variants on the GDF-stitched panel.

Each strategy in two entry cadences with weekly exits:
  - monthly entry  + weekly exits
  - biweekly entry + weekly exits

For OM25, weekly exits are driven by a shared weekly Omega rank file
(--hold-signals) — drop holdings whose weekly rank > top_n + exit_buffer.
For TL25, weekly exits are the built-in 200 DMA + ATR triggers.

Outputs:
  experiments/oos_walkthrough/cadence_<ts>/
    <strategy>_<entry>/  -- per-variant equity, trades, summary
    comparison.csv       -- cross-variant headline metrics
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
PRICES_DIR = "nse500_data_merged"
UNIVERSE = "data/static/nse500_universe.csv"
BENCHMARK = "data/benchmarks/nifty100.csv"
INITIAL_CAPITAL = 1_000_000


def run(cmd: list) -> None:
    print(f"\n>>> {' '.join(str(a) for a in cmd)}")
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"failed: {cmd}")


def period_metrics(equity: pd.DataFrame, label: str, boundary: pd.Timestamp,
                   period: str) -> dict:
    if period == "OOS":
        eq = equity[equity["date"] < boundary]
    elif period == "IS":
        eq = equity[equity["date"] >= boundary]
    else:
        eq = equity
    if eq.empty:
        return {"variant": label, "period": period}
    pv = eq.set_index("date")["portfolio_value"].astype(float)
    rets = pv.pct_change().dropna()
    if rets.empty or pv.iloc[0] <= 0:
        return {"variant": label, "period": period}
    days = (pv.index[-1] - pv.index[0]).days
    years = max(days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (rets.mean() * 252) / vol if vol > 0 else float("nan")
    cum = pv / pv.cummax()
    return {
        "variant": label, "period": period,
        "start": pv.index[0].date(), "end": pv.index[-1].date(),
        "years": round(years, 2),
        "cagr_pct": round(cagr * 100, 2),
        "vol_pct": round(vol * 100, 2),
        "sharpe": round(sharpe, 2),
        "max_dd_pct": round((cum.min() - 1) * 100, 2),
        "end_value": round(pv.iloc[-1], 2),
    }


def build_om25_signals(out_dir: Path, freq: str) -> Path:
    sig = out_dir / f"om25_signals_{freq}.csv"
    audit = out_dir / f"om25_audit_{freq}.csv"
    if sig.exists():
        print(f"[skip] {sig.name} already built")
        return sig
    run([PYTHON, "scripts/build_om25_signals.py",
         "--prices-dir", PRICES_DIR, "--universe", UNIVERSE,
         "--output", str(sig), "--audit-output", str(audit),
         "--top-n", "100", "--rebalance-freq", freq])
    return sig


def build_tl25_signals(out_dir: Path, freq: str) -> Path:
    sig = out_dir / f"tl25_signals_{freq}.csv"
    audit = out_dir / f"tl25_audit_{freq}.csv"
    if sig.exists():
        print(f"[skip] {sig.name} already built")
        return sig
    run([PYTHON, "scripts/build_trend_leaders_signals.py",
         "--prices-dir", PRICES_DIR, "--universe", UNIVERSE,
         "--output", str(sig), "--audit-output", str(audit),
         "--top-n", "25", "--rebalance-freq", freq])
    return sig


def run_om25(entry_freq: str, base: Path) -> Path:
    """Run OM25 with given entry cadence + weekly exit hook."""
    sig_dir = base / "_signals"
    sig_dir.mkdir(parents=True, exist_ok=True)
    weekly_sig = build_om25_signals(sig_dir, "weekly")
    entry_sig = build_om25_signals(sig_dir, entry_freq)

    out = base / f"om25_{entry_freq}_entry_weekly_exit"
    out.mkdir(parents=True, exist_ok=True)
    run([PYTHON, "scripts/backtest_om25.py",
         "--prices-dir", PRICES_DIR, "--signals", str(entry_sig),
         "--benchmark", BENCHMARK, "--output-dir", str(out),
         "--top-n", "25", "--initial-capital", str(INITIAL_CAPITAL),
         "--hold-signals", str(weekly_sig), "--exit-buffer", "25"])
    return out / "om25_equity.csv"


def run_tl25(entry_freq: str, base: Path) -> Path:
    """Run TL25 with given entry cadence (weekly exits already built-in)."""
    sig_dir = base / "_signals"
    sig_dir.mkdir(parents=True, exist_ok=True)
    sig = build_tl25_signals(sig_dir, entry_freq)

    out = base / f"tl25_{entry_freq}_entry_weekly_exit"
    out.mkdir(parents=True, exist_ok=True)
    run([PYTHON, "scripts/backtest_trend_leaders.py",
         "--prices-dir", PRICES_DIR, "--signals", str(sig),
         "--benchmark", BENCHMARK, "--output-dir", str(out),
         "--top-n", "25", "--initial-capital", str(INITIAL_CAPITAL),
         "--variant", "base", "--atr-mult", "5.0", "--atr-min-floor", "0.0"])
    return out / "tl20_equity.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--is-start", default="2020-07-10")
    ap.add_argument("--strategies", nargs="+",
                    choices=["om25", "tl25"], default=["om25", "tl25"])
    args = ap.parse_args()

    is_boundary = pd.Timestamp(args.is_start)
    ts = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    base = ROOT / f"experiments/oos_walkthrough/cadence_{ts}"
    base.mkdir(parents=True, exist_ok=True)
    print(f"\n[base] {base}\n")

    variants = []
    for s in args.strategies:
        for freq in ("monthly", "biweekly"):
            label = f"{s}_{freq}_entry+weekly_exit"
            try:
                if s == "om25":
                    eq_path = run_om25(freq, base)
                else:
                    eq_path = run_tl25(freq, base)
                variants.append((label, eq_path))
            except Exception as e:
                print(f"[FAIL] {label}: {e}")

    rows = []
    for label, eq_path in variants:
        if not eq_path.exists():
            continue
        eq = pd.read_csv(eq_path, parse_dates=["date"])
        for period in ("full", "OOS", "IS"):
            rows.append(period_metrics(eq, label, is_boundary, period))

    df = pd.DataFrame(rows)
    df.to_csv(base / "comparison.csv", index=False)

    print("\n" + "=" * 90)
    print("CADENCE-VARIANT OOS COMPARISON")
    print("=" * 90)
    print(df.to_string(index=False))

    pivot = df[df["period"].isin(["OOS", "IS"])][
        ["variant", "period", "cagr_pct", "sharpe", "max_dd_pct"]
    ].pivot(index="variant", columns="period",
            values=["cagr_pct", "sharpe", "max_dd_pct"])
    print("\n=== Pivot (OOS vs IS) ===")
    print(pivot.to_string())
    with open(base / "comparison.txt", "w") as f:
        f.write("CADENCE-VARIANT OOS COMPARISON\n\n")
        f.write(df.to_string(index=False))
        f.write("\n\n=== Pivot (OOS vs IS) ===\n")
        f.write(pivot.to_string())
    print(f"\n[wrote] {base/'comparison.csv'}")


if __name__ == "__main__":
    main()
