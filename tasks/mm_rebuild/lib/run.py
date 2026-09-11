"""Thin runner: the OM25 harness with the momentum score swapped in. Runs and registry live under tasks/mm_rebuild/runs."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import pandas as pd
import numpy as np
HERE = Path(__file__).resolve().parent; TASK = HERE.parent
import importlib.util
OM_LIB = TASK.parent / "om25_rebuild" / "lib"; sys.path.insert(0, str(OM_LIB)); sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("om25_run", OM_LIB / "run.py"); om = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(om)  # the OM25 harness, by path (this file is also called run.py)
from momentum import make_momentum_score  # noqa: E402
import windows as W  # noqa: E402
RUNS = TASK / "runs"; RUNS.mkdir(exist_ok=True); W.REG = RUNS / "registry.csv"
DEFAULTS = dict(universe="nifty250", kind="abs", lookback=126, min_obs=110, skip=0, vol_floor=0.05, positive_only=False,
                top_n=25, exit_buffer=20, cadence="monthly", exit_cadence="same", trailing_stop=0.0, max_weight=1.0, slippage=0.002,
                min_hold_days=0, fill_from_buffer=False, trim_to_target=0.0, stop_check="weekly", rebalance_day=1, sector_cap=0, satellite_slots=0, universe_cap=0, turnover_floor=0.0, sizing="equal", iv_window=63, dyn_n_bear=0, dyn_mode="lever", bear_buffer=-1, vol_target=0.0, vol_window=21, str_kind="breadth_ma", str_len=200, str_thresh=0.3, str_mode="abs", mix_w=0.5, cr_quantile=0.0, vol_kick="none", vol_k=0.0, regimes=1, bull_kind="abs", overlay=False, regime_kind="roc", roc_n=31, confirm=3, bear_exposure=1.0, reenter_on_flip=False, start="2010-01-01", end="2015-12-31")
_ID_OPTIONAL = {"mix_w", "trim_to_target", "fill_from_buffer", "stop_check", "rebalance_day", "sector_cap", "satellite_slots", "bear_buffer", "universe_cap", "turnover_floor", "sizing", "iv_window", "dyn_n_bear", "dyn_mode", "vol_target", "vol_window", "str_kind", "str_len", "str_thresh", "str_mode", "min_hold_days", "vol_kick", "vol_k", "cr_quantile", "regimes", "bull_kind", "overlay", "regime_kind", "roc_n", "confirm", "bear_exposure", "reenter_on_flip"}


_turn = {}
def turnover_panel(cols):
    """Rupee turnover (close x volume) per symbol from the master per-symbol files, aligned to the close panel's calendar. Cached in runs/."""
    if "p" not in _turn:
        cache = RUNS / "turnover_panel.parquet"
        if cache.exists():
            _turn["p"] = pd.read_parquet(cache)
        else:
            close = om.panels()["close"]; frames = {}
            for sym in close.columns:
                f = om.PANEL / f"{sym}_day.csv"
                if f.exists():
                    d = pd.read_csv(f, usecols=["date", "close", "volume"], parse_dates=["date"]).set_index("date")
                    frames[sym] = (d["close"] * d["volume"]).reindex(close.index)
            _turn["p"] = pd.DataFrame(frames); _turn["p"].to_parquet(cache)
    return _turn["p"].reindex(columns=cols)


def monthly_on_or_after(cal, day):
    """First trading day of each month on or after calendar day `day` (day=1 reproduces the engine's monthly_first_trading_day)."""
    out = []
    for (y, m), grp in pd.Series(cal, index=cal).groupby([cal.year, cal.month]):
        hit = grp[grp.index.day >= day]
        if len(hit): out.append(hit.index[0])
    return pd.DatetimeIndex(out)


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
    volume_panel = turnover_panel(cols) if (cfg["vol_kick"] != "none" or cfg["universe_cap"] or cfg["turnover_floor"]) else None
    core_mask = None
    if cfg["universe_cap"] or cfg["satellite_slots"]:
        from regime import membership_mask
        core_mask = membership_mask(om.MEMBERSHIP["nifty250"], close).reindex(columns=cols, fill_value=False)
    def build_score(kind):
        if kind in ("cr", "5050", "uc"):   # OM25's capture-statistics scores (om25_rebuild/lib/score.py), one regime, return filter on
            from score import make_capture_score
            w_uc, w_cr = {"uc": (1.0, 0.0), "cr": (0.0, 1.0), "5050": (0.5, 0.5)}[kind]
            return make_capture_score(returns_uni, None, w_uc_bull=w_uc, w_cr_bull=w_cr, return_filter=True, lookback=cfg["lookback"], min_obs=cfg["min_obs"], candidate_fn=candidate_fn)
        if kind.startswith("mix"):          # 2026-09-11: rank blend of vol-adjusted momentum (weight mix_w) and capture ratio (1 - mix_w)
            fm = build_score("voladj"); fc = build_score("cr"); w = cfg["mix_w"]
            def mix(signal_date, **_):
                a = fm(signal_date); b = fc(signal_date); i = a.index.intersection(b.index)
                if len(i) == 0: return pd.Series(dtype=float)
                return w * a[i].rank(pct=True) + (1 - w) * b[i].rank(pct=True)
            return mix
        return make_momentum_score(returns_uni, kind=kind, lookback=cfg["lookback"], min_obs=cfg["min_obs"], skip=cfg["skip"],
                                   vol_floor=cfg["vol_floor"], positive_only=cfg["positive_only"], candidate_fn=candidate_fn, cr_quantile=cfg["cr_quantile"],
                                   volume_panel=volume_panel, vol_kick=cfg["vol_kick"], vol_k=cfg["vol_k"],
                                   core_mask=core_mask, universe_cap=cfg["universe_cap"], turnover_floor=cfg["turnover_floor"])
    score_fn = build_score(cfg["kind"])
    if False:
      score_fn = make_momentum_score(returns_uni, kind=cfg["kind"], lookback=cfg["lookback"], min_obs=cfg["min_obs"], skip=cfg["skip"],
                                     vol_floor=cfg["vol_floor"], positive_only=cfg["positive_only"], candidate_fn=candidate_fn, cr_quantile=cfg["cr_quantile"],
                                     volume_panel=volume_panel, vol_kick=cfg["vol_kick"], vol_k=cfg["vol_k"],
                                     core_mask=core_mask, universe_cap=cfg["universe_cap"], turnover_floor=cfg["turnover_floor"])
    if cfg["satellite_slots"]:
        # founder 2026-09-10: keep the majority of the book in the Nifty 250 core and reserve K slots for the
        # strongest names outside it (the 251-500 band). Implemented as a synthetic ranking so the engine's
        # nlargest(top_n + exit_buffer) yields exactly (top_n - K) core then K satellite; the exit buffer is
        # split between the two sleeves in proportion. Satellite names sit at the BOTTOM of the top-N block,
        # so a bear truncation (dyn_n_bear) cuts them first.
        _base_mc = score_fn; _K = cfg["satellite_slots"]; _TN = cfg["top_n"]; _EB = cfg["exit_buffer"]
        _ncore = _TN - _K; _bc = int(round(_EB * _ncore / _TN)); _bt = _EB - _bc
        def score_fn(signal_date, **_):
            sc = _base_mc(signal_date)
            if sc.empty:
                return sc
            is_core = core_mask.loc[signal_date].reindex(sc.index).fillna(False).astype(bool)
            if _K >= _TN:   # satellite_slots == top_n means a PURE non-core book: drop the core entirely
                t = sc[~is_core.values].sort_values(ascending=False)
                return pd.Series(np.linspace(1.0, 0.0, len(t)), index=t.index)
            c = sc[is_core.values].sort_values(ascending=False); t = sc[~is_core.values].sort_values(ascending=False)
            order = list(c.index[:_ncore]) + list(t.index[:_K]) + list(c.index[_ncore:_ncore + _bc]) + list(t.index[_K:_K + _bt])
            seen = set(order); order += [x for x in sc.sort_values(ascending=False).index if x not in seen]
            return pd.Series(np.linspace(1.0, 0.0, len(order)), index=order)
    start = pd.Timestamp(cfg["start"]); end = pd.Timestamp(cfg["end"]) if cfg["end"] else cal[-1]
    overlay_panel = None; roc = None
    if cfg["overlay"] or cfg["regimes"] == 2 or cfg["dyn_n_bear"]:
        # both series are confirmed then shifted one session inside their builders: the value at t is decided from closes <= t-1
        roc = (om.roc_regime(om.REGIME_INDEX, cfg["roc_n"], cfg["confirm"], cal) if cfg["regime_kind"] == "roc"
               else om.strength_series(cfg["universe"], cfg["str_kind"], cfg["str_len"], cfg["str_thresh"], cfg["str_mode"], cfg["confirm"], end)).reindex(cal).ffill().fillna(True).astype(bool)
    if cfg["overlay"]:
        overlay_panel = roc
    if cfg["dyn_n_bear"]:
        # founder 2026-09-10: hold top_n names in bull, dyn_n_bear in bear. 'lever': each name keeps its 1/top_n weight, so gross
        # exposure falls to dyn_n_bear/top_n; 'concentrate': the engine's 1/n sizing keeps the book fully invested in fewer names.
        _dyn_base = score_fn; bb = cfg["exit_buffer"] if cfg["bear_buffer"] < 0 else cfg["bear_buffer"]; nb = cfg["dyn_n_bear"] + bb
        _last = {}
        def score_fn(signal_date, **_):
            sc = _dyn_base(signal_date); _last["rank"] = list(sc.index)
            return sc if bool(roc.get(signal_date, True)) else sc.nlargest(nb)
        if cfg["dyn_mode"] == "lever":
            overlay_panel = roc.astype(float).where(roc, cfg["dyn_n_bear"] / cfg["top_n"])
        # NOTE (2026-09-10 audit): 'concentrate' as first run only tightened the exit rank in bear (the engine still fills toward top_n from
        # the truncated list; §8-§9 runs held 17-25 names). 'hold' below is the founder's actual idea: in bear only the top dyn_n_bear ranks
        # may be bought, so the book runs down to N names, fully invested through the engine's 1/n sizing; exits at rank N + bear_buffer.
    if cfg["vol_target"] > 0:
        # exposure = min(1, target / realised vol of NIFTY 500 over the trailing window), set at Friday's close from returns <= that
        # close and applied from the next session (shift(1) then ffill), so no session's exposure uses its own return
        idx5 = pd.read_csv(om.MASTER / "benchmarks/NIFTY_500.csv", parse_dates=["date"]).set_index("date")["close"].sort_index()
        rv = idx5.pct_change().rolling(cfg["vol_window"]).std() * (252 ** 0.5)
        w = (cfg["vol_target"] / rv).clip(upper=1.0)
        w = w[w.index.dayofweek == 4].reindex(cal).shift(1).ffill().fillna(1.0)
        overlay_panel = w if overlay_panel is None else overlay_panel.astype(float).where(overlay_panel.astype(bool) if overlay_panel.dtype == bool else overlay_panel >= 1.0, overlay_panel.astype(float)).combine(w, min)
    if cfg["regimes"] == 2:   # §3d tilt: bull -> bull_kind score, bear -> the base kind
        bull_fn = build_score(cfg["bull_kind"]); _tilt_base = score_fn
        def score_fn(signal_date, **_):
            return (bull_fn if bool(roc.get(signal_date, True)) else _tilt_base)(signal_date)
    # the stop (and any weekly rank check) is evaluated only on these signal dates and executed the next session
    _mon = (lambda c: monthly_on_or_after(c, cfg["rebalance_day"])) if cfg["rebalance_day"] != 1 else om.monthly_first_trading_day
    weekly = {"weekly": om.fridays, "biweekly": om.biweekly_fridays, "monthly": _mon}[cfg["stop_check"]](cal); weekly = weekly[(weekly >= start) & (weekly <= end)]
    from scripts._clean_engine import thursdays as _thu
    entry_all = {"biweekly": om.biweekly_fridays, "weekly": om.fridays, "weekly_thu": _thu, "monthly": _mon}[cfg["cadence"]](cal)
    entries = entry_all[(entry_all >= start) & (entry_all <= end)]
    if cfg["overlay"] and cfg["reenter_on_flip"]:
        flips = overlay_panel.index[overlay_panel & ~overlay_panel.shift(1, fill_value=False)]; entries = entries.union(flips[(flips >= start) & (flips <= end)])
    cal_run = cal[cal <= end]
    size_weights = None; top_n_fn = None
    if cfg["dyn_n_bear"] and cfg["dyn_mode"] == "hold":
        # founder's idea, properly: in bear the engine may hold at most dyn_n_bear names (entries capped there, 1/n sizing on the smaller
        # book); exits at rank dyn_n_bear + bear_buffer via the truncated list. Positions bought earlier at 1/25 are not topped up (the
        # engine never resizes existing holdings), so the bear book can carry some cash; reported as 'invested'.
        def top_n_fn(sd):
            return cfg["top_n"] if sd is None or bool(roc.get(sd, True)) else cfg["dyn_n_bear"]
    if cfg["sizing"] in ("invvol", "invvol_bear"):
        # inverse-volatility weights over the intended book, capped at max_weight and renormalised; vol from returns up to the
        # signal date (the entry executes the next session), so sizing never sees the entry day's return
        ivol = 1.0 / returns_uni.rolling(cfg["iv_window"], min_periods=int(cfg["iv_window"] * 0.8)).std().replace(0, np.nan)
        def size_weights(sd, symbols):
            if sd is None or sd not in ivol.index: return None
            if cfg["sizing"] == "invvol_bear" and (roc is None or bool(roc.get(sd, True))): return None   # equal weight in bull
            v = ivol.loc[sd].reindex(symbols).dropna()
            if v.empty: return None
            w = v / v.sum()
            for _ in range(5):
                over = w > cfg["max_weight"]
                if not over.any(): break
                w[over] = cfg["max_weight"]; rest = w[~over]; w[~over] = rest / rest.sum() * (1 - cfg["max_weight"] * over.sum()) if rest.sum() > 0 else rest
            return w.to_dict()
    sector_of = None
    if cfg["sector_cap"]:
        # sector per symbol, point-in-time by snapshot window where the archives allow; priority current scheme > 2014-20 > 2006-13 > Zerodha,
        # all mapped to NSE's current 21 sectors (sector/scheme_map.csv). Unlabelled names (13% of all-ever) are unconstrained.
        lk = pd.read_csv(HERE.parent / "sector/sector_v2_lookup.csv", parse_dates=["as_of_first", "as_of"])
        sector_of = {}
        for sym, g in lk.groupby("symbol"):
            g = g.sort_values(["pri", "as_of"], ascending=[True, False]); sector_of[sym] = g.sector_v2.iloc[0]
    from _engine_iv import run_strategy as _run
    res = _run(close_panel=close.loc[cal_run], trade_panel=trade.loc[cal_run], calendar=cal_run, benchmark_aligned=p["bench"].loc[cal_run],
                          entry_signal_dates=entries, weekly_signal_dates=weekly, signal_function=score_fn, signal_function_args={},
                          sma_200_panel=p["sma200"].loc[cal_run], atr_20_panel=p["atr20"].loc[cal_run],
                          top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"], max_weight=cfg["max_weight"], slippage=cfg["slippage"],
                          atr_mult=0.0, atr_min_floor=cfg["trailing_stop"], use_trailing_stop=cfg["trailing_stop"] > 0, use_dma_exit=False,
                          weekly_rank_check=(cfg["exit_cadence"] == "weekly"),
                          regime_panel=overlay_panel, bear_exposure=float(cfg["bear_exposure"]) if cfg["overlay"] else 0.0,
                          membership_fn=membership_fn, min_hold_days=cfg["min_hold_days"], size_weights=size_weights, top_n_fn=top_n_fn, sector_of=sector_of, sector_cap=cfg["sector_cap"] or None, fill_from_buffer=cfg["fill_from_buffer"], trim_to_target=cfg["trim_to_target"], initial_capital=1_000_000)
    out.mkdir(parents=True, exist_ok=True); json.dump(cfg, open(out / "config.json", "w"), indent=1)
    res["equity"].to_csv(out / "equity.csv", index=False); res["trades"].to_csv(out / "trades.csv", index=False)
    if "exits" in res: res["exits"].to_csv(out / "exits.csv", index=False)
    return cfg, res
