"""COMBO Defensive with a breadth-driven 3-state regime (user state machine).

Replaces production COMBO's NIFTY-100 close-vs-100dma 2-state gate with a
3-state regime driven by `avg_dist_from_200dma` from the breadth atlas:

    State machine (sticky, deep is one-way to bull):
      bull -> bear : breadth below bear_entry for N days
      bear -> bull : breadth above bear_exit  for N days
      bear -> deep : breadth below deep_entry for N days
      deep -> bull : breadth above bear_exit  for N days (must reach BULL threshold)
      (no deep -> bear transition: deep is sticky until full bull recovery)

    Exposure mapping:
      bull -> 100%
      bear -> 50%
      deep -> 100%

The "deep is sticky to bull" design comes from the observation that
once we have deployed at 100% during a panic, intermediate de-risking
during the recovery is wealth-destroying. We only trim back to 50%
once normalcy returns (a NEW bull -> bear leg).

Comparisons (single full-span backtest each, metrics sliced per window):
  A_PROD          - current production (NIFTY-100 2-state, bear_skips_entries=True)
  B_BEAR_ENTRIES  - production gate but bear_skips_entries=False (24-stock structure)
  D_BREADTH       - this new variant
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from scripts.om25_v3 import (  # noqa: E402
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.combo_defensive import LOCKED as COMBO_LOCKED, make_combo_score_fn  # noqa: E402
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402


STATE_BULL = "bull"
STATE_BEAR = "bear"
STATE_DEEP = "deep"

# Atlas-derived thresholds (matches the OM25 3-state experiment that
# concluded avg_dist_from_200dma is the most consistent breadth metric).
BREADTH_METRIC = "avg_dist_from_200dma"
BEAR_ENTRY = 0.00
BEAR_EXIT  = 0.05
DEEP_ENTRY = -0.10
# deep_exit is not used in this machine — see docstring above.

EXPOSURE_MAP = {STATE_BULL: 1.0, STATE_BEAR: 0.5, STATE_DEEP: 1.0}

WINDOWS = {
    "IS":     ("2009-09-01", "2016-12-31"),
    "OOS-A":  ("2017-01-01", "2019-12-31"),
    "OOS-B":  ("2020-01-01", "2022-12-31"),
    "OOS-C":  ("2023-01-01", "2026-05-08"),
    "2021+":  ("2021-01-01", "2026-05-08"),
    "FULL":   ("2009-09-01", "2026-05-08"),
}


def build_three_state_regime_sticky_deep(
    series: pd.Series,
    *,
    bear_entry: float,
    bear_exit: float,
    deep_entry: float,
    higher_is_bull: bool,
    confirm_days: int,
    calendar: pd.DatetimeIndex,
) -> pd.Series:
    """Three-state regime with sticky-deep semantics.

    Transitions:
      bull -> bear  if breadth < bear_entry for confirm_days
      bear -> bull  if breadth > bear_exit  for confirm_days
      bear -> deep  if breadth < deep_entry for confirm_days
      deep -> bull  if breadth > bear_exit  for confirm_days (must reach BULL line)
      no deep -> bear

    Lagged 1 trading day at the end so today uses yesterday's close.
    """
    s = series.sort_index().replace([np.inf, -np.inf], np.nan).dropna()
    if not higher_is_bull:
        s = -s
        bear_entry, bear_exit, deep_entry = -bear_entry, -bear_exit, -deep_entry

    below_bear = (s < bear_entry).rolling(confirm_days, min_periods=confirm_days).sum()
    above_bear = (s > bear_exit ).rolling(confirm_days, min_periods=confirm_days).sum()
    below_deep = (s < deep_entry).rolling(confirm_days, min_periods=confirm_days).sum()

    state = STATE_BULL
    out: list[str] = []
    for i in range(len(s)):
        bb = below_bear.iloc[i]
        ab = above_bear.iloc[i]
        bd = below_deep.iloc[i]
        if state == STATE_BULL:
            if not np.isnan(bb) and bb == confirm_days:
                state = STATE_BEAR
        elif state == STATE_BEAR:
            if not np.isnan(bd) and bd == confirm_days:
                state = STATE_DEEP
            elif not np.isnan(ab) and ab == confirm_days:
                state = STATE_BULL
        elif state == STATE_DEEP:
            if not np.isnan(ab) and ab == confirm_days:
                state = STATE_BULL
        out.append(state)

    regime = pd.Series(out, index=s.index, dtype=object)
    lagged = regime.shift(1).reindex(calendar).ffill()
    lagged.loc[lagged.isna()] = STATE_BULL
    return lagged.astype(object)


def build_combo_score(close_panel, calendar, regime_index_path):
    """Production COMBO composite score — heterogeneous universes
    (L6 on NSE 500, OM25 on Nifty 250) with priority dedup.
    OM25's internal regime tilt fires inside this score regardless of
    the portfolio-level regime overlay used downstream.
    """
    nse500 = load_universe(ROOT / COMBO_LOCKED["l6_universe_csv"])
    nse500_cols = [s for s in close_panel.columns if s in nse500]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(COMBO_LOCKED["l6_lookback_months"]),
        skip_days=COMBO_LOCKED["l6_skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=COMBO_LOCKED["l6_vol_floor"],
        vol_power=COMBO_LOCKED["l6_vol_power"], cross_sectional_zscore=True,
    )

    nifty250 = load_universe(ROOT / COMBO_LOCKED["om25_universe_csv"])
    nifty250_cols = [s for s in close_panel.columns if s in nifty250]
    om25_returns = close_panel[nifty250_cols].pct_change()
    om25_internal_regime = build_regime_panel_confirmed(
        regime_index_path,
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_internal_regime,
        bull_w_uc=COMBO_LOCKED["om25_bull_w_uc"], bull_w_cr=COMBO_LOCKED["om25_bull_w_cr"],
        bear_w_uc=COMBO_LOCKED["om25_bear_w_uc"], bear_w_cr=COMBO_LOCKED["om25_bear_w_cr"],
        return_filter=COMBO_LOCKED["om25_return_filter"],
        lookback=COMBO_LOCKED["om25_lookback"], min_obs=COMBO_LOCKED["om25_min_obs"],
    )
    return make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=COMBO_LOCKED["n_per_strategy"],
    )


def load_breadth_panel(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    return df.sort_values("date").set_index("date")


def run_variant(*, label, close_panel, trade_panel, calendar, benchmark_aligned,
                sma_200, atr_20, entry_dates, weekly_dates, combo_score,
                portfolio_regime, bear_exposure, bear_skips_entries,
                args, out_dir, regime_redeploy_on_increase=False):
    print(f"[run] {label}  "
          f"regime_panel={'YES' if portfolio_regime is not None else 'None'}  "
          f"bear_exposure={bear_exposure}  "
          f"bear_skips_entries={bear_skips_entries}  "
          f"redeploy={regime_redeploy_on_increase}")
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
        signal_function=combo_score, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=COMBO_LOCKED["top_n"], exit_buffer=COMBO_LOCKED["exit_buffer"],
        max_weight=COMBO_LOCKED["max_weight"], slippage=COMBO_LOCKED["slippage"],
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False, weekly_rank_check=False,
        regime_panel=portfolio_regime,
        bear_exposure=bear_exposure,
        bear_skips_entries=bear_skips_entries,
        regime_redeploy_on_increase=regime_redeploy_on_increase,
        min_hold_days=COMBO_LOCKED["min_hold_days"],
        initial_capital=args.initial_capital,
    )
    if res is None:
        return None
    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq.to_csv(out_dir / f"{label}_equity.csv", index=False)
    res["trades"].to_csv(out_dir / f"{label}_trades.csv", index=False)
    return res


def window_metrics(pv: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    pv = pv.loc[(pv.index >= start) & (pv.index <= end)]
    if len(pv) < 2:
        return {}
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    dd = (pv / pv.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd < 0 else np.nan
    return {
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(sharpe, 3),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(dd * 100, 2),
        "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None,
        "years": round(years, 2),
    }


def holdings_stats(eq: pd.DataFrame, breadth_regime: pd.Series,
                   start: pd.Timestamp, end: pd.Timestamp) -> dict:
    sub = eq.loc[(eq["date"] >= start) & (eq["date"] <= end)]
    if len(sub) == 0:
        return {}
    reg_aligned = breadth_regime.reindex(sub["date"]).ffill()
    bull_mask = reg_aligned.values == STATE_BULL
    bear_mask = reg_aligned.values == STATE_BEAR
    deep_mask = reg_aligned.values == STATE_DEEP
    cash_pct = sub["cash_pct"] if "cash_pct" in sub.columns else None
    return {
        "n_days": len(sub),
        "n_bull_days": int(bull_mask.sum()),
        "n_bear_days": int(bear_mask.sum()),
        "n_deep_days": int(deep_mask.sum()),
        "bull_holdings_mean": round(float(sub.loc[bull_mask, "holdings"].mean()), 1) if bull_mask.any() else None,
        "bear_holdings_mean": round(float(sub.loc[bear_mask, "holdings"].mean()), 1) if bear_mask.any() else None,
        "deep_holdings_mean": round(float(sub.loc[deep_mask, "holdings"].mean()), 1) if deep_mask.any() else None,
        "end_holdings": int(sub["holdings"].iloc[-1]),
        "end_cash_pct": round(float(cash_pct.iloc[-1]) * 100, 2) if cash_pct is not None else None,
    }


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path, default=ROOT / COMBO_LOCKED["regime_index_path"])
    ap.add_argument("--breadth-panel", type=Path, default=ROOT / "data/breadth/breadth_daily.csv")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--output-dir", type=Path, default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or ROOT / "tasks/breadth_atlas/combo_3state/runs" / f"combo_breadth_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] price panels")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark).reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    combo_score = build_combo_score(close_panel, calendar, args.regime_index)

    # Production NIFTY-100 MA-100 2-state (for A_PROD and B_BEAR_ENTRIES)
    ma_regime = build_regime_panel_confirmed(
        args.regime_index,
        COMBO_LOCKED["regime_ma_window"], COMBO_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )

    # Breadth 3-state regime (sticky-deep state machine)
    print(f"[breadth] loading {args.breadth_panel.name}")
    breadth = load_breadth_panel(args.breadth_panel)
    breadth_regime = build_three_state_regime_sticky_deep(
        breadth[BREADTH_METRIC],
        bear_entry=BEAR_ENTRY, bear_exit=BEAR_EXIT, deep_entry=DEEP_ENTRY,
        higher_is_bull=True, confirm_days=COMBO_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    breadth_exposure = breadth_regime.map(EXPOSURE_MAP).astype(float)

    # Diagnostic: transition counts
    transitions = []
    prev = None
    for d, st in breadth_regime.items():
        if st != prev:
            transitions.append((d, prev, st))
            prev = st
    print(f"[breadth] state-machine transitions over full calendar:")
    counts = {}
    for _, p, s in transitions[1:]:  # skip first (None -> bull)
        key = f"{p} -> {s}"
        counts[key] = counts.get(key, 0) + 1
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v} times")
    transitions_df = pd.DataFrame(transitions, columns=["date", "from_state", "to_state"])
    transitions_df.to_csv(out_dir / "breadth_transitions.csv", index=False)

    # Entry / weekly date setup
    full_start = pd.Timestamp(WINDOWS["FULL"][0])
    full_end = pd.Timestamp(WINDOWS["FULL"][1])
    entry_dates = biweekly_fridays(calendar)
    entry_dates = entry_dates[(entry_dates >= full_start) & (entry_dates <= full_end)]
    weekly = fridays(calendar)
    weekly_dates = weekly[(weekly >= full_start) & (weekly <= full_end)]

    variants = [
        # (label, regime_panel, bear_exposure, bear_skips_entries, redeploy_on_increase)
        ("A_PROD",         ma_regime,         0.5, True,  False),
        ("B_BEAR_ENTRIES", ma_regime,         0.5, False, False),
        ("D_BREADTH",      breadth_exposure,  0.0, False, True),   # NEW: redeploy on bear→deep/bull
    ]

    eqs = {}
    for label, reg, be, bse, redeploy in variants:
        res = run_variant(
            label=label, close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark,
            sma_200=sma_200, atr_20=atr_20,
            entry_dates=entry_dates, weekly_dates=weekly_dates,
            combo_score=combo_score,
            portfolio_regime=reg, bear_exposure=be, bear_skips_entries=bse,
            regime_redeploy_on_increase=redeploy,
            args=args, out_dir=out_dir,
        )
        if res is not None:
            eq = res["equity"].copy()
            eq["date"] = pd.to_datetime(eq["date"])
            eqs[label] = eq

    # === Per-window metrics ===
    print("\n=== Per-window metrics ===\n")
    rows = []
    for label, eq in eqs.items():
        pv = eq.set_index("date")["pv"].astype(float)
        for window_name, (start_s, end_s) in WINDOWS.items():
            s, e = pd.Timestamp(start_s), pd.Timestamp(end_s)
            m = window_metrics(pv, s, e)
            if not m:
                continue
            rows.append({"variant": label, "window": window_name, **m})
    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv(out_dir / "metrics_by_window.csv", index=False)

    show_cols = ["variant", "window", "cagr_pct", "sharpe", "max_dd_pct", "calmar", "years"]
    for window_name in WINDOWS:
        sub = metrics_df[metrics_df["window"] == window_name]
        if sub.empty:
            continue
        print(f"--- {window_name} ---")
        print(sub[show_cols].to_string(index=False))
        print()

    # === Holdings stats (D_BREADTH uses breadth-state labels) ===
    if "D_BREADTH" in eqs:
        print("\n=== D_BREADTH holdings by breadth state ===\n")
        h_rows = []
        for window_name, (start_s, end_s) in WINDOWS.items():
            s, e = pd.Timestamp(start_s), pd.Timestamp(end_s)
            stats = holdings_stats(eqs["D_BREADTH"], breadth_regime, s, e)
            if stats:
                h_rows.append({"window": window_name, **stats})
        h_df = pd.DataFrame(h_rows)
        h_df.to_csv(out_dir / "breadth_holdings_by_window.csv", index=False)
        print(h_df.to_string(index=False))

    (out_dir / "config.json").write_text(json.dumps({
        "variants": [
            {"label": "A_PROD", "regime": "NIFTY-100 100-DMA 2-state, bear_skips_entries=True"},
            {"label": "B_BEAR_ENTRIES", "regime": "NIFTY-100 100-DMA 2-state, bear_skips_entries=False"},
            {"label": "D_BREADTH", "regime": f"breadth 3-state on {BREADTH_METRIC}, sticky-deep state machine, exposure 100/50/100"},
        ],
        "breadth_metric": BREADTH_METRIC,
        "breadth_thresholds": {
            "bear_entry": BEAR_ENTRY, "bear_exit": BEAR_EXIT, "deep_entry": DEEP_ENTRY,
        },
        "state_machine": "sticky-deep — deep transitions ONLY to bull (no deep->bear)",
        "exposure_map": EXPOSURE_MAP,
        "confirm_days": COMBO_LOCKED["regime_confirm_days"],
        "windows": WINDOWS,
    }, indent=2, default=str))
    print(f"[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
