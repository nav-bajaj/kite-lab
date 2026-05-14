"""Multi-strategy combo portfolio: top 8 each from L6 + OM25 v3 + TL25 v3.

Builds a 24-stock weekly-cadence portfolio whose holdings are the priority-
deduped union of each strategy's top-8.

  Each Thursday close → compute scores from all three strategies on their
  native universes (L6=NSE500, OM25=Nifty250, TL25=NSE500). Build the
  combined top-24 by:
    1) Take L6's top 8 (priority 1).
    2) From OM25's ranking, skip anything in L6's top 8; take the next 8.
    3) From TL25's ranking, skip anything in L6+OM25's combined; take next 8.
  → Friday OHLC/4 execution.

Compares against each constituent strategy as standalones on the same
window (2017-01 → 2026-05 OOS-style) and against L6 production.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, thursdays, fridays, biweekly_fridays,
)
from scripts._momentum_engine import (
    BASELINE as MM_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.tl25_v3 import (
    V3_LOCKED as TL25_LOCKED, build_tl25_panels, make_tl25_score,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics


N_PER_STRATEGY = 8


def make_combined_score_fn(score_fns_in_priority_order: list):
    """Combine multiple score functions into a single ranking via priority-dedup.

    Args:
      score_fns_in_priority_order: list of (label, score_fn) tuples.
        Priority is in order — first claims its top N, second claims its
        top N excluding first's picks, etc.

    Returns:
      score_fn(signal_date) → pd.Series indexed by symbol, scores descending.
      Up to N_PER_STRATEGY × len(score_fns) symbols.
    """
    def score_fn(signal_date, **_):
        picked = set()  # symbols already claimed by higher-priority strategy
        combined_rows = []  # list of (sym, src_label, within_strategy_rank)

        for label, sf in score_fns_in_priority_order:
            scores = sf(signal_date)
            if scores is None or scores.empty:
                continue
            ranked = scores.dropna().sort_values(ascending=False)
            taken = 0
            for sym in ranked.index:
                if sym in picked:
                    continue
                picked.add(sym)
                combined_rows.append((sym, label, taken))
                taken += 1
                if taken >= N_PER_STRATEGY:
                    break

        if not combined_rows:
            return pd.Series(dtype=float)
        # Convert to descending score: highest score for the first symbol
        n = len(combined_rows)
        return pd.Series({
            sym: float(n - i)
            for i, (sym, _label, _rank) in enumerate(combined_rows)
        })
    return score_fn


def build_context():
    """Load panels + score function closures for all three strategies."""
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    # L6 momentum on NSE 500
    print("[setup] L6 momentum on NSE 500 ...")
    nse500_uni = load_universe(ROOT / "data/static/nse500_universe.csv")
    nse500_cols = [s for s in close_panel.columns if s in nse500_uni]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(MM_BASELINE["lookback_months"]),
        skip_days=MM_BASELINE["skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels,
        vol_floor=MM_BASELINE["vol_floor"],
        vol_power=MM_BASELINE["vol_power"],
        cross_sectional_zscore=True,
    )

    # OM25 v3 on Nifty 250
    print("[setup] OM25 v3 on Nifty 250 ...")
    nifty250_uni = load_universe(ROOT / "data/static/nifty250_universe.csv")
    nifty250_cols = [s for s in close_panel.columns if s in nifty250_uni]
    om25_returns = close_panel[nifty250_cols].pct_change()
    om25_regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )

    # TL25 v3 on NSE 500
    print("[setup] TL25 v3 on NSE 500 ...")
    tl25_panels_data = build_tl25_panels(
        close_panel[nse500_cols],
        dma_short=TL25_LOCKED["dma_short"], dma_long=TL25_LOCKED["dma_long"],
        dma_persist_ref=TL25_LOCKED["dma_persist_ref"],
        persistence_window=TL25_LOCKED["persistence_window"],
        drawdown_window=TL25_LOCKED["drawdown_window"],
        drawdown_concavity=TL25_LOCKED["drawdown_concavity"],
        momentum_window=TL25_LOCKED["momentum_window"],
    )
    tl25_score = make_tl25_score(
        tl25_panels_data,
        w_persistence=TL25_LOCKED["w_persistence"],
        w_drawdown=TL25_LOCKED["w_drawdown"],
        w_momentum=TL25_LOCKED["w_momentum"],
    )

    return {
        "close_panel": close_panel, "trade_panel": trade_panel,
        "calendar": calendar, "benchmark_aligned": benchmark_aligned,
        "sma_200": sma_200, "atr_20": atr_20,
        "l6_score": l6_score, "om25_score": om25_score, "tl25_score": tl25_score,
        "n_l6": len(nse500_cols), "n_om25": len(nifty250_cols),
    }


WINDOWS = [
    ("IS",          "2009-09-01", "2016-12-31"),
    ("OOS_A",       "2017-01-01", "2019-12-31"),
    ("OOS_B",       "2020-01-01", "2022-12-31"),
    ("OOS_C",       "2023-01-01", "2026-05-08"),
    ("OOS_full",    "2017-01-01", "2026-05-08"),
    ("Prod window", "2020-07-10", "2026-05-08"),
]


def _calmar(c, d):
    if d is None or pd.isna(d) or abs(d) < 1e-6:
        return None
    return c / abs(d)


def _sortino(eq, start, end):
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    sub = eq[(eq["date"] >= s) & (eq["date"] <= e)]
    if len(sub) < 5: return None
    rets = sub["pv"].astype(float).pct_change().dropna()
    if rets.empty: return None
    downside = rets[rets < 0]
    if downside.empty or downside.std() == 0: return None
    excess = rets.mean() * 252 - 0.05
    return excess / (downside.std() * math.sqrt(252))


def evaluate_strategy(label, score_fn, ctx, top_n, entry_dates,
                       weekly_filt, min_hold_days=8):
    """Run a single strategy via run_strategy and slice into windows."""
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=top_n, exit_buffer=0,
        max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
        weekly_rank_check=False,
        regime_panel=None, bear_exposure=0.0,
        min_hold_days=min_hold_days,
        initial_capital=1_000_000,
    )
    eq = res["equity"]
    rows = []
    for w_id, start, end in WINDOWS:
        m = period_metrics(eq, w_id, start, end)
        cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
        rows.append({
            "track": label, "window": w_id,
            "cagr_pct": round(cagr, 2) if cagr is not None else None,
            "sharpe": round(sh, 2) if sh is not None else None,
            "sortino": round(_sortino(eq, start, end), 2)
                        if _sortino(eq, start, end) is not None else None,
            "calmar": round(_calmar(cagr, dd), 2)
                       if _calmar(cagr, dd) is not None else None,
            "max_dd_pct": round(dd, 2) if dd is not None else None,
        })
    return rows, res


def main():
    ctx = build_context()
    # Use Thursday signals (L6 native) for the combined portfolio, weekly cadence
    entry_thu = thursdays(ctx["calendar"])
    weekly_fri = fridays(ctx["calendar"])  # weekly DD-stop check day (unused — no stops here)
    start_ts = pd.Timestamp("2009-09-01")
    end_ts = pd.Timestamp("2026-05-08")
    entry_dates = entry_thu[(entry_thu >= start_ts) & (entry_thu <= end_ts)]
    weekly_filt = weekly_fri[(weekly_fri >= start_ts) & (weekly_fri <= end_ts)]

    all_rows = []

    # === Multi-strategy combo (L6 priority order) ===
    print("\n[run] Combo (L6 → OM25 → TL25 priority, 8+8+8 = 24 stocks, weekly) ...")
    combined_fn_l6first = make_combined_score_fn([
        ("L6", ctx["l6_score"]),
        ("OM25", ctx["om25_score"]),
        ("TL25", ctx["tl25_score"]),
    ])
    rows, res = evaluate_strategy("COMBO_L6_first", combined_fn_l6first, ctx,
                                    top_n=24, entry_dates=entry_dates,
                                    weekly_filt=weekly_filt)
    all_rows.extend(rows)
    combo_l6_eq = res["equity"]

    # === Multi-strategy combo (OM25 priority order) ===
    print("[run] Combo (OM25 → TL25 → L6 priority) ...")
    combined_fn_om25first = make_combined_score_fn([
        ("OM25", ctx["om25_score"]),
        ("TL25", ctx["tl25_score"]),
        ("L6", ctx["l6_score"]),
    ])
    rows, _ = evaluate_strategy("COMBO_OM25_first", combined_fn_om25first, ctx,
                                   top_n=24, entry_dates=entry_dates,
                                   weekly_filt=weekly_filt)
    all_rows.extend(rows)

    # === L6 standalone (Thursday, 24 stocks, for reference) ===
    print("[run] L6 standalone (Thursday weekly, 24 stocks) ...")
    rows, l6_res = evaluate_strategy("L6 standalone", ctx["l6_score"], ctx,
                                       top_n=24, entry_dates=entry_dates,
                                       weekly_filt=weekly_filt)
    all_rows.extend(rows)

    # === OM25 v3 standalone at Thursday/weekly (for context) ===
    print("[run] OM25 standalone (Thursday weekly, 24 stocks) ...")
    rows, _ = evaluate_strategy("OM25 standalone", ctx["om25_score"], ctx,
                                   top_n=24, entry_dates=entry_dates,
                                   weekly_filt=weekly_filt)
    all_rows.extend(rows)

    # === TL25 v3 standalone at Thursday/weekly (for context) ===
    print("[run] TL25 standalone (Thursday weekly, 24 stocks) ...")
    rows, _ = evaluate_strategy("TL25 standalone", ctx["tl25_score"], ctx,
                                   top_n=24, entry_dates=entry_dates,
                                   weekly_filt=weekly_filt)
    all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    out_dir = ROOT / "tasks/MM-tuning"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "multi_strategy_combo.csv"
    df.to_csv(out_path, index=False)

    # Pretty print
    print(f"\n{'=' * 120}")
    print("MULTI-STRATEGY COMBO (8+8+8 = 24 stocks, weekly Thursday signals)")
    print(f"  vs L6/OM25/TL25 standalones on the same setup")
    print(f"{'=' * 120}")
    for w in ["IS", "OOS_A", "OOS_B", "OOS_C", "OOS_full", "Prod window"]:
        sub = df[df["window"] == w]
        if sub.empty: continue
        print(f"\n--- {w} ---")
        cols = ["track", "cagr_pct", "sharpe", "sortino", "calmar", "max_dd_pct"]
        print(sub[cols].to_string(index=False))

    print(f"\n[wrote] {out_path}")


if __name__ == "__main__":
    main()
