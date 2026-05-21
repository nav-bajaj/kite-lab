"""Apply the 3-state breadth regime as a SCORE-TILT (not exposure) to
TL25, L6, and COMBO. Mirrors the OM25 anchor design: 100% exposure always,
20% drawdown stop where production has it, score weights cycle by state.

Per-portfolio state-tilt design:

  TL25 (Persistence / Drawdown / Momentum):
      bull : 0.40 / 0.20 / 0.40   (production A3)
      bear : 0.20 / 0.60 / 0.20   (defensive — drawdown-heavy)
      deep : 0.00 / 0.00 / 1.00   (aggressive — pure momentum)

  L6 (vol-adjusted momentum, single dimension):
      bull : vol_power = 1.0   (production)
      bear : vol_power = 2.0   (defensive — penalize volatile names)
      deep : vol_power = 0.0   (aggressive — raw momentum)

  COMBO (50/50 L6 + OM25 dedup-blended):
      bull : L6 vp=1.0 + OM25 UC/CR 50/50   (production)
      bear : L6 vp=2.0 + OM25 CR-only
      deep : L6 vp=0.0 + OM25 UC-only

Tested on both NSE 500 and Nifty 250 universes. Each portfolio gets a
production-baseline run (no regime tilt — whatever the live config does)
and a 3-state-breadth run.

Breadth metric: avg_dist_from_200dma (the consistent winner from the OM25 sweep).
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
    biweekly_fridays, fridays, thursdays, run_strategy,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402

from scripts.tl25_v3 import V3_LOCKED as TL25_LOCKED, build_tl25_panels  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6_BASELINE, build_momentum_panels,
    lookback_months_to_days,
)
from scripts.combo_defensive import LOCKED as COMBO_LOCKED, make_combo_score_fn  # noqa: E402
from scripts.om25_v3 import (  # noqa: E402
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed,
)

from tasks.breadth_atlas.experiments.om25_three_state_experiment import (  # noqa: E402
    STATE_BULL, STATE_BEAR, STATE_DEEP, WINDOWS, METRIC_THRESHOLDS,
    build_three_state_regime, load_breadth_panel,
    make_three_state_score as make_om25_3state_score,
)


BREADTH_METRIC = "avg_dist_from_200dma"

# Per-portfolio state-tilt parameters

TL25_WEIGHTS = {
    STATE_BULL: (0.40, 0.20, 0.40),
    STATE_BEAR: (0.20, 0.60, 0.20),
    STATE_DEEP: (0.00, 0.00, 1.00),
}

L6_VOL_POWERS = {
    STATE_BULL: 1.0,
    STATE_BEAR: 2.0,
    STATE_DEEP: 0.0,
}

# OM25 weights used inside COMBO's OM25 component
OM25_COMBO_WEIGHTS = {
    STATE_BULL: (0.5, 0.5),
    STATE_BEAR: (0.0, 1.0),
    STATE_DEEP: (1.0, 0.0),
}

UNIVERSES = {
    "NSE500":   "data/static/nse500_universe.csv",
    "Nifty250": "data/static/nifty250_universe.csv",
}


# ============================================================
# 3-state score factories
# ============================================================

def make_tl25_3state_score(panels: dict, regime: pd.Series, weights: dict):
    """TL25 score with weights cycling by 3-state breadth regime.

    Eligibility filter is the same in every state (production semantics).
    """
    eligibility = panels["eligibility"]
    persistence = panels["persistence"]
    drawdown = panels["drawdown"]
    momentum_raw = panels["momentum_raw"]

    def score_fn(signal_date, **_):
        if signal_date not in eligibility.index:
            return pd.Series(dtype=float)
        state = regime.get(signal_date, STATE_BULL)
        wp, wd, wm = weights.get(state, weights[STATE_BULL])
        wsum = wp + wd + wm
        if wsum <= 0:
            return pd.Series(dtype=float)
        wp_n, wd_n, wm_n = wp / wsum, wd / wsum, wm / wsum

        elig_row = eligibility.loc[signal_date]
        if not elig_row.any():
            return pd.Series(dtype=float)
        persist_row = persistence.loc[signal_date].fillna(0)
        dd_row = drawdown.loc[signal_date].fillna(0)
        mom_raw_row = momentum_raw.loc[signal_date]

        mom_eligible = mom_raw_row.where(elig_row).dropna()
        if len(mom_eligible) > 1 and wm > 0:
            mom_ranked = mom_eligible.rank(method="average", ascending=True)
            mom_pct = (mom_ranked - 1) / (len(mom_ranked) - 1)
            mom_pct_full = pd.Series(0.0, index=elig_row.index)
            mom_pct_full.loc[mom_pct.index] = mom_pct.values
        else:
            mom_pct_full = pd.Series(0.0, index=elig_row.index)

        weighted = (wp_n * persist_row + wd_n * dd_row + wm_n * mom_pct_full)
        return weighted.where(elig_row)

    return score_fn


def make_l6_3state_score(close_panel: pd.DataFrame, regime: pd.Series,
                          vol_powers: dict, *, lookback_days: int,
                          skip_days: int, vol_floor: float,
                          cross_sectional_zscore: bool = True):
    """L6 score with vol_power cycling by 3-state breadth regime."""
    panels = build_momentum_panels(
        close_panel, lookback_days=lookback_days, skip_days=skip_days,
    )
    momentum = panels["momentum"]
    realized_vol = panels["realized_vol"]

    def score_fn(signal_date, **_):
        if signal_date not in momentum.index:
            return pd.Series(dtype=float)
        state = regime.get(signal_date, STATE_BULL)
        vp = vol_powers.get(state, vol_powers[STATE_BULL])

        mom_row = momentum.loc[signal_date]
        vol_row = realized_vol.loc[signal_date]
        denom = vol_row.clip(lower=vol_floor)
        if abs(vp - 1.0) > 1e-9:
            denom = denom.pow(vp)
        score = mom_row / denom
        score = score.replace([np.inf, -np.inf], np.nan).dropna()
        if score.empty:
            return score
        if cross_sectional_zscore and len(score) > 1:
            mu = score.mean(); sd = score.std()
            if sd is not None and sd > 0:
                score = (score - mu) / sd
        return score

    return score_fn


def make_combo_3state_score(close_panel: pd.DataFrame, regime: pd.Series,
                             universe_path: Path, args):
    """COMBO score: priority-deduped L6(3state) + OM25(3state)."""
    universe = load_universe(universe_path)
    cols = [s for s in close_panel.columns if s in universe]

    l6_score = make_l6_3state_score(
        close_panel[cols], regime, L6_VOL_POWERS,
        lookback_days=lookback_months_to_days(COMBO_LOCKED["l6_lookback_months"]),
        skip_days=COMBO_LOCKED["l6_skip_days"],
        vol_floor=COMBO_LOCKED["l6_vol_floor"],
        cross_sectional_zscore=True,
    )
    om25_returns = close_panel[cols].pct_change()
    om25_score = make_om25_3state_score(
        om25_returns, regime, weights=OM25_COMBO_WEIGHTS,
        return_filter=COMBO_LOCKED["om25_return_filter"],
        lookback=COMBO_LOCKED["om25_lookback"],
        min_obs=COMBO_LOCKED["om25_min_obs"],
    )
    return make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=COMBO_LOCKED["n_per_strategy"],
    )


# ============================================================
# Baseline (production) score builders — no regime tilt
# ============================================================

def make_tl25_baseline_score(panels: dict):
    return make_tl25_3state_score(
        panels,
        regime=pd.Series(dtype=object),    # empty -> always falls back
        weights={STATE_BULL: (TL25_LOCKED["w_persistence"],
                              TL25_LOCKED["w_drawdown"],
                              TL25_LOCKED["w_momentum"])},
    )


def make_l6_baseline_score(close_panel: pd.DataFrame):
    return make_l6_3state_score(
        close_panel, regime=pd.Series(dtype=object),
        vol_powers={STATE_BULL: L6_BASELINE["vol_power"]},
        lookback_days=lookback_months_to_days(L6_BASELINE["lookback_months"]),
        skip_days=L6_BASELINE["skip_days"],
        vol_floor=L6_BASELINE["vol_floor"],
        cross_sectional_zscore=L6_BASELINE["cross_sectional_zscore"],
    )


def make_combo_baseline_score(close_panel: pd.DataFrame, universe_path: Path,
                               index_regime: pd.Series):
    """Production COMBO score: bull/bear UC/CR via NIFTY-100 close-vs-100dma."""
    universe = load_universe(universe_path)
    cols = [s for s in close_panel.columns if s in universe]
    # L6 component — no regime
    l6_score = make_l6_3state_score(
        close_panel[cols], regime=pd.Series(dtype=object),
        vol_powers={STATE_BULL: COMBO_LOCKED["l6_vol_power"]},
        lookback_days=lookback_months_to_days(COMBO_LOCKED["l6_lookback_months"]),
        skip_days=COMBO_LOCKED["l6_skip_days"],
        vol_floor=COMBO_LOCKED["l6_vol_floor"],
        cross_sectional_zscore=True,
    )
    # OM25 component — bull/bear tilt via NIFTY-100 2-state index regime
    # Reuse make_om25_3state_score with a 2-key weight map keyed by True/False
    # via translation: convert bool regime to "bull"/"bear" labels.
    def _bool_to_label(b):
        if pd.isna(b):
            return STATE_BULL
        return STATE_BULL if bool(b) else STATE_BEAR
    bull_bear_regime = index_regime.map(_bool_to_label).astype(object)
    om25_returns = close_panel[cols].pct_change()
    om25_weights = {
        STATE_BULL: (COMBO_LOCKED["om25_bull_w_uc"], COMBO_LOCKED["om25_bull_w_cr"]),
        STATE_BEAR: (COMBO_LOCKED["om25_bear_w_uc"], COMBO_LOCKED["om25_bear_w_cr"]),
    }
    om25_score = make_om25_3state_score(
        om25_returns, bull_bear_regime, weights=om25_weights,
        return_filter=COMBO_LOCKED["om25_return_filter"],
        lookback=COMBO_LOCKED["om25_lookback"],
        min_obs=COMBO_LOCKED["om25_min_obs"],
    )
    return make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=COMBO_LOCKED["n_per_strategy"],
    )


# ============================================================
# Engine config per portfolio
# ============================================================

def portfolio_engine_cfg(portfolio: str) -> dict:
    """Returns engine kwargs for run_strategy — production-faithful but
    100% exposure throughout (no regime overlay).
    """
    if portfolio == "TL25":
        return dict(
            top_n=TL25_LOCKED["top_n"], exit_buffer=TL25_LOCKED["exit_buffer"],
            max_weight=TL25_LOCKED["max_weight"], slippage=TL25_LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=TL25_LOCKED["atr_min_floor"],
            use_trailing_stop=TL25_LOCKED["use_trailing_stop"], use_dma_exit=False,
            weekly_rank_check=TL25_LOCKED.get("weekly_rank_check", False),
            min_hold_days=0,
        )
    if portfolio == "L6":
        return dict(
            top_n=L6_BASELINE["top_n"], exit_buffer=L6_BASELINE["exit_buffer"],
            max_weight=L6_BASELINE["max_weight"], slippage=L6_BASELINE["slippage"],
            atr_mult=0.0, atr_min_floor=L6_BASELINE["drawdown_stop"],
            use_trailing_stop=L6_BASELINE["drawdown_stop"] > 0.0,
            use_dma_exit=False, weekly_rank_check=False,
            min_hold_days=L6_BASELINE["min_hold_days"],
        )
    if portfolio == "COMBO":
        return dict(
            top_n=COMBO_LOCKED["top_n"], exit_buffer=COMBO_LOCKED["exit_buffer"],
            max_weight=COMBO_LOCKED["max_weight"], slippage=COMBO_LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=0.20,
            use_trailing_stop=True, use_dma_exit=False, weekly_rank_check=False,
            min_hold_days=COMBO_LOCKED["min_hold_days"],
        )
    raise ValueError(portfolio)


def entries_for(portfolio: str, calendar, start, end):
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    if portfolio == "L6":
        all_e = thursdays(calendar)
        weekly = thursdays(calendar)
    else:
        all_e = biweekly_fridays(calendar)
        weekly = fridays(calendar)
    return (all_e[(all_e >= s) & (all_e <= e)],
            weekly[(weekly >= s) & (weekly <= e)])


# ============================================================
# Run one variant
# ============================================================

def collect_metrics(result, label, config, active_start, active_end) -> dict:
    if result is None:
        return {"label": label, **config, "error": "no_result"}
    eq = result["equity"].copy()
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
    dd = (pv / pv.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd < 0 else np.nan
    trades = result["trades"]
    return {
        "label": label, **config,
        "start": str(pv.index[0].date()), "end": str(pv.index[-1].date()),
        "years": round(years, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe_rf5": round(sharpe, 3),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(dd * 100, 2),
        "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None,
        "n_buys": int((trades["side"] == "BUY").sum()) if not trades.empty else 0,
        "n_sells": int((trades["side"] == "SELL").sum()) if not trades.empty else 0,
    }


def run_one(*, portfolio, label, score_fn, close_panel, trade_panel, calendar,
            benchmark, entry_dates, weekly_dates, sma_200_panel, atr_20_panel,
            args, config, active_start, active_end, out_dir):
    eng = portfolio_engine_cfg(portfolio)
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
        regime_panel=None, bear_exposure=0.0, bear_skips_entries=False,
        initial_capital=args.initial_capital,
        **eng,
    )
    if res is not None:
        res["equity"].to_csv(out_dir / f"{label}_equity.csv", index=False)
    return collect_metrics(res, label, config, active_start, active_end)


# ============================================================
# Main
# ============================================================

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--breadth-panel", type=Path, default=ROOT / "data/breadth/breadth_daily.csv")
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path, default=ROOT / "indices_data_historical/NIFTY_100.csv")
    ap.add_argument("--portfolios", nargs="+", default=["TL25", "L6", "COMBO"])
    ap.add_argument("--universes", nargs="+", default=list(UNIVERSES.keys()))
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--output-dir", type=Path, default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or ROOT / "tasks/breadth_atlas/experiments/portfolios_3state" / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] price panels")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark).reindex(calendar).ffill()
    sma_200_panel = close_panel.rolling(200, min_periods=200).mean()
    atr_20_panel = close_panel.pct_change().rolling(20).std()

    # 2-state NIFTY-100 regime (for COMBO baseline only)
    index_regime = build_regime_panel_confirmed(
        args.regime_index, OM25_LOCKED["regime_ma_window"],
        OM25_LOCKED["regime_confirm_days"], calendar=calendar,
    )

    # 3-state breadth regime
    breadth = load_breadth_panel(args.breadth_panel)
    bear_in, bear_out, deep_in, deep_out, higher = METRIC_THRESHOLDS[BREADTH_METRIC]
    breadth_regime = build_three_state_regime(
        breadth[BREADTH_METRIC],
        bear_entry=bear_in, bear_exit=bear_out,
        deep_entry=deep_in, deep_exit=deep_out,
        higher_is_bull=higher, confirm_days=3, calendar=calendar,
    )

    rows: list[dict] = []
    for univ_label in args.universes:
        univ_path = ROOT / UNIVERSES[univ_label]
        universe = load_universe(univ_path)
        univ_cols = [s for s in close_panel.columns if s in universe]
        print(f"\n=== Universe: {univ_label} ({len(univ_cols)} symbols) ===")

        # Pre-build per-portfolio score functions for this universe
        score_builders = {}
        if "TL25" in args.portfolios:
            panels_full = build_tl25_panels(close_panel[univ_cols])
            score_builders["TL25"] = {
                "baseline": make_tl25_baseline_score(panels_full),
                "breadth3state": make_tl25_3state_score(panels_full, breadth_regime, TL25_WEIGHTS),
            }
        if "L6" in args.portfolios:
            score_builders["L6"] = {
                "baseline": make_l6_baseline_score(close_panel[univ_cols]),
                "breadth3state": make_l6_3state_score(
                    close_panel[univ_cols], breadth_regime, L6_VOL_POWERS,
                    lookback_days=lookback_months_to_days(L6_BASELINE["lookback_months"]),
                    skip_days=L6_BASELINE["skip_days"],
                    vol_floor=L6_BASELINE["vol_floor"],
                    cross_sectional_zscore=L6_BASELINE["cross_sectional_zscore"],
                ),
            }
        if "COMBO" in args.portfolios:
            score_builders["COMBO"] = {
                "baseline": make_combo_baseline_score(close_panel, univ_path, index_regime),
                "breadth3state": make_combo_3state_score(close_panel, breadth_regime, univ_path, args),
            }

        for portfolio in args.portfolios:
            for window_name, (start_s, end_s) in WINDOWS.items():
                w_start, w_end = pd.Timestamp(start_s), pd.Timestamp(end_s)
                entry_dates, weekly_dates = entries_for(portfolio, calendar, w_start, w_end)
                if len(entry_dates) == 0:
                    continue
                for variant in ["baseline", "breadth3state"]:
                    label = f"{univ_label}_{portfolio}_{window_name}_{variant}"
                    print(f"  {label}")
                    rows.append(run_one(
                        portfolio=portfolio, label=label,
                        score_fn=score_builders[portfolio][variant],
                        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
                        benchmark=benchmark,
                        entry_dates=entry_dates, weekly_dates=weekly_dates,
                        sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
                        args=args,
                        config={"universe": univ_label, "portfolio": portfolio,
                                "window": window_name, "variant": variant,
                                "metric": BREADTH_METRIC if variant == "breadth3state" else None},
                        active_start=entry_dates[0], active_end=entry_dates[-1],
                        out_dir=out_dir,
                    ))

    summary = pd.DataFrame(rows)
    summary.to_csv(out_dir / "summary.csv", index=False)
    (out_dir / "config.json").write_text(json.dumps({
        "breadth_metric": BREADTH_METRIC,
        "metric_thresholds": METRIC_THRESHOLDS[BREADTH_METRIC],
        "tl25_weights": {k: list(v) for k, v in TL25_WEIGHTS.items()},
        "l6_vol_powers": L6_VOL_POWERS,
        "om25_combo_weights": {k: list(v) for k, v in OM25_COMBO_WEIGHTS.items()},
        "windows": WINDOWS,
        "portfolios": list(args.portfolios),
        "universes": list(args.universes),
    }, indent=2, default=str))

    show_cols = ["universe", "portfolio", "window", "variant",
                 "cagr_pct", "sharpe_rf5", "max_dd_pct", "calmar"]
    print("\n=== Results ===")
    print(summary[show_cols].to_string(index=False))
    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
