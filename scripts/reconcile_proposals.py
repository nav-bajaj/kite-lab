"""Reconcile the membership proposal rule against the engine's recorded trades.

For a portfolio run dir (which has ``*_signals.csv`` + ``*_trades.csv``), replay
the trades to reconstruct holdings before each entry rebalance, run
``propose_next_rebalance`` using that rebalance's signal ranking, and compare
the predicted BUYs/SELLs to what the engine actually traded. This quantifies
how faithfully the rank + exit-buffer rule reproduces the engine — the main
expected divergence being ad-hoc trailing-stop / DMA exits the rank rule does
not model (they appear as ``extra_actual_sells``).

Run this on staging against real run dirs to validate before the proposal
artifact is exposed to clients.

    python scripts/reconcile_proposals.py \
        --run-dir data/om25_v3_portfolios/om25_v3_portfolio_<ts> \
        --top-n 24 --exit-buffer 15
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datetime import date as _date, timedelta  # noqa: E402

from data_pipeline.rebalance_proposal import propose_next_rebalance  # noqa: E402


def reconcile(
    signals_by_date: dict,
    trades: list,
    *,
    top_n: int,
    exit_buffer: int,
    bear_by_date: dict | None = None,
    bear_skips_entries: bool = False,
    window_days: int = 7,
) -> dict:
    """Compare predicted vs actual membership changes per entry rebalance.

    Args:
        signals_by_date: ``{date: [symbols ranked best-first]}`` at entry dates.
        trades: list of ``{"date", "symbol", "side"}`` (engine's recorded trades).
        bear_by_date: optional ``{date: bool}`` bear-regime flag at each signal date.
        window_days: a rebalance's execution trades are matched within this many
            days after the signal date; a rebalance with no trades in the window
            is treated as a no-change rebalance (actuals empty), not mis-mapped
            to a later one.

    Returns ``{"results": [...per rebalance...], "summary": {...}}``.
    """
    by_date: dict = {}
    for t in trades:
        slot = by_date.setdefault(t["date"], {"BUY": set(), "SELL": set()})
        slot[t["side"]].add(t["symbol"])
    trade_dates = sorted((_date.fromisoformat(d), d) for d in by_date)

    results = []
    for D in sorted(signals_by_date):
        d_parsed = _date.fromisoformat(D)

        # Execution trades for this rebalance: first trade date within the window.
        exec_d = None
        for tp, ts in trade_dates:
            if d_parsed <= tp <= d_parsed + timedelta(days=window_days):
                exec_d = ts
                break

        # Holdings just before this rebalance = replay all trades strictly before D
        # (captures any off-week weekly-exit trades since the last entry).
        holdings: set = set()
        for tp, ts in trade_dates:
            if tp >= d_parsed:
                break
            holdings |= by_date[ts]["BUY"]
            holdings -= by_date[ts]["SELL"]

        is_bear = bool(bear_by_date.get(D)) if bear_by_date else False
        prop = propose_next_rebalance(
            signals_by_date[D], holdings,
            top_n=top_n, exit_buffer=exit_buffer, is_entry=True,
            is_bear=is_bear, bear_skips_entries=bear_skips_entries,
        )
        pred_buys = {o.symbol for o in prop.buys}
        pred_sells = {o.symbol for o in prop.sells}
        act_buys = by_date[exec_d]["BUY"] if exec_d else set()
        act_sells = by_date[exec_d]["SELL"] if exec_d else set()

        results.append({
            "signal_date": D,
            "exec_date": exec_d,
            "buys_match": pred_buys == act_buys,
            "sells_match": pred_sells == act_sells,
            "extra_actual_sells": sorted(act_sells - pred_sells),    # likely stop exits
            "missing_actual_sells": sorted(pred_sells - act_sells),
            "extra_actual_buys": sorted(act_buys - pred_buys),
            "missing_actual_buys": sorted(pred_buys - act_buys),
        })

    n = len(results)
    exact = sum(1 for r in results if r["buys_match"] and r["sells_match"])
    buys_ok = sum(1 for r in results if r["buys_match"])
    sells_ok = sum(1 for r in results if r["sells_match"])
    summary = {
        "rebalances": n,
        "exact_match": exact,
        "buys_match": buys_ok,
        "sells_match": sells_ok,
        "match_rate": round(exact / n, 4) if n else None,
    }
    return {"results": results, "summary": summary}


# --- CLI: load a run dir's signals + trades and reconcile --------------------

def _load_signals(signals_csv: Path):
    import pandas as pd
    df = pd.read_csv(signals_csv)
    signals_by_date, bear_by_date = {}, {}
    for d, grp in df.sort_values("rank").groupby("date"):
        ds = str(pd.Timestamp(d).date())
        signals_by_date[ds] = grp["symbol"].astype(str).tolist()
        if "regime" in grp.columns:
            bear_by_date[ds] = str(grp["regime"].iloc[0]).lower() == "bear"
    return signals_by_date, bear_by_date


def _load_trades(trades_csv: Path):
    import pandas as pd
    df = pd.read_csv(trades_csv)
    return [
        {"date": str(pd.Timestamp(r["date"]).date()),
         "symbol": str(r["symbol"]), "side": str(r["side"])}
        for _, r in df.iterrows()
    ]


def _find(run_dir: Path, suffix: str):
    hits = sorted(run_dir.glob(f"*{suffix}"))
    return hits[0] if hits else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Reconcile proposals vs recorded trades")
    ap.add_argument("--run-dir", type=Path, required=True)
    ap.add_argument("--top-n", type=int, required=True)
    ap.add_argument("--exit-buffer", type=int, required=True)
    ap.add_argument("--bear-skips-entries", action="store_true")
    args = ap.parse_args()

    signals_csv = _find(args.run_dir, "_signals.csv")
    trades_csv = _find(args.run_dir, "_trades.csv")
    if not signals_csv or not trades_csv:
        print(f"ERROR: need *_signals.csv and *_trades.csv in {args.run_dir}")
        return 1

    signals_by_date, bear_by_date = _load_signals(signals_csv)
    trades = _load_trades(trades_csv)
    rep = reconcile(
        signals_by_date, trades,
        top_n=args.top_n, exit_buffer=args.exit_buffer,
        bear_by_date=bear_by_date, bear_skips_entries=args.bear_skips_entries,
    )

    s = rep["summary"]
    print(f"Rebalances: {s['rebalances']}  exact: {s['exact_match']}  "
          f"buys_ok: {s['buys_match']}  sells_ok: {s['sells_match']}  "
          f"match_rate: {s['match_rate']}")
    for r in rep["results"]:
        if not (r["buys_match"] and r["sells_match"]):
            print(f"  {r['signal_date']} -> {r['exec_date']}: "
                  f"+sells {r['extra_actual_sells']} -sells {r['missing_actual_sells']} "
                  f"+buys {r['extra_actual_buys']} -buys {r['missing_actual_buys']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
