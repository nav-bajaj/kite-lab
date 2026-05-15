"""OM25 US retune — IS=2009-2016 / OOS=2017-2026 against US equities.

Mirrors tasks/om25/experiments/_om25_oos_retune.py methodology but on US data.
Adds an explicit Stage 3 that sweeps regime-tilt overlay parameters (SPY-100-DMA
based) on top of the Stage-2 winners — one per cadence (monthly + biweekly).

Selection: highest IS Sharpe. OOS only inspected after winner is chosen.

Flags:
  --stop-after-stage N    Stop after Stage N (1, 2, or 3; default 3)
  --resume-dir DIR        Reuse prior stage1.csv (and stage2.csv if present)
                           from DIR; only the stages still missing will run.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (  # noqa: E402
    run_strategy, fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts.om25_v3 import build_regime_panel_confirmed  # noqa: E402
from scripts.multi_window_oos_eval import period_metrics  # noqa: E402


PRICES_DIR = ROOT / "us_equities_data"
UNIVERSE = ROOT / "data/static/us_equities_universe.csv"
BENCHMARK = ROOT / "data/benchmarks/spy.csv"
REGIME_IDX = ROOT / "data/benchmarks/spy.csv"

IS_START = pd.Timestamp("2009-09-01")
IS_END = pd.Timestamp("2016-12-31")

US_WINDOWS = [
    ("IS",       "2009-09-01", "2016-12-31"),
    ("OOS_A",    "2017-01-01", "2019-12-31"),
    ("OOS_B",    "2020-01-01", "2022-12-31"),
    ("OOS_C",    "2023-01-01", "2026-05-13"),
    ("OOS_full", "2017-01-01", "2026-05-13"),
]


# ---------------------------------------------------------------------------
# Score factory — supports optional regime tilt
# ---------------------------------------------------------------------------

def make_om25_score(returns_universe, *,
                    w_uc=0.5, w_cr=0.5,
                    return_filter=False,
                    lookback=252, min_obs=220,
                    skip_days=0,
                    regime_panel=None,
                    bear_w_uc=None, bear_w_cr=None):
    """OM25 score with optional regime-tilted bull/bear weights.

    When regime_panel + bear_w_* are provided, weights flip per signal date.
    When regime_panel is None, bull weights apply unconditionally (v2-style).

    `skip_days` excludes the most recent N trading days from the scoring window
    (Jegadeesh-Titman 12-1 style). e.g. lookback=252, skip_days=21 measures
    UC/CR over the window [-273, -21] rather than [-252, 0].
    """
    if w_uc <= 0 and w_cr <= 0:
        raise ValueError("at least one of w_uc, w_cr must be > 0")
    if skip_days < 0:
        raise ValueError("skip_days must be >= 0")
    has_tilt = (regime_panel is not None and
                bear_w_uc is not None and bear_w_cr is not None)

    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback + skip_days:
            return pd.Series(dtype=float)

        if has_tilt:
            rv = regime_panel.get(signal_date, True)
            is_bull = bool(rv) if rv is not None else True
            wu, wc = (w_uc, w_cr) if is_bull else (bear_w_uc, bear_w_cr)
        else:
            wu, wc = w_uc, w_cr
        if wu + wc <= 0:
            return pd.Series(dtype=float)
        w_sum = wu + wc
        wu_n, wc_n = wu / w_sum, wc / w_sum

        end_idx = idx - skip_days + 1
        start_idx = end_idx - lookback
        window = returns_universe.iloc[start_idx:end_idx]
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
        return wu_n * up_pct + wc_n * cr_pct
    return score_fn


# ---------------------------------------------------------------------------
# Single-config runner
# ---------------------------------------------------------------------------

def run_config(*, ctx, cfg: dict, is_only: bool = True,
               regime_panel=None,
               bear_w_uc=None, bear_w_cr=None) -> dict:
    if cfg["cadence"] == "monthly":
        entry_all = ctx["monthly_first"]
    elif cfg["cadence"] == "biweekly":
        entry_all = ctx["biweekly_fri"]
    else:
        raise ValueError(cfg["cadence"])

    skip_days = int(cfg.get("skip_days", 0))
    min_date = ctx["close_panel"].index[cfg["lookback"] + skip_days]
    entry_filt = entry_all[entry_all >= min_date]
    if is_only:
        entry_filt = entry_filt[entry_filt <= IS_END]
    entry_filt = entry_filt[entry_filt >= IS_START]

    score_fn = make_om25_score(
        ctx["returns_uni"],
        w_uc=cfg["w_uc"], w_cr=cfg["w_cr"],
        return_filter=cfg["return_filter"],
        lookback=cfg["lookback"], min_obs=cfg["min_obs"],
        skip_days=skip_days,
        regime_panel=regime_panel,
        bear_w_uc=bear_w_uc, bear_w_cr=bear_w_cr,
    )
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entry_filt,
        weekly_signal_dates=ctx["weekly_filt_full"],
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        atr_mult=cfg["atr_mult"], atr_min_floor=cfg["atr_min_floor"],
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=cfg["atr_mult"] > 0 or cfg["atr_min_floor"] > 0,
    )
    if res is None:
        return {**cfg, "status": "no_signals"}

    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    is_m = period_metrics(eq, "IS_tune", IS_START, IS_END)
    out = {**cfg, "status": "ok"}
    for k in ("cagr_pct", "sharpe", "vol_pct", "max_dd_pct"):
        out[f"is_{k}"] = is_m.get(k)
    out["_equity"] = eq
    return out


# ---------------------------------------------------------------------------
# Stage 1 grid (score variants)
# ---------------------------------------------------------------------------

STAGE1_BASELINE = dict(
    lookback=252, min_obs=220,
    top_n=25, exit_buffer=15,
    cadence="monthly",
    atr_mult=0.0, atr_min_floor=0.0,
)

STAGE1_GRID = []
for (w_uc, w_cr) in [(1.0, 0.0), (0.7, 0.3), (0.5, 0.5), (0.3, 0.7), (0.0, 1.0)]:
    for return_filter in (False, True):
        for min_obs in (220, 150):
            STAGE1_GRID.append(STAGE1_BASELINE | dict(
                w_uc=w_uc, w_cr=w_cr,
                return_filter=return_filter,
                min_obs=min_obs,
            ))


def stage2_grid_for_winner(winner: dict) -> list:
    """~15 stage-2 configs around a stage-1 winner."""
    base = {k: winner[k] for k in (
        "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
        "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
    )}
    grid = []
    seen = set()

    def add(cfg):
        key = tuple(sorted((k, v) for k, v in cfg.items()
                             if k != "atr_min_floor" or cfg["atr_mult"] > 0))
        if key in seen:
            return
        seen.add(key)
        grid.append(cfg)

    for lb in (126, 189, 252, 378):
        scaled_min_obs = int(lb * 220 / 252)
        add(base | dict(lookback=lb, min_obs=scaled_min_obs))
    for tn, bf in [(20, 10), (20, 15), (25, 10), (25, 20), (30, 15), (30, 20)]:
        add(base | dict(top_n=tn, exit_buffer=bf))
    for cad in ("monthly", "biweekly"):
        add(base | dict(cadence=cad))
    for atr in (0.0, 4.0, 5.0):
        add(base | dict(atr_mult=atr, atr_min_floor=0.0))
    return grid


# ---------------------------------------------------------------------------
# Stage 3 — regime tilt overlay
# ---------------------------------------------------------------------------

def stage3_grid_for_winner(winner: dict) -> list:
    """36 regime-tilt configs around a base score winner."""
    base = {k: winner[k] for k in (
        "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
        "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
    )}
    grid = []
    for ma in (50, 100, 150, 200):
        for confirm in (1, 3, 5):
            for (bear_w_uc, bear_w_cr) in [(0.0, 1.0), (0.25, 0.75), (0.5, 0.5)]:
                grid.append({
                    **base,
                    "regime_ma": ma,
                    "regime_confirm": confirm,
                    "bear_w_uc": bear_w_uc,
                    "bear_w_cr": bear_w_cr,
                })
    return grid


# ---------------------------------------------------------------------------
# Stage 4 — skip_days (Jegadeesh-Titman 12-1 style)
# ---------------------------------------------------------------------------

SKIP_GRID = [0, 5, 21, 42]  # 0d, 1w, 1mo, 2mo


def stage4_configs_for_winners(winners: list) -> list:
    """Sweep skip_days on each base winner. Returns list of cfg dicts."""
    out = []
    for base in winners:
        for sd in SKIP_GRID:
            c = {k: base[k] for k in (
                "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
                "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
            )}
            # Pull regime params if the base came from Stage 3
            for k in ("regime_ma", "regime_confirm", "bear_w_uc", "bear_w_cr"):
                if k in base and pd.notna(base.get(k)):
                    c[k] = base[k]
            c["skip_days"] = sd
            c["_base_cadence"] = base["cadence"]
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Multi-window eval (post-winner)
# ---------------------------------------------------------------------------

def evaluate_winner_windows(eq: pd.DataFrame, windows=US_WINDOWS) -> pd.DataFrame:
    rows = []
    for label, start, end in windows:
        rows.append({"window": label, **period_metrics(eq, label, start, end)})
    return pd.DataFrame(rows)


def passes_us_criteria(window_df: pd.DataFrame) -> tuple[bool, list[str]]:
    failures = []

    def metric(label, key):
        sub = window_df[window_df["window"] == label]
        return float(sub.iloc[0][key]) if not sub.empty and key in sub.columns else None

    is_s = metric("IS", "sharpe")
    oof_s = metric("OOS_full", "sharpe")
    oa_s = metric("OOS_A", "sharpe")
    ob_s = metric("OOS_B", "sharpe")
    oc_s = metric("OOS_C", "sharpe")
    oof_dd = metric("OOS_full", "max_dd_pct")
    if is_s is None or is_s < 1.0:
        failures.append(f"IS Sharpe {is_s} < 1.0")
    if oof_s is None or oof_s < 1.0:
        failures.append(f"OOS-full Sharpe {oof_s} < 1.0")
    for lbl, val in [("OOS_A", oa_s), ("OOS_B", ob_s), ("OOS_C", oc_s)]:
        if val is None or val < 0.7:
            failures.append(f"{lbl} Sharpe {val} < 0.7")
    if oof_dd is None or oof_dd < -45.0:
        failures.append(f"OOS-full Max DD {oof_dd}% > -45%")
    return (len(failures) == 0, failures)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stop-after-stage", type=int, default=4,
                    choices=(1, 2, 3, 4))
    ap.add_argument("--resume-dir", type=Path, default=None,
                    help="Reuse stage1.csv / stage2.csv from this dir if present")
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / f"experiments/oos_retune/{ts}_om25_us"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")
    if args.resume_dir:
        print(f"[resume] reading prior stages from {args.resume_dir}")

    print(f"\n[load] prices from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_universe(UNIVERSE)
    cols = [c for c in close_panel.columns if c in universe]
    close_uni = close_panel[cols]
    returns_uni = close_uni.pct_change()
    print(f"[univ] {len(cols)} symbols, "
          f"{calendar[0].date()} -> {calendar[-1].date()}")

    weekly_fri = fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt_full = weekly_fri[weekly_fri >= calendar[252]]

    ctx = dict(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned, sma_200=sma_200, atr_20=atr_20,
        close_uni=close_uni, returns_uni=returns_uni,
        weekly_filt_full=weekly_filt_full,
        monthly_first=monthly_first, biweekly_fri=biweekly_fri,
    )

    # ---- Stage 1 ----
    prior_stage1 = args.resume_dir / "stage1.csv" if args.resume_dir else None
    if prior_stage1 and prior_stage1.exists():
        df1 = pd.read_csv(prior_stage1).sort_values("is_sharpe", ascending=False)
        df1.to_csv(out_dir / "stage1.csv", index=False)
        print(f"\n[stage1] LOADED {len(df1)} configs from {prior_stage1}")
    else:
        print(f"\n{'='*78}\nStage 1: {len(STAGE1_GRID)} score variants (IS Sharpe selection)\n{'='*78}")
        rows1 = []
        t0 = time.time()
        for i, cfg in enumerate(STAGE1_GRID, 1):
            out = run_config(ctx=ctx, cfg=cfg, is_only=True)
            out.pop("_equity", None)
            rows1.append(out)
            elapsed = time.time() - t0
            print(f"  [{i:2d}/{len(STAGE1_GRID)}] "
                  f"uc={cfg['w_uc']:.1f}/cr={cfg['w_cr']:.1f} "
                  f"filt={int(cfg['return_filter'])} mobs={cfg['min_obs']}   "
                  f"Sharpe={out.get('is_sharpe', 0):.2f}  "
                  f"CAGR={out.get('is_cagr_pct', 0):6.2f}%  "
                  f"DD={out.get('is_max_dd_pct', 0):6.2f}%  ({elapsed:.0f}s)")
        df1 = pd.DataFrame(rows1).sort_values("is_sharpe", ascending=False)
        df1.to_csv(out_dir / "stage1.csv", index=False)
    print(f"\n[stage1] top 5 by IS Sharpe:")
    print(df1.head(5)[["w_uc", "w_cr", "return_filter", "min_obs",
                       "is_sharpe", "is_cagr_pct", "is_max_dd_pct"]]
          .to_string(index=False))

    top3 = df1.head(3).to_dict("records")

    if args.stop_after_stage < 2:
        print(f"\n[stop] --stop-after-stage 1 → halting after Stage 1.")
        return 0

    # ---- Stage 2 ----
    prior_stage2 = args.resume_dir / "stage2.csv" if args.resume_dir else None
    if prior_stage2 and prior_stage2.exists():
        df2 = pd.read_csv(prior_stage2).sort_values("is_sharpe", ascending=False)
        df2.to_csv(out_dir / "stage2.csv", index=False)
        print(f"\n[stage2] LOADED {len(df2)} configs from {prior_stage2}")
    else:
        print(f"\n{'='*78}\nStage 2: sub-grids around top-3 stage-1 winners\n{'='*78}")
        s2_configs, seen_keys = [], set()
        for w in top3:
            for c in stage2_grid_for_winner(w):
                key = tuple(sorted(c.items()))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                s2_configs.append(c)
        print(f"  total stage-2 configs (deduped): {len(s2_configs)}")

        rows2, t0 = [], time.time()
        for i, cfg in enumerate(s2_configs, 1):
            out = run_config(ctx=ctx, cfg=cfg, is_only=True)
            out.pop("_equity", None)
            rows2.append(out)
            elapsed = time.time() - t0
            if i % 5 == 0 or i == len(s2_configs):
                print(f"  [{i:2d}/{len(s2_configs)}] "
                      f"lb={cfg['lookback']} top_n={cfg['top_n']} "
                      f"buf={cfg['exit_buffer']} cad={cfg['cadence'][:3]} "
                      f"atr={cfg['atr_mult']:.0f}   "
                      f"Sharpe={out.get('is_sharpe', 0):.2f}  "
                      f"CAGR={out.get('is_cagr_pct', 0):6.2f}%  ({elapsed:.0f}s)")

        df2 = pd.DataFrame(rows2).sort_values("is_sharpe", ascending=False)
        df2.to_csv(out_dir / "stage2.csv", index=False)

    df12 = pd.concat([df1, df2], ignore_index=True).sort_values(
        "is_sharpe", ascending=False)
    df12.to_csv(out_dir / "stage12.csv", index=False)

    print(f"\n[stage1+2] top 5 by IS Sharpe (overall):")
    print(df12.head(5)[["lookback", "w_uc", "w_cr", "return_filter",
                        "top_n", "exit_buffer", "cadence", "atr_mult",
                        "is_sharpe", "is_cagr_pct", "is_max_dd_pct"]]
          .to_string(index=False))

    # Pick top-1 per cadence — feed BOTH into Stage 3
    base_winners = []
    for cad in ("monthly", "biweekly"):
        sub = df12[df12["cadence"] == cad].sort_values("is_sharpe", ascending=False)
        if not sub.empty:
            base_winners.append(sub.iloc[0].to_dict())
    print(f"\n[stage1+2] top-1 by cadence (feed → Stage 3):")
    for w in base_winners:
        print(f"  {w['cadence']:8s} lb={w['lookback']:3d} "
              f"top_n={w['top_n']} buf={w['exit_buffer']:2d} "
              f"atr={w['atr_mult']:.0f}  "
              f"Sharpe={w['is_sharpe']:.2f}  CAGR={w['is_cagr_pct']:.2f}%  "
              f"DD={w['is_max_dd_pct']:.2f}%")

    base_winner = df12.iloc[0].to_dict()  # for downstream "best overall" usage

    if args.stop_after_stage < 3:
        print(f"\n[stop] --stop-after-stage 2 → halting after Stage 2.")
        return 0

    # ---- Stage 3: regime tilt overlay, swept on BOTH per-cadence winners ----
    prior_stage3 = args.resume_dir / "stage3.csv" if args.resume_dir else None
    if prior_stage3 and prior_stage3.exists():
        df3 = pd.read_csv(prior_stage3).sort_values("is_sharpe", ascending=False)
        df3.to_csv(out_dir / "stage3.csv", index=False)
        print(f"\n[stage3] LOADED {len(df3)} configs from {prior_stage3}")
        eligible_bases = [w for w in base_winners if w.get("is_sharpe", 0) >= 1.0]
    elif not [w for w in base_winners if w.get("is_sharpe", 0) >= 1.0]:
        eligible_bases = []
        print(f"\n[stage3] SKIPPED — no base winner clears IS Sharpe ≥ 1.0")
        df3 = pd.DataFrame()
    else:
        eligible_bases = [w for w in base_winners if w.get("is_sharpe", 0) >= 1.0]
        print(f"\n{'='*78}\nStage 3: regime-tilt overlay around {len(eligible_bases)} base winners\n{'='*78}")
        regime_cache = {}
        rows3, t0 = [], time.time()
        all_cfgs = []
        for base in eligible_bases:
            for c in stage3_grid_for_winner(base):
                c["_base_cadence"] = base["cadence"]
                all_cfgs.append(c)
        print(f"  total stage-3 configs across cadences: {len(all_cfgs)}")
        for i, cfg in enumerate(all_cfgs, 1):
            key = (cfg["regime_ma"], cfg["regime_confirm"])
            if key not in regime_cache:
                regime_cache[key] = build_regime_panel_confirmed(
                    REGIME_IDX, ma_window=cfg["regime_ma"],
                    confirm_days=cfg["regime_confirm"], calendar=calendar,
                )
            rp = regime_cache[key]
            base_cfg = {k: cfg[k] for k in (
                "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
                "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
            )}
            out = run_config(ctx=ctx, cfg=base_cfg, is_only=True,
                             regime_panel=rp,
                             bear_w_uc=cfg["bear_w_uc"],
                             bear_w_cr=cfg["bear_w_cr"])
            out.pop("_equity", None)
            for k in ("regime_ma", "regime_confirm", "bear_w_uc", "bear_w_cr"):
                out[k] = cfg[k]
            rows3.append(out)
            elapsed = time.time() - t0
            if i % 8 == 0 or i == len(all_cfgs):
                print(f"  [{i:2d}/{len(all_cfgs)}] cad={cfg['cadence'][:3]} "
                      f"ma={cfg['regime_ma']:3d} cf={cfg['regime_confirm']} "
                      f"bearUC/CR={cfg['bear_w_uc']:.2f}/{cfg['bear_w_cr']:.2f}   "
                      f"Sharpe={out.get('is_sharpe', 0):.2f}  ({elapsed:.0f}s)")

        df3 = pd.DataFrame(rows3).sort_values("is_sharpe", ascending=False)
        df3.to_csv(out_dir / "stage3.csv", index=False)
        print(f"\n[stage3] top 5 by IS Sharpe (across both cadences):")
        print(df3.head(5)[["cadence", "lookback", "regime_ma", "regime_confirm",
                           "bear_w_uc", "bear_w_cr",
                           "is_sharpe", "is_cagr_pct", "is_max_dd_pct"]]
              .to_string(index=False))

    if args.stop_after_stage < 4:
        print(f"\n[stop] --stop-after-stage 3 → halting after Stage 3.")
        # Still compute best so far for diagnostics
        candidates = [("base", base_winner)]
        if not df3.empty:
            r3 = df3.iloc[0].to_dict()
            if r3.get("is_sharpe", 0) > base_winner.get("is_sharpe", 0):
                candidates.append(("regime", r3))
        winner_label, winner_cfg = candidates[-1]
        print(f"Best so far: {winner_label}  IS Sharpe={winner_cfg.get('is_sharpe', 'NA')}")
        return 0

    # ---- Stage 4: skip_days sweep on per-cadence winners ----
    # Pull best regime-overlaid config per cadence from df3 if available,
    # otherwise fall back to per-cadence Stage-2 base_winners.
    stage4_inputs = []
    for cad in ("monthly", "biweekly"):
        if not df3.empty and "cadence" in df3.columns:
            sub = df3[df3["cadence"] == cad].sort_values("is_sharpe", ascending=False)
            if not sub.empty:
                stage4_inputs.append(sub.iloc[0].to_dict())
                continue
        # fallback: base winner for this cadence
        cand = [w for w in base_winners if w["cadence"] == cad]
        if cand:
            stage4_inputs.append(cand[0])

    s4_cfgs = stage4_configs_for_winners(stage4_inputs)
    print(f"\n{'='*78}\nStage 4: skip_days sweep on {len(stage4_inputs)} per-cadence winners\n{'='*78}")
    print(f"  total stage-4 configs: {len(s4_cfgs)}  (skip_days ∈ {SKIP_GRID})")

    regime_cache_s4 = {}
    rows4, t0 = [], time.time()
    for i, cfg in enumerate(s4_cfgs, 1):
        rp = None
        bw_uc = bw_cr = None
        if "regime_ma" in cfg and "regime_confirm" in cfg:
            key = (int(cfg["regime_ma"]), int(cfg["regime_confirm"]))
            if key not in regime_cache_s4:
                regime_cache_s4[key] = build_regime_panel_confirmed(
                    REGIME_IDX, ma_window=key[0],
                    confirm_days=key[1], calendar=calendar,
                )
            rp = regime_cache_s4[key]
            bw_uc = float(cfg["bear_w_uc"])
            bw_cr = float(cfg["bear_w_cr"])
        base_cfg = {k: cfg[k] for k in (
            "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
            "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
            "skip_days",
        )}
        out = run_config(ctx=ctx, cfg=base_cfg, is_only=True,
                         regime_panel=rp, bear_w_uc=bw_uc, bear_w_cr=bw_cr)
        out.pop("_equity", None)
        out["skip_days"] = cfg["skip_days"]
        for k in ("regime_ma", "regime_confirm", "bear_w_uc", "bear_w_cr"):
            if k in cfg:
                out[k] = cfg[k]
        rows4.append(out)
        elapsed = time.time() - t0
        print(f"  [{i:2d}/{len(s4_cfgs)}] cad={cfg['cadence'][:3]} "
              f"lb={cfg['lookback']} skip={cfg['skip_days']:2d}   "
              f"Sharpe={out.get('is_sharpe', 0):.2f}  "
              f"CAGR={out.get('is_cagr_pct', 0):6.2f}%  "
              f"DD={out.get('is_max_dd_pct', 0):6.2f}%  ({elapsed:.0f}s)")

    df4 = pd.DataFrame(rows4).sort_values("is_sharpe", ascending=False)
    df4.to_csv(out_dir / "stage4.csv", index=False)
    print(f"\n[stage4] top 5 by IS Sharpe:")
    print(df4.head(5)[["cadence", "lookback", "skip_days",
                       "is_sharpe", "is_cagr_pct", "is_max_dd_pct"]]
          .to_string(index=False))

    # ---- Pick OVERALL winner across base / regime / skip ----
    candidates = [("base", base_winner)]
    if not df3.empty:
        r3 = df3.iloc[0].to_dict()
        if r3.get("is_sharpe", 0) > base_winner.get("is_sharpe", 0):
            candidates.append(("regime", r3))
    if not df4.empty:
        r4 = df4.iloc[0].to_dict()
        if r4.get("is_sharpe", 0) > candidates[-1][1].get("is_sharpe", 0):
            candidates.append(("skip", r4))
    winner_label, winner_cfg = candidates[-1]
    print(f"\n{'='*78}\nWinner ({winner_label}):")
    for k in ("lookback", "w_uc", "w_cr", "return_filter", "min_obs", "top_n",
              "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
              "skip_days",
              "regime_ma", "regime_confirm", "bear_w_uc", "bear_w_cr"):
        if k in winner_cfg and pd.notna(winner_cfg[k]):
            print(f"  {k:<18} {winner_cfg[k]}")
    print(f"  is_sharpe          {winner_cfg.get('is_sharpe', 'NA')}")
    print('=' * 78)

    # ---- Re-run winner on full window (IS + OOS) ----
    base_cfg = {k: winner_cfg[k] for k in (
        "w_uc", "w_cr", "return_filter", "lookback", "min_obs",
        "top_n", "exit_buffer", "cadence", "atr_mult", "atr_min_floor",
    )}
    base_cfg["skip_days"] = int(winner_cfg.get("skip_days", 0) or 0)
    rp = None
    bw_uc = bw_cr = None
    if winner_label in ("regime", "skip") and "regime_ma" in winner_cfg \
            and pd.notna(winner_cfg.get("regime_ma")):
        rp = build_regime_panel_confirmed(
            REGIME_IDX, ma_window=int(winner_cfg["regime_ma"]),
            confirm_days=int(winner_cfg["regime_confirm"]), calendar=calendar,
        )
        bw_uc = float(winner_cfg["bear_w_uc"])
        bw_cr = float(winner_cfg["bear_w_cr"])
    full = run_config(ctx=ctx, cfg=base_cfg, is_only=False,
                      regime_panel=rp, bear_w_uc=bw_uc, bear_w_cr=bw_cr)
    eq_full = full["_equity"]
    eq_full.to_csv(out_dir / "winner_equity.csv", index=False)

    # ---- Multi-window evaluation ----
    wdf = evaluate_winner_windows(eq_full, US_WINDOWS)
    wdf.to_csv(out_dir / "winner_windows.csv", index=False)
    passed, failures = passes_us_criteria(wdf)
    print(f"\nMulti-window evaluation:")
    print(wdf.to_string(index=False))
    print(f"\nPass criteria: {'PASS ✓' if passed else 'FAIL ✗'}")
    if not passed:
        for f in failures:
            print(f"  - {f}")
    print(f"\n[done] outputs → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
