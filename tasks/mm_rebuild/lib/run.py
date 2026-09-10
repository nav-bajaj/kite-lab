"""Thin runner: the OM25 harness with the momentum score swapped in. Runs and registry live under tasks/mm_rebuild/runs."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; TASK = HERE.parent
import importlib.util
OM_LIB = TASK.parent / "om25_rebuild" / "lib"; sys.path.insert(0, str(OM_LIB)); sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("om25_run", OM_LIB / "run.py"); om = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(om)  # the OM25 harness, by path (this file is also called run.py)
from momentum import make_momentum_score  # noqa: E402
import windows as W  # noqa: E402
RUNS = TASK / "runs"; RUNS.mkdir(exist_ok=True); W.REG = RUNS / "registry.csv"
DEFAULTS = dict(universe="nifty250", kind="abs", lookback=126, min_obs=110, skip=0, vol_floor=0.05, positive_only=False,
                top_n=25, exit_buffer=20, cadence="monthly", exit_cadence="same", trailing_stop=0.0, max_weight=1.0, slippage=0.002,
                overlay=False, regime_kind="roc", roc_n=31, confirm=3, bear_exposure=1.0, reenter_on_flip=False, start="2010-01-01", end="2015-12-31")
_ID_OPTIONAL = {"overlay", "regime_kind", "roc_n", "confirm", "bear_exposure", "reenter_on_flip"}


def cfg_id(cfg: dict) -> str:
    core = {k: v for k, v in cfg.items() if not (k in _ID_OPTIONAL and v == DEFAULTS[k])}
    return hashlib.md5(json.dumps(core, sort_keys=True).encode()).hexdigest()[:10]


def run_candidate(**overrides):
    cfg = {**DEFAULTS, **overrides}; out = RUNS / cfg_id(cfg)
    if om._complete(out, cfg["end"] or om.panels()["close"].index[-1]):
        return cfg, {"equity": pd.read_csv(out / "equity.csv"), "reused": True}
    p = om.panels(); close, trade = p["close"], p["trade"]; cal = close.index
    universe, membership_fn, candidate_fn = om.resolve_universe(om.MEMBERSHIP[cfg["universe"]], om.MEMBERSHIP[cfg["universe"]])
    cols = [s for s in close.columns if s in universe]; returns_uni = close[cols].pct_change()
    score_fn = make_momentum_score(returns_uni, kind=cfg["kind"], lookback=cfg["lookback"], min_obs=cfg["min_obs"], skip=cfg["skip"],
                                   vol_floor=cfg["vol_floor"], positive_only=cfg["positive_only"], candidate_fn=candidate_fn)
    start = pd.Timestamp(cfg["start"]); end = pd.Timestamp(cfg["end"]) if cfg["end"] else cal[-1]
    overlay_panel = None
    if cfg["overlay"]:
        overlay_panel = om.roc_regime(om.REGIME_INDEX, cfg["roc_n"], cfg["confirm"], cal).astype(bool)
    weekly = om.fridays(cal); weekly = weekly[(weekly >= start) & (weekly <= end)]
    entry_all = {"biweekly": om.biweekly_fridays, "weekly": om.fridays, "monthly": om.monthly_first_trading_day}[cfg["cadence"]](cal)
    entries = entry_all[(entry_all >= start) & (entry_all <= end)]
    if cfg["overlay"] and cfg["reenter_on_flip"]:
        flips = overlay_panel.index[overlay_panel & ~overlay_panel.shift(1, fill_value=False)]; entries = entries.union(flips[(flips >= start) & (flips <= end)])
    cal_run = cal[cal <= end]
    res = om.run_strategy(close_panel=close.loc[cal_run], trade_panel=trade.loc[cal_run], calendar=cal_run, benchmark_aligned=p["bench"].loc[cal_run],
                          entry_signal_dates=entries, weekly_signal_dates=weekly, signal_function=score_fn, signal_function_args={},
                          sma_200_panel=p["sma200"].loc[cal_run], atr_20_panel=p["atr20"].loc[cal_run],
                          top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"], max_weight=cfg["max_weight"], slippage=cfg["slippage"],
                          atr_mult=0.0, atr_min_floor=cfg["trailing_stop"], use_trailing_stop=cfg["trailing_stop"] > 0, use_dma_exit=False,
                          weekly_rank_check=(cfg["exit_cadence"] == "weekly"),
                          regime_panel=overlay_panel, bear_exposure=float(cfg["bear_exposure"]) if cfg["overlay"] else 0.0,
                          membership_fn=membership_fn, initial_capital=1_000_000)
    out.mkdir(parents=True, exist_ok=True); json.dump(cfg, open(out / "config.json", "w"), indent=1)
    res["equity"].to_csv(out / "equity.csv", index=False); res["trades"].to_csv(out / "trades.csv", index=False)
    if "exits" in res: res["exits"].to_csv(out / "exits.csv", index=False)
    return cfg, res
