"""OM25 breadth-regime experiment.

This is research code, not production pipeline code. It compares the locked
OM25 v3 index regime against breadth-derived regimes in three roles:

1. score   - breadth controls the OM25 UC/CR score tilt only
2. overlay - breadth controls portfolio exposure only
3. both    - breadth controls both score tilt and portfolio exposure

Example:
    python tasks/breadth_atlas/experiments/om25_breadth_regime_experiment.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
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


@dataclass(frozen=True)
class BreadthRule:
    metric: str
    threshold: float
    higher_is_bull: bool = True

    @property
    def slug(self) -> str:
        direction = "ge" if self.higher_is_bull else "le"
        thresh = str(self.threshold).replace("-", "m").replace(".", "p")
        return f"{self.metric}_{direction}_{thresh}"


QUICK_RULES = [
    BreadthRule("pct_above_200dma", 0.40),
    BreadthRule("avg_dist_from_200dma", 0.00),
    BreadthRule("net_new_highs_pct", 0.00),
]

FULL_RULES = [
    BreadthRule("pct_above_200dma", 0.30),
    BreadthRule("pct_above_200dma", 0.40),
    BreadthRule("pct_above_200dma", 0.50),
    BreadthRule("pct_above_100dma", 0.35),
    BreadthRule("pct_above_100dma", 0.45),
    BreadthRule("avg_dist_from_200dma", -0.05),
    BreadthRule("avg_dist_from_200dma", 0.00),
    BreadthRule("net_new_highs_pct", -0.05),
    BreadthRule("net_new_highs_pct", 0.00),
]


def parse_rule(raw: str) -> BreadthRule:
    """Parse metric:threshold[:higher|lower]."""
    parts = raw.split(":")
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError(
            "Rule must be metric:threshold or metric:threshold:higher|lower"
        )
    metric = parts[0]
    try:
        threshold = float(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid threshold in {raw!r}") from exc
    direction = parts[2].lower() if len(parts) == 3 else "higher"
    if direction not in {"higher", "lower"}:
        raise argparse.ArgumentTypeError("Direction must be higher or lower")
    return BreadthRule(metric, threshold, higher_is_bull=(direction == "higher"))


def load_breadth_panel(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Build it with: python scripts/build_breadth_panel.py"
        )
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    return df.sort_values("date").set_index("date")


def build_threshold_regime(
    series: pd.Series,
    *,
    threshold: float,
    higher_is_bull: bool,
    confirm_days: int,
    calendar: pd.DatetimeIndex,
) -> pd.Series:
    """Build a lagged sticky bull/bear panel from a breadth threshold.

    True = bull, False = bear. A regime flip requires `confirm_days`
    consecutive raw bull or raw bear observations, matching the production
    NIFTY-100 close-vs-MA hysteresis style.
    """
    series = series.sort_index().replace([np.inf, -np.inf], np.nan)
    raw_bull = series >= threshold if higher_is_bull else series <= threshold
    raw_bull = raw_bull.where(series.notna())
    n_bull = raw_bull.astype(float).rolling(
        confirm_days, min_periods=confirm_days
    ).sum()

    state = True
    values: list[bool] = []
    for value in n_bull.values:
        if np.isnan(value):
            values.append(state)
            continue
        if state and value == 0:
            state = False
        elif not state and value == confirm_days:
            state = True
        values.append(state)

    regime = pd.Series(values, index=series.index, dtype=bool)
    lagged = regime.shift(1).reindex(calendar).ffill()
    if lagged.isna().any():
        lagged = lagged.astype(object)
        lagged.loc[lagged.isna()] = True
    return lagged.astype(bool)


def metrics_from_result(
    variant_id: str,
    result: dict,
    *,
    regime: pd.Series | None,
    active_start: pd.Timestamp,
    active_end: pd.Timestamp,
    config: dict,
) -> dict:
    eq = result["equity"].copy()
    trades = result["trades"].copy()
    exits = result["exits"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    drawdown = pv / pv.cummax() - 1.0
    max_dd = drawdown.min()
    calmar = cagr / abs(max_dd) if max_dd < 0 else np.nan

    bear_days = None
    bear_frac = None
    if regime is not None:
        active = regime.loc[(regime.index >= active_start) & (regime.index <= active_end)]
        if len(active) > 0:
            bear_days = int((~active.astype(bool)).sum())
            bear_frac = float((~active.astype(bool)).mean())

    return {
        "variant_id": variant_id,
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
        "bear_days": bear_days,
        "bear_frac_pct": round(bear_frac * 100, 2) if bear_frac is not None else None,
    }


def run_one(
    *,
    variant_id: str,
    close_panel: pd.DataFrame,
    trade_panel: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    benchmark_aligned: pd.Series,
    returns_uni: pd.DataFrame,
    entry_dates: pd.DatetimeIndex,
    weekly_dates: pd.DatetimeIndex,
    score_regime: pd.Series,
    overlay_regime: pd.Series | None,
    args: argparse.Namespace,
    config: dict,
    out_dir: Path,
) -> dict | None:
    score_fn = make_om25_tilt_score(
        returns_uni,
        score_regime,
        bull_w_uc=args.bull_w_uc,
        bull_w_cr=args.bull_w_cr,
        bear_w_uc=args.bear_w_uc,
        bear_w_cr=args.bear_w_cr,
        return_filter=not args.no_return_filter,
        lookback=args.lookback,
        min_obs=args.min_obs,
    )
    result = run_strategy(
        close_panel=close_panel,
        trade_panel=trade_panel,
        calendar=calendar,
        benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates,
        weekly_signal_dates=weekly_dates,
        signal_function=score_fn,
        signal_function_args={},
        sma_200_panel=close_panel.rolling(200, min_periods=200).mean(),
        atr_20_panel=close_panel.pct_change().rolling(20).std(),
        top_n=args.top_n,
        exit_buffer=args.exit_buffer,
        max_weight=args.max_weight,
        slippage=args.slippage,
        atr_mult=0.0,
        atr_min_floor=args.drawdown_stop,
        use_trailing_stop=args.drawdown_stop > 0,
        use_dma_exit=False,
        regime_panel=overlay_regime,
        bear_exposure=args.bear_exposure if overlay_regime is not None else 0.0,
        bear_skips_entries=not args.allow_bear_entries,
        initial_capital=args.initial_capital,
    )
    if result is None:
        return None

    equity_path = out_dir / f"{variant_id}_equity.csv"
    result["equity"].to_csv(equity_path, index=False)
    return metrics_from_result(
        variant_id,
        result,
        regime=overlay_regime,
        active_start=entry_dates[0],
        active_end=entry_dates[-1],
        config=config,
    )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="OM25 breadth-regime experiment")
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--breadth-panel", type=Path, default=ROOT / "data/breadth/breadth_daily.csv")
    ap.add_argument("--universe", type=Path, default=ROOT / LOCKED["universe_csv"])
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path, default=ROOT / LOCKED["regime_index_path"])
    ap.add_argument("--start", type=str, default="2016-01-01")
    ap.add_argument("--end", type=str, default=None)
    ap.add_argument("--cadence", choices=["monthly", "biweekly"], default=LOCKED["cadence"])
    ap.add_argument("--preset", choices=["quick", "full"], default="quick")
    ap.add_argument("--rule", action="append", type=parse_rule,
                    help="Custom breadth rule: metric:threshold[:higher|lower]. Can repeat.")
    ap.add_argument("--mode", choices=["score", "overlay", "both", "all"], default="all")
    ap.add_argument("--confirm-days", type=int, default=LOCKED["regime_confirm_days"])
    ap.add_argument("--bear-exposure", type=float, default=0.50)
    ap.add_argument("--allow-bear-entries", action="store_true",
                    help="When using overlay mode, keep buying in bear regimes at scaled weight.")
    ap.add_argument("--top-n", type=int, default=LOCKED["top_n"])
    ap.add_argument("--exit-buffer", type=int, default=LOCKED["exit_buffer"])
    ap.add_argument("--lookback", type=int, default=LOCKED["lookback"])
    ap.add_argument("--min-obs", type=int, default=LOCKED["min_obs"])
    ap.add_argument("--max-weight", type=float, default=LOCKED["max_weight"])
    ap.add_argument("--slippage", type=float, default=LOCKED["slippage"])
    ap.add_argument("--bull-w-uc", type=float, default=LOCKED["bull_w_uc"])
    ap.add_argument("--bull-w-cr", type=float, default=LOCKED["bull_w_cr"])
    ap.add_argument("--bear-w-uc", type=float, default=LOCKED["bear_w_uc"])
    ap.add_argument("--bear-w-cr", type=float, default=LOCKED["bear_w_cr"])
    ap.add_argument("--drawdown-stop", type=float, default=LOCKED["drawdown_stop_pct"])
    ap.add_argument("--no-return-filter", action="store_true")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--output-dir", type=Path, default=None)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or ROOT / "tasks/breadth_atlas/experiments/runs" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] price panels")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark).reindex(calendar).ffill()

    if args.cadence == "biweekly":
        all_entries = biweekly_fridays(calendar)
    else:
        all_entries = monthly_first_trading_day(calendar)
    weekly = fridays(calendar)
    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end) if args.end else calendar[-1]
    entry_dates = all_entries[(all_entries >= start) & (all_entries <= end)]
    weekly_dates = weekly[(weekly >= start) & (weekly <= end)]
    if len(entry_dates) == 0:
        raise RuntimeError("No entry dates in requested date range")

    universe = load_universe(args.universe)
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()
    print(f"       universe={len(cols)} symbols, entries={len(entry_dates)}, weekly={len(weekly_dates)}")

    print("[load] baseline index regime")
    index_regime = build_regime_panel_confirmed(
        args.regime_index,
        LOCKED["regime_ma_window"],
        args.confirm_days,
        calendar=calendar,
    )

    print("[run] baseline index-score regime")
    rows: list[dict] = []
    baseline = run_one(
        variant_id="baseline_index_score",
        close_panel=close_panel,
        trade_panel=trade_panel,
        calendar=calendar,
        benchmark_aligned=benchmark,
        returns_uni=returns_uni,
        entry_dates=entry_dates,
        weekly_dates=weekly_dates,
        score_regime=index_regime,
        overlay_regime=None,
        args=args,
        config={
            "mode": "baseline",
            "metric": "nifty100_close_vs_100dma",
            "threshold": None,
            "higher_is_bull": True,
            "bear_exposure": None,
        },
        out_dir=out_dir,
    )
    if baseline is not None:
        rows.append(baseline)

    rules = args.rule if args.rule else (FULL_RULES if args.preset == "full" else QUICK_RULES)
    breadth = load_breadth_panel(args.breadth_panel)
    modes = ["score", "overlay", "both"] if args.mode == "all" else [args.mode]

    for rule in rules:
        if rule.metric not in breadth.columns:
            raise ValueError(f"{rule.metric!r} not found in {args.breadth_panel}")
        breadth_regime = build_threshold_regime(
            breadth[rule.metric],
            threshold=rule.threshold,
            higher_is_bull=rule.higher_is_bull,
            confirm_days=args.confirm_days,
            calendar=calendar,
        )
        for mode in modes:
            variant_id = f"{mode}_{rule.slug}"
            print(f"[run] {variant_id}")
            score_regime = breadth_regime if mode in {"score", "both"} else index_regime
            overlay_regime = breadth_regime if mode in {"overlay", "both"} else None
            row = run_one(
                variant_id=variant_id,
                close_panel=close_panel,
                trade_panel=trade_panel,
                calendar=calendar,
                benchmark_aligned=benchmark,
                returns_uni=returns_uni,
                entry_dates=entry_dates,
                weekly_dates=weekly_dates,
                score_regime=score_regime,
                overlay_regime=overlay_regime,
                args=args,
                config={
                    "mode": mode,
                    "metric": rule.metric,
                    "threshold": rule.threshold,
                    "higher_is_bull": rule.higher_is_bull,
                    "bear_exposure": args.bear_exposure if mode in {"overlay", "both"} else None,
                },
                out_dir=out_dir,
            )
            if row is not None:
                rows.append(row)

    summary = pd.DataFrame(rows)
    summary = summary.sort_values(
        ["sharpe_rf5", "cagr_pct", "max_dd_pct"],
        ascending=[False, False, False],
    )
    summary.to_csv(out_dir / "summary.csv", index=False)

    config = vars(args).copy()
    config["prices_dir"] = str(args.prices_dir)
    config["breadth_panel"] = str(args.breadth_panel)
    config["universe"] = str(args.universe)
    config["benchmark"] = str(args.benchmark)
    config["regime_index"] = str(args.regime_index)
    config["output_dir"] = str(out_dir)
    config["rule"] = [r.__dict__ for r in rules]
    (out_dir / "config.json").write_text(json.dumps(config, indent=2, default=str))

    show_cols = [
        "variant_id",
        "mode",
        "metric",
        "threshold",
        "cagr_pct",
        "sharpe_rf5",
        "max_dd_pct",
        "calmar",
        "bear_frac_pct",
    ]
    print("\n=== Top variants by Sharpe ===")
    print(summary[show_cols].head(12).to_string(index=False))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
