"""One candidate -> one backtest on the master store, through the production
engine unchanged. No weight cap, no stops (brief). Panels are loaded once
per process and shared across candidates.
"""
from __future__ import annotations

import hashlib, json, os, sys
from pathlib import Path

import pandas as pd

REPO = Path("/Users/navdeep/kite-lab")
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scripts._clean_engine import run_strategy, fridays, biweekly_fridays, monthly_first_trading_day  # noqa: E402
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.universe_membership import resolve_universe  # noqa: E402
from score import make_capture_score  # noqa: E402
from regime import roc_regime, ma_regime  # noqa: E402

MASTER = REPO / "data/master"
PANEL = MASTER / "panels/pr"
REGIME_INDEX = MASTER / "benchmarks/NIFTY_100.csv"
BENCH = MASTER / "benchmarks/NIFTY_100_bench.csv"
MEMBERSHIP = {"nifty250": MASTER / "membership/nifty250.csv", "nse500": MASTER / "membership/nse500.csv"}
RUNS = Path(__file__).resolve().parent.parent / "runs"

DEFAULTS = dict(universe="nifty250", score="5050", regimes=1, roc_n=31, confirm=3, overlay=False, bear_exposure=1.0, redeploy=False,
                top_n=25, exit_buffer=20, cadence="biweekly", lookback=252, min_obs=220,
                return_filter=True, start="2006-01-01", end=None, slippage=0.002,
                # smoke-test-only switches, never searched
                legacy_updown_rule=False, max_weight=1.0, trailing_stop=0.0, regime_kind="roc", ma_window=100)
SCORE_W = {"uc": (1.0, 0.0), "cr": (0.0, 1.0), "5050": (0.5, 0.5)}

_cache = {}


def panels():
    if "close" not in _cache:
        close, trade = load_price_panels(PANEL)
        _cache["close"], _cache["trade"] = close, trade
        _cache["bench"] = load_benchmark(BENCH).reindex(close.index).ffill()
        _cache["sma200"] = close.rolling(200, min_periods=200).mean()
        _cache["atr20"] = close.pct_change().rolling(20).std()
    return _cache


def cfg_id(cfg: dict) -> str:
    return hashlib.md5(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:10]


def _complete(out, end):
    """A run written before a disk-full interrupt may be truncated; trust it only if equity reaches the run end."""
    eq = out / "equity.csv"
    if not eq.exists() or not (out / "config.json").exists():
        return False
    try:
        last = pd.read_csv(eq).iloc[-1, 0]
        return pd.Timestamp(last) >= pd.Timestamp(end) - pd.Timedelta(days=7)
    except Exception:
        return False


def run_candidate(**overrides):
    cfg = {**DEFAULTS, **overrides}
    out = RUNS / cfg_id(cfg)
    if _complete(out, cfg["end"] or panels()["close"].index[-1]):
        return cfg, {"equity": pd.read_csv(out / "equity.csv"), "trades": pd.read_csv(out / "trades.csv"), "reused": True}
    p = panels(); close, trade = p["close"], p["trade"]; cal = close.index
    universe, membership_fn, candidate_fn = resolve_universe(MEMBERSHIP[cfg["universe"]], MEMBERSHIP[cfg["universe"]])
    cols = [s for s in close.columns if s in universe]
    returns_uni = close[cols].pct_change()
    roc = (roc_regime(REGIME_INDEX, cfg["roc_n"], cfg["confirm"], cal) if cfg["regime_kind"] == "roc"
           else ma_regime(REGIME_INDEX, cfg["ma_window"], cfg["confirm"], cal))
    reg = roc if cfg["regimes"] == 2 else None                 # score tilt (two regimes) or not
    overlay_panel = roc.astype(bool) if cfg["overlay"] else None   # exposure overlay (§3e)
    w_uc, w_cr = SCORE_W[cfg["score"]]
    score_fn = make_capture_score(returns_uni, reg, w_uc_bull=w_uc, w_cr_bull=w_cr, w_uc_bear=0.0, w_cr_bear=1.0,
                                  return_filter=cfg["return_filter"], lookback=cfg["lookback"], min_obs=cfg["min_obs"],
                                  candidate_fn=candidate_fn, legacy_updown_rule=cfg["legacy_updown_rule"])
    start, end = pd.Timestamp(cfg["start"]), (pd.Timestamp(cfg["end"]) if cfg["end"] else cal[-1])
    weekly = fridays(cal); weekly = weekly[(weekly >= start) & (weekly <= end)]
    entry_all = {"biweekly": biweekly_fridays, "weekly": fridays, "monthly": monthly_first_trading_day}[cfg["cadence"]](cal)
    entries = entry_all[(entry_all >= start) & (entry_all <= end)]
    res = run_strategy(close_panel=close, trade_panel=trade, calendar=cal, benchmark_aligned=p["bench"],
                       entry_signal_dates=entries, weekly_signal_dates=weekly,
                       signal_function=score_fn, signal_function_args={},
                       sma_200_panel=p["sma200"], atr_20_panel=p["atr20"],
                       top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"], max_weight=cfg["max_weight"],
                       slippage=cfg["slippage"], atr_mult=0.0, atr_min_floor=cfg["trailing_stop"],
                       use_trailing_stop=cfg["trailing_stop"] > 0, use_dma_exit=False,
                       regime_panel=overlay_panel, bear_exposure=float(cfg["bear_exposure"]) if cfg["overlay"] else 0.0,
                       regime_redeploy_on_increase=bool(cfg["redeploy"]),
                       membership_fn=membership_fn, initial_capital=1_000_000)
    out = RUNS / cfg_id(cfg); out.mkdir(parents=True, exist_ok=True)
    json.dump(cfg, open(out / "config.json", "w"), indent=1)
    res["equity"].to_csv(out / "equity.csv", index=False); res["trades"].to_csv(out / "trades.csv", index=False)
    if "exits" in res: res["exits"].to_csv(out / "exits.csv", index=False)
    return cfg, res
