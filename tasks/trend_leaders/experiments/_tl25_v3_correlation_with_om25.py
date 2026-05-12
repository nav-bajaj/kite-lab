"""Compare A3 (single Offensive) vs B2 (tilt) on correlation with OM25 v3.

User insight: regime-tilt TL25 may collapse diversification with OM25 v3
since both fire bear-mode at the same dates. Single Offensive TL25
ignores regime entirely → different exposure profile.

Verify with:
  - Daily-return correlation between OM25 v3 equity and each TL25
  - Holdings overlap (Jaccard) at sampled rebalance dates
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy
from scripts.tl25_v3 import make_tl25_score
from scripts.om25_v3 import build_regime_panel_confirmed
from tasks.trend_leaders.experiments._tl25_v3_baseline import setup as tl25_setup


REGIME_INDEX = ROOT / "indices_data_historical/NIFTY_100.csv"
OM25_EQUITY = ROOT / "tasks/oos_retune_2026/winner_artifacts/om25_winner_v2_with_dd_stop_equity.csv"


def run_tl25(label, ctx, regime, bull, bear):
    bp, bd, bm = bull
    rp, rd, rm = bear
    atr_panel = ctx["close_panel"].pct_change().rolling(20).std()
    has_tilt = (rp, rd, rm) != (bp, bd, bm)
    score_fn = make_tl25_score(
        ctx["panels"],
        w_persistence=bp, w_drawdown=bd, w_momentum=bm,
        regime_panel=regime if has_tilt else None,
        bear_w_persistence=rp if has_tilt else None,
        bear_w_drawdown=rd if has_tilt else None,
        bear_w_momentum=rm if has_tilt else None,
    )
    t0 = time.time()
    print(f"  [run] {label} ...", flush=True)
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=ctx["entry_dates"], weekly_signal_dates=ctx["weekly_filt"],
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=atr_panel,
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.20,
        use_trailing_stop=True, use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
    )
    print(f"      done {time.time() - t0:.0f}s", flush=True)
    return res


def holdings_at(trades_df, date):
    """Reconstruct holdings (set of symbols) at a given date from trades."""
    held = {}
    sub = trades_df[trades_df["date"] <= date]
    for _, t in sub.iterrows():
        sym = t["symbol"]
        if t["side"] == "BUY":
            held[sym] = held.get(sym, 0) + t["shares"]
        else:
            held[sym] = held.get(sym, 0) - t["shares"]
    return {s for s, sh in held.items() if sh > 0}


def jaccard(a, b):
    if not a and not b: return 0
    return len(a & b) / max(len(a | b), 1)


def main():
    ctx = tl25_setup()
    print(f"[regime] panel...", flush=True)
    regime = build_regime_panel_confirmed(REGIME_INDEX, 100, 3, calendar=ctx["calendar"])

    # Load OM25 v3 equity + reconstruct OM25 trades for holdings
    om25_eq = pd.read_csv(OM25_EQUITY, parse_dates=["date"])
    om25_eq["date"] = pd.to_datetime(om25_eq["date"])
    om25_pv = om25_eq.set_index("date")["pv"].astype(float)
    om25_rets = om25_pv.pct_change().dropna()

    # Try to find OM25 trades file
    om25_trades_path = ROOT / "tasks/oos_retune_2026/winner_artifacts/om25_winner_v2_trades.csv"
    om25_trades = None
    if om25_trades_path.exists():
        om25_trades = pd.read_csv(om25_trades_path, parse_dates=["date"])
        om25_trades["date"] = pd.to_datetime(om25_trades["date"])

    print(f"\n[backtest] TL25 candidates...", flush=True)
    res_a3 = run_tl25(
        "A3) Single Offensive P+M 40/20/40", ctx, regime,
        (0.40, 0.20, 0.40), (0.40, 0.20, 0.40),
    )
    res_b2 = run_tl25(
        "B2) P-heavy 50/25/25 → P+DD 50/50/0 tilt", ctx, regime,
        (0.50, 0.25, 0.25), (0.50, 0.50, 0.00),
    )

    eq_a3 = res_a3["equity"].copy()
    eq_a3["date"] = pd.to_datetime(eq_a3["date"])
    eq_b2 = res_b2["equity"].copy()
    eq_b2["date"] = pd.to_datetime(eq_b2["date"])
    rets_a3 = eq_a3.set_index("date")["pv"].astype(float).pct_change().dropna()
    rets_b2 = eq_b2.set_index("date")["pv"].astype(float).pct_change().dropna()

    print(f"\n{'=' * 80}")
    print("DAILY-RETURN CORRELATION vs OM25 v3 (full period)")
    print(f"{'=' * 80}")
    common_a3 = pd.concat([om25_rets, rets_a3], axis=1, keys=["om25", "a3"]).dropna()
    common_b2 = pd.concat([om25_rets, rets_b2], axis=1, keys=["om25", "b2"]).dropna()
    corr_a3 = common_a3["om25"].corr(common_a3["a3"])
    corr_b2 = common_b2["om25"].corr(common_b2["b2"])
    print(f"  A3 (single Offensive)  vs OM25 v3:  daily return correlation = {corr_a3:.3f}")
    print(f"  B2 (regime-tilt)       vs OM25 v3:  daily return correlation = {corr_b2:.3f}")

    # By-regime correlations
    print(f"\n--- Same correlations split by regime (using NIFTY 100 100-DMA 3-conf):")
    reg = regime.reindex(common_a3.index).fillna(True)
    bull_dates = reg[reg == True].index
    bear_dates = reg[reg == False].index
    if len(bull_dates) > 30:
        c_a3_bull = common_a3.loc[common_a3.index.intersection(bull_dates)]
        c_b2_bull = common_b2.loc[common_b2.index.intersection(bull_dates)]
        print(f"  Bull regime ({len(c_a3_bull)} days):")
        print(f"    A3 vs OM25: {c_a3_bull['om25'].corr(c_a3_bull['a3']):.3f}")
        print(f"    B2 vs OM25: {c_b2_bull['om25'].corr(c_b2_bull['b2']):.3f}")
    if len(bear_dates) > 30:
        c_a3_bear = common_a3.loc[common_a3.index.intersection(bear_dates)]
        c_b2_bear = common_b2.loc[common_b2.index.intersection(bear_dates)]
        print(f"  Bear regime ({len(c_a3_bear)} days):")
        print(f"    A3 vs OM25: {c_a3_bear['om25'].corr(c_a3_bear['a3']):.3f}")
        print(f"    B2 vs OM25: {c_b2_bear['om25'].corr(c_b2_bear['b2']):.3f}")

    # Holdings overlap at sampled dates
    if om25_trades is not None:
        print(f"\n{'=' * 80}")
        print("HOLDINGS OVERLAP (Jaccard) at quarterly snapshots")
        print(f"{'=' * 80}")
        sample_dates = pd.date_range("2018-01-01", "2026-05-01", freq="QS-JAN")
        tr_a3 = res_a3["trades"].copy()
        tr_a3["date"] = pd.to_datetime(tr_a3["date"])
        tr_b2 = res_b2["trades"].copy()
        tr_b2["date"] = pd.to_datetime(tr_b2["date"])

        rows = []
        for d in sample_dates:
            try:
                h_om = holdings_at(om25_trades, d)
                h_a3 = holdings_at(tr_a3, d)
                h_b2 = holdings_at(tr_b2, d)
                reg_d = bool(regime.get(d, True))
                rows.append({
                    "date": d.date(),
                    "regime": "bull" if reg_d else "bear",
                    "om25_n": len(h_om),
                    "a3_n": len(h_a3),
                    "b2_n": len(h_b2),
                    "a3_vs_om25": round(jaccard(h_om, h_a3), 3),
                    "b2_vs_om25": round(jaccard(h_om, h_b2), 3),
                    "a3_b2_overlap": round(jaccard(h_a3, h_b2), 3),
                })
            except Exception:
                continue
        ovr = pd.DataFrame(rows)
        print(ovr.to_string(index=False))

        bull_rows = ovr[ovr["regime"] == "bull"]
        bear_rows = ovr[ovr["regime"] == "bear"]
        print(f"\n--- Avg Jaccard overlap ---")
        print(f"  Bull regime: A3 vs OM25 = {bull_rows['a3_vs_om25'].mean():.3f},  "
              f"B2 vs OM25 = {bull_rows['b2_vs_om25'].mean():.3f}")
        if len(bear_rows) > 0:
            print(f"  Bear regime: A3 vs OM25 = {bear_rows['a3_vs_om25'].mean():.3f},  "
                  f"B2 vs OM25 = {bear_rows['b2_vs_om25'].mean():.3f}")


if __name__ == "__main__":
    main()
