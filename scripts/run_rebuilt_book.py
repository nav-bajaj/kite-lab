#!/usr/bin/env python
"""Production runner for the rebuilt books (mm_v1, om25_v4) — production_port_2026 P2.

    python scripts/run_rebuilt_book.py --book mm_v1 [--start 2020-01-01] [--end YYYY-MM-DD] [--output-dir DIR]

Reads the master store (MASTER_STORE_DIR, /data/master on Railway), writes data/<book>_portfolios/<book>_portfolio_<ts>/ in the
layout sync_service and the dashboard already read: <book>_equity/trades/exits/signals.csv, metrics.json, latest.json and
backtests/baseline/momentum_*.csv. The book's published history starts at --start; its research lock date is in metrics.json.
"""
from __future__ import annotations
import argparse, json, sys, os
from pathlib import Path
import pandas as pd
ROOT = Path(os.environ.get("KITE_LAB_ROOT", Path(__file__).resolve().parents[1])); sys.path.insert(0, str(ROOT))
from scripts.rebuilt_books import BOOKS, build_and_run  # noqa: E402
from scripts.run_om25_v3_portfolio import write_dashboard_outputs  # noqa: E402
from scripts.metrics_common import compute_dashboard_metrics  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--book", choices=BOOKS, required=True); ap.add_argument("--start", default="2020-01-01"); ap.add_argument("--end", default=None)
    ap.add_argument("--output-dir", type=Path, default=None); ap.add_argument("--master-dir", type=Path, default=None)
    a = ap.parse_args(); ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out = a.output_dir or ROOT / f"data/{a.book}_portfolios/{a.book}_portfolio_{ts}"; out.mkdir(parents=True, exist_ok=True)
    dash = out / "backtests" / "baseline"; dash.mkdir(parents=True, exist_ok=True)
    print(f"[run] {a.book} · start {a.start} · output {out}")
    cfg, res, signals, regime, close = build_and_run(a.book, a.start, a.end, a.master_dir)
    if res is None:
        print("  [no result — empty rebalance set]"); return
    eq, trades, exits = res["equity"].copy(), res["trades"].copy(), res["exits"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    eq.to_csv(out / f"{a.book}_equity.csv", index=False); trades.to_csv(out / f"{a.book}_trades.csv", index=False); exits.to_csv(out / f"{a.book}_exits.csv", index=False); signals.to_csv(out / f"{a.book}_signals.csv", index=False)
    write_dashboard_outputs(dashboard_dir=dash, eq=eq, trades=trades, exits=exits, close_panel=close, slippage=cfg["slippage"])
    m = compute_dashboard_metrics(eq.rename(columns={"pv": "portfolio_value"})[["date", "portfolio_value"]], trades, exits)
    metrics = {"book": a.book, "name": cfg["name"], "config": cfg, "start": a.start, "end": a.end, "run_at": ts, "lock_date": cfg["lock_date"],
               "result": {k: (float(v) if isinstance(v, (int, float)) else str(v)) for k, v in m.items()},
               "regime_today": "bull" if bool(regime.iloc[-1]) else "bear", "holdings": int(eq["holdings"].iloc[-1]), "cash_pct": float(eq["cash_pct"].iloc[-1])}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    (out.parent / "latest.json").write_text(json.dumps({"path": out.name, "timestamp": pd.Timestamp.now().isoformat()}))
    r = metrics["result"]; print(f"[done] {a.book}: {r.get('start')} → {r.get('end')}  CAGR {100*float(r['cagr']):.1f}%  Sharpe {float(r['sharpe_ratio']):.2f}  MaxDD {100*float(r['max_drawdown']):.1f}%  trades {int(float(r['trades_total']))}  regime today {metrics['regime_today']}")


if __name__ == "__main__":
    main()
