"""OM25 three-state breadth-regime experiment (simple harness).

Compares the production OM25 v3 baseline (2-state NIFTY-100 regime) against a
3-state breadth-driven regime where ONLY the score weights change per state:

    State         Score (UC, CR)
    bull          (0.5, 0.5)     ← OM25 v3 production identity
    bear          (0.0, 1.0)     ← pure capture-ratio (defensive)
    deep          (1.0, 0.0)     ← pure upside-capture (score flip)

Exposure stays 100% in every state. The 20% from-peak drawdown stop is on in
every state. The only mechanical lever changing across states is the UC/CR
score blend. No free parameters — thresholds are atlas-derived.

Evaluated separately on IS (2009-09 → 2016-12) and three OOS sub-windows
inherited from oos_retune_2026.

Run:
    python tasks/breadth_atlas/experiments/om25_three_state_experiment.py
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

from scripts._clean_engine import (  # noqa: E402
    biweekly_fridays,
    fridays,
    monthly_first_trading_day,
    run_strategy,
)
from scripts.backtest_momentum import load_benchmark, load_price_panels  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts.om25_v3 import (  # noqa: E402
    LOCKED,
    build_regime_panel_confirmed,
    make_om25_tilt_score,
)


STATE_BULL = "bull"
STATE_BEAR = "bear"
STATE_DEEP = "deep"
STATE_NORMAL = "normal"

WEIGHTS = {
    STATE_BULL: (0.5, 0.5),
    STATE_BEAR: (0.0, 1.0),
    STATE_DEEP: (1.0, 0.0),
}

# 2-state weights: no bear regime, only normal vs deep value.
WEIGHTS_2STATE = {
    STATE_NORMAL: (0.5, 0.5),
    STATE_DEEP:   (1.0, 0.0),
}

# Always-on protections, all states.
DRAWDOWN_STOP = LOCKED["drawdown_stop_pct"]   # 0.20 — 20% from-peak
# Exposure stays 100% everywhere; we pass regime_panel=None to the engine.

# IS/OOS windows inherited from oos_retune_2026.
WINDOWS = {
    "IS":    ("2009-09-01", "2016-12-31"),
    "OOS-A": ("2017-01-01", "2019-12-31"),
    "OOS-B": ("2020-01-01", "2022-12-31"),
    "OOS-C": ("2023-01-01", "2026-05-08"),
}

# Atlas-derived breadth thresholds with asymmetric hysteresis. NOT optimised.
# Format: (bear_entry, bear_exit, deep_entry, deep_exit, higher_is_bull)
# Bear entries cluster near atlas medians; deep entries near atlas p5.
# Exit thresholds offset by ~5-10% of the metric's range to prevent flicker.
METRIC_THRESHOLDS = {
    "pct_above_200dma":     (0.40, 0.50, 0.20, 0.30, True),
    "avg_dist_from_200dma": (0.00, 0.05, -0.10, -0.05, True),
    "pct_above_100dma":     (0.40, 0.50, 0.20, 0.30, True),
    "pct_above_50dma":      (0.40, 0.50, 0.20, 0.30, True),
    "net_new_highs_pct":    (0.00, 0.03, -0.10, -0.05, True),
    "mcclellan_sum":        (2.50, 2.70, 1.50, 1.80, True),
}

UNIVERSES = {
    "Nifty250": "data/static/nifty250_universe.csv",
    "NSE500":   "data/static/nse500_universe.csv",
}


def load_breadth_panel(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    return df.sort_values("date").set_index("date")


def build_three_state_regime(
    series: pd.Series,
    *,
    bear_entry: float,
    bear_exit: float,
    deep_entry: float,
    deep_exit: float,
    higher_is_bull: bool,
    confirm_days: int,
    calendar: pd.DatetimeIndex,
) -> pd.Series:
    """Sticky three-state machine with asymmetric-threshold hysteresis.

    Transitions need `confirm_days` consecutive crossings of the relevant
    threshold. Direct bull↔deep transitions are NOT allowed — state must
    pass through bear. Starts in bull. Lagged 1 day at the end so today
    uses yesterday's close.
    """
    s = series.sort_index().replace([np.inf, -np.inf], np.nan).dropna()
    if not higher_is_bull:
        s = -s
        bear_entry, bear_exit = -bear_entry, -bear_exit
        deep_entry, deep_exit = -deep_entry, -deep_exit

    below_bear_entry = (s < bear_entry).rolling(confirm_days, min_periods=confirm_days).sum()
    above_bear_exit  = (s > bear_exit ).rolling(confirm_days, min_periods=confirm_days).sum()
    below_deep_entry = (s < deep_entry).rolling(confirm_days, min_periods=confirm_days).sum()
    above_deep_exit  = (s > deep_exit ).rolling(confirm_days, min_periods=confirm_days).sum()

    state = STATE_BULL
    out: list[str] = []
    for i in range(len(s)):
        bbe = below_bear_entry.iloc[i]
        abe = above_bear_exit.iloc[i]
        bde = below_deep_entry.iloc[i]
        ade = above_deep_exit.iloc[i]
        if state == STATE_BULL:
            if not np.isnan(bbe) and bbe == confirm_days:
                state = STATE_BEAR
        elif state == STATE_BEAR:
            if not np.isnan(bde) and bde == confirm_days:
                state = STATE_DEEP
            elif not np.isnan(abe) and abe == confirm_days:
                state = STATE_BULL
        elif state == STATE_DEEP:
            if not np.isnan(ade) and ade == confirm_days:
                state = STATE_BEAR
        out.append(state)

    regime = pd.Series(out, index=s.index, dtype=object)
    lagged = regime.shift(1).reindex(calendar).ffill()
    lagged.loc[lagged.isna()] = STATE_BULL
    return lagged.astype(object)


def build_two_state_regime(
    series: pd.Series,
    *,
    deep_entry: float,
    deep_exit: float,
    higher_is_bull: bool,
    confirm_days: int,
    calendar: pd.DatetimeIndex,
) -> pd.Series:
    """Sticky 2-state machine: normal/deep with asymmetric hysteresis.

    No bear state. Transitions only between normal and deep when the
    breadth metric crosses the deep_entry / deep_exit thresholds for
    `confirm_days` consecutive trading days. Lagged 1 day.
    """
    s = series.sort_index().replace([np.inf, -np.inf], np.nan).dropna()
    if not higher_is_bull:
        s = -s
        deep_entry, deep_exit = -deep_entry, -deep_exit

    below_deep = (s < deep_entry).rolling(confirm_days, min_periods=confirm_days).sum()
    above_deep = (s > deep_exit ).rolling(confirm_days, min_periods=confirm_days).sum()

    state = STATE_NORMAL
    out: list[str] = []
    for i in range(len(s)):
        bd = below_deep.iloc[i]
        ad = above_deep.iloc[i]
        if state == STATE_NORMAL:
            if not np.isnan(bd) and bd == confirm_days:
                state = STATE_DEEP
        elif state == STATE_DEEP:
            if not np.isnan(ad) and ad == confirm_days:
                state = STATE_NORMAL
        out.append(state)

    regime = pd.Series(out, index=s.index, dtype=object)
    lagged = regime.shift(1).reindex(calendar).ffill()
    lagged.loc[lagged.isna()] = STATE_NORMAL
    return lagged.astype(object)


def make_three_state_score(
    returns_universe: pd.DataFrame,
    regime: pd.Series,
    *,
    weights: dict | None = None,
    return_filter: bool = True,
    lookback: int = 252,
    min_obs: int = 220,
):
    """Score closure: picks UC/CR weights from `weights` by state."""
    w = weights if weights is not None else WEIGHTS
    default_state = STATE_NORMAL if STATE_NORMAL in w else STATE_BULL
    default_weights = w[default_state]
    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback:
            return pd.Series(dtype=float)
        state = regime.get(signal_date, default_state)
        w_uc, w_cr = w.get(state, default_weights)
        if w_uc + w_cr <= 0:
            return pd.Series(dtype=float)
        w_sum = w_uc + w_cr
        w_uc_n, w_cr_n = w_uc / w_sum, w_cr / w_sum

        window = returns_universe.iloc[idx - lookback + 1:idx + 1]
        market_ret = window.mean(axis=1)
        results = {}
        for sym in window.columns:
            r = window[sym].dropna()
            if len(r) < min_obs:
                continue
            if return_filter and ((1 + r).prod() - 1) <= 0:
                continue
            common = r.index.intersection(market_ret.index)
            sr = r.loc[common]
            mr = market_ret.loc[common]
            up = mr > 0
            dn = mr < 0
            if up.sum() < 50 or dn.sum() < 50:
                continue
            uc = sr[up].mean() / mr[up].mean() if mr[up].mean() > 0 else 0
            dc = sr[dn].mean() / mr[dn].mean() if mr[dn].mean() < 0 else 1
            ratio = uc / dc if dc > 0 else uc
            results[sym] = {"up": uc, "ratio": ratio}
        if not results:
            return pd.Series(dtype=float)
        df = pd.DataFrame(results).T
        up_pct = df["up"].rank(method="average") / len(df)
        cr_pct = df["ratio"].rank(method="average") / len(df)
        return w_uc_n * up_pct + w_cr_n * cr_pct

    return score_fn


def compute_metrics(result: dict, label: str, config: dict,
                    active_start: pd.Timestamp, active_end: pd.Timestamp,
                    regime: pd.Series | None) -> dict:
    eq = result["equity"].copy()
    trades = result["trades"].copy()
    exits = result["exits"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= active_start) & (pv.index <= active_end)]
    if len(pv) < 2:
        return {"label": label, **config, "error": "empty_window"}
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    drawdown = pv / pv.cummax() - 1.0
    max_dd = drawdown.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else np.nan

    state_days = {STATE_BULL: 0, STATE_BEAR: 0, STATE_DEEP: 0, STATE_NORMAL: 0}
    if regime is not None:
        active = regime.loc[(regime.index >= active_start) & (regime.index <= active_end)]
        for state in state_days:
            state_days[state] = int((active == state).sum())

    return {
        "label": label,
        **config,
        "start": str(pv.index[0].date()),
        "end": str(pv.index[-1].date()),
        "years": round(years, 2),
        "end_value": round(float(pv.iloc[-1]), 2),
        "total_return_pct": round((pv.iloc[-1] / pv.iloc[0] - 1) * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe_rf5": round(sharpe, 3),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(max_dd * 100, 2),
        "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None,
        "n_buys": int((trades["side"] == "BUY").sum()) if not trades.empty else 0,
        "n_sells": int((trades["side"] == "SELL").sum()) if not trades.empty else 0,
        "n_exits": int(len(exits)),
        "days_bull": state_days[STATE_BULL],
        "days_bear": state_days[STATE_BEAR],
        "days_deep": state_days[STATE_DEEP],
        "days_normal": state_days[STATE_NORMAL],
    }


def run_variant(
    *,
    label: str,
    close_panel, trade_panel, calendar, benchmark,
    returns_uni, entry_dates, weekly_dates,
    sma_200_panel, atr_20_panel,
    score_fn,
    args, config: dict,
    regime: pd.Series | None,
    out_dir: Path,
) -> dict | None:
    """Always: regime_panel=None (no exposure scaling), atr_min_floor=0.20 scalar."""
    result = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
        top_n=args.top_n, exit_buffer=args.exit_buffer,
        max_weight=args.max_weight, slippage=args.slippage,
        atr_mult=0.0, atr_min_floor=DRAWDOWN_STOP,
        use_trailing_stop=True, use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
        initial_capital=args.initial_capital,
    )
    if result is None:
        return None
    result["equity"].to_csv(out_dir / f"{label}_equity.csv", index=False)
    return compute_metrics(
        result, label=label, config=config,
        active_start=entry_dates[0], active_end=entry_dates[-1],
        regime=regime,
    )


def slice_dates(start: str, end: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    return pd.Timestamp(start), pd.Timestamp(end)


def build_entries(calendar, cadence, start, end):
    all_entries = biweekly_fridays(calendar) if cadence == "biweekly" else monthly_first_trading_day(calendar)
    weekly = fridays(calendar)
    return (all_entries[(all_entries >= start) & (all_entries <= end)],
            weekly[(weekly >= start) & (weekly <= end)])


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--breadth-panel", type=Path, default=ROOT / "data/breadth/breadth_daily.csv")
    ap.add_argument("--universes", nargs="+", default=list(UNIVERSES.keys()),
                    help="Universe labels to run (keys of UNIVERSES dict)")
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path, default=ROOT / LOCKED["regime_index_path"])
    ap.add_argument("--cadence", choices=["monthly", "biweekly"], default=LOCKED["cadence"])
    ap.add_argument("--confirm-days", type=int, default=LOCKED["regime_confirm_days"])
    ap.add_argument("--top-n", type=int, default=LOCKED["top_n"])
    ap.add_argument("--exit-buffer", type=int, default=LOCKED["exit_buffer"])
    ap.add_argument("--lookback", type=int, default=LOCKED["lookback"])
    ap.add_argument("--min-obs", type=int, default=LOCKED["min_obs"])
    ap.add_argument("--max-weight", type=float, default=LOCKED["max_weight"])
    ap.add_argument("--slippage", type=float, default=LOCKED["slippage"])
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--metrics", nargs="+", default=list(METRIC_THRESHOLDS.keys()))
    ap.add_argument("--bull-uc-only", action="store_true",
                    help="Bull state uses UC-only score (default: UC/CR 50/50)")
    ap.add_argument("--two-state", action="store_true",
                    help="Use 2-state regime (normal/deep) — no bear state. "
                         "Weights: normal=(0.5,0.5), deep=(1.0,0.0).")
    ap.add_argument("--output-dir", type=Path, default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or ROOT / "tasks/breadth_atlas/experiments/runs_3state" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] price panels")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark).reindex(calendar).ffill()
    sma_200_panel = close_panel.rolling(200, min_periods=200).mean()
    atr_20_panel = close_panel.pct_change().rolling(20).std()

    breadth = load_breadth_panel(args.breadth_panel)
    index_regime = build_regime_panel_confirmed(
        args.regime_index, LOCKED["regime_ma_window"], args.confirm_days, calendar=calendar
    )

    # Pre-build breadth regime panels (universe-independent).
    breadth_regimes: dict[str, pd.Series] = {}
    for metric in args.metrics:
        if metric not in METRIC_THRESHOLDS:
            raise ValueError(f"No fixed thresholds for {metric!r}")
        bear_in, bear_out, deep_in, deep_out, higher = METRIC_THRESHOLDS[metric]
        if args.two_state:
            breadth_regimes[metric] = build_two_state_regime(
                breadth[metric],
                deep_entry=deep_in, deep_exit=deep_out,
                higher_is_bull=higher, confirm_days=args.confirm_days,
                calendar=calendar,
            )
        else:
            breadth_regimes[metric] = build_three_state_regime(
                breadth[metric],
                bear_entry=bear_in, bear_exit=bear_out,
                deep_entry=deep_in, deep_exit=deep_out,
                higher_is_bull=higher, confirm_days=args.confirm_days,
                calendar=calendar,
            )

    rows: list[dict] = []
    for univ_label in args.universes:
        if univ_label not in UNIVERSES:
            raise ValueError(f"Unknown universe {univ_label!r}; options: {list(UNIVERSES)}")
        universe_path = ROOT / UNIVERSES[univ_label]
        universe = load_universe(universe_path)
        cols = [s for s in close_panel.columns if s in universe]
        returns_uni = close_panel[cols].pct_change()
        print(f"\n[universe] {univ_label}: {len(cols)} symbols from {universe_path.name}")

        baseline_score = make_om25_tilt_score(
            returns_uni, index_regime,
            bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
            bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
            return_filter=LOCKED["return_filter"], lookback=args.lookback, min_obs=args.min_obs,
        )
        if args.two_state:
            weights = dict(WEIGHTS_2STATE)
        else:
            weights = dict(WEIGHTS)
            if args.bull_uc_only:
                weights[STATE_BULL] = (1.0, 0.0)
        breadth_scores = {
            metric: make_three_state_score(
                returns_uni, reg, weights=weights,
                return_filter=LOCKED["return_filter"], lookback=args.lookback,
                min_obs=args.min_obs,
            )
            for metric, reg in breadth_regimes.items()
        }

        for window_name, (start_s, end_s) in WINDOWS.items():
            w_start, w_end = slice_dates(start_s, end_s)
            w_entries, w_weekly = build_entries(calendar, args.cadence, w_start, w_end)
            print(f"[{univ_label} {window_name}] {w_start.date()} -> {w_end.date()} : {len(w_entries)} entries")

            label = f"{univ_label}_{window_name}_baseline_2state"
            print(f"  {label}")
            b_row = run_variant(
                label=label,
                close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
                benchmark=benchmark, returns_uni=returns_uni,
                entry_dates=w_entries, weekly_dates=w_weekly,
                sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
                score_fn=baseline_score,
                args=args,
                config={"universe": univ_label, "window": window_name,
                        "regime": "baseline_2state", "metric": None},
                regime=None, out_dir=out_dir,
            )
            if b_row is not None:
                rows.append(b_row)

            for metric in args.metrics:
                label = f"{univ_label}_{window_name}_3state_{metric}"
                print(f"  {label}")
                row = run_variant(
                    label=label,
                    close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
                    benchmark=benchmark, returns_uni=returns_uni,
                    entry_dates=w_entries, weekly_dates=w_weekly,
                    sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
                    score_fn=breadth_scores[metric],
                    args=args,
                    config={"universe": univ_label, "window": window_name,
                            "regime": "3state_breadth", "metric": metric},
                    regime=breadth_regimes[metric], out_dir=out_dir,
                )
                if row is not None:
                    rows.append(row)

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False)

    active_weights = dict(WEIGHTS)
    if args.bull_uc_only:
        active_weights[STATE_BULL] = (1.0, 0.0)
    config_dump = {
        "windows": WINDOWS,
        "metric_thresholds": METRIC_THRESHOLDS,
        "weights": {k: list(v) for k, v in active_weights.items()},
        "drawdown_stop": DRAWDOWN_STOP,
        "metrics": list(args.metrics),
        "universes": list(args.universes),
        "confirm_days": args.confirm_days,
        "bull_uc_only": args.bull_uc_only,
    }
    (out_dir / "config.json").write_text(json.dumps(config_dump, indent=2, default=str))

    show_cols = ["universe", "window", "metric", "cagr_pct", "sharpe_rf5",
                 "max_dd_pct", "calmar", "days_bull", "days_bear", "days_deep"]
    print("\n=== All results ===")
    print(summary[show_cols].to_string(index=False))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
