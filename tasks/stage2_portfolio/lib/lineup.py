"""S2-v2 against the full production lineup on identical data.

TL25 v3, L6 v2, OM25 v3 and COMBO Defensive are each run at their locked
production config through scripts/_clean_engine.run_strategy - the same engine
production uses - on this task's panel, calendar, membership and benchmark.
S2-v2 runs through the task engine. Only the data basis is held common.

Window starts 2010-01-04: the NIFTY 100 history that OM25 and COMBO need for
their regime panel begins there, so every strategy is given the same start.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2]))

from scripts._clean_engine import (run_strategy, fridays, biweekly_fridays,
                                   thursdays)
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score, V3_LOCKED
from scripts._momentum_engine import build_momentum_panels, make_momentum_score
from scripts.om25_v3 import (LOCKED as OM25_LOCKED,
                             build_regime_panel_confirmed, make_om25_tilt_score)
from scripts.combo_defensive import LOCKED as COMBO_LOCKED, make_combo_score_fn
from scripts.universe_membership import (load_membership, all_ever_members,
                                         make_membership_fn, make_candidate_fn,
                                         union_membership_fns)

from lib.run_s2 import build_context, run_one, metrics
from lib.panels import MEMBERSHIP_RECON, MEMBERSHIP_PROD, ROOT

IS = ("2010-01-04", "2016-12-31")
OOS = ("2017-01-01", None)

N250_RECON = ROOT / "tasks/index_reconstruction/data/nifty250_membership_reconstructed.csv"
N250_PROD = ROOT / "data/static/nifty250_membership.csv"

S2V2 = dict(variant="E_rs_unext", top_n=20, exit_buffer=40, stop=0.0,
            weight_mode="drift", sector_cap=0, hold_mode="tiered",
            exit_confirm_weeks=3)


def stitched_nifty100(calendar):
    """Historical NIFTY 100 spliced with the live file (they agree to 5e-6)."""
    a = pd.read_csv(ROOT / "indices_data_historical/NIFTY_100.csv",
                    parse_dates=["date"]).set_index("date")["close"]
    b = pd.read_csv(ROOT / "indices_data/NIFTY_100.csv",
                    parse_dates=["date"]).set_index("date")["close"]
    s = pd.concat([a[a.index < pd.Timestamp("2020-01-01")], b]).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    out = ROOT / "tmp_nifty100_stitched.csv"
    s.rename("close").reset_index().to_csv(out, index=False)
    return out


def truncate(ctx, start, end):
    cal = ctx["prices"]["calendar"]
    e = pd.Timestamp(end) if end else cal[-1]
    cal2 = cal[cal <= e]
    return (ctx["prices"]["close"].loc[cal2], ctx["prices"]["trade"].loc[cal2],
            cal2, pd.Timestamp(start), e)


def native(ctx, name, regime_path):
    """Run one production strategy at its locked config."""
    def go(start, end):
        close, trade, cal, s_ts, e_ts = truncate(ctx, start, end)
        bench = ctx["benchmark"].reindex(cal).ffill()
        sma200 = close.rolling(200, min_periods=160).mean()
        atr20 = close.pct_change(fill_method=None).rolling(20, min_periods=16).std()
        wk = fridays(cal); wk = wk[(wk >= s_ts) & (wk <= e_ts)]
        bi = biweekly_fridays(cal); bi = bi[(bi >= s_ts) & (bi <= e_ts)]
        th = thursdays(cal); th = th[(th >= s_ts) & (th <= e_ts)]
        common = dict(close_panel=close, trade_panel=trade, calendar=cal,
                      benchmark_aligned=bench, sma_200_panel=sma200,
                      atr_20_panel=atr20, max_weight=0.075, slippage=0.002,
                      signal_function_args={}, initial_capital=1_000_000)
        mem_nse = ctx["membership_fn"]; cand_nse = ctx["candidate_fn"]

        if name == "TL25v3":
            p = build_tl25_panels(close, dma_short=50, dma_long=200,
                                  dma_persist_ref=100, persistence_window=252,
                                  drawdown_window=126, drawdown_concavity=2,
                                  momentum_window=63)
            sf = make_tl25_score(p, w_persistence=0.40, w_drawdown=0.20,
                                 w_momentum=0.40, candidate_fn=cand_nse)
            return run_strategy(entry_signal_dates=bi, weekly_signal_dates=wk,
                                signal_function=sf, top_n=25, exit_buffer=20,
                                atr_mult=0.0, atr_min_floor=0.20,
                                use_trailing_stop=True, use_dma_exit=False,
                                weekly_rank_check=True, regime_panel=None,
                                bear_exposure=0.0, membership_fn=mem_nse,
                                **common)

        if name == "L6v2":
            p = build_momentum_panels(close, lookback_days=126)
            sf = make_momentum_score(p, vol_floor=0.05, vol_power=1.0,
                                     cross_sectional_zscore=True,
                                     candidate_fn=cand_nse)
            return run_strategy(entry_signal_dates=th, weekly_signal_dates=th,
                                signal_function=sf, top_n=24, exit_buffer=0,
                                atr_mult=0.0, atr_min_floor=0.0,
                                use_trailing_stop=False, use_dma_exit=False,
                                weekly_rank_check=False, regime_panel=None,
                                bear_exposure=0.0, min_hold_days=8,
                                membership_fn=mem_nse, **common)

        regime = build_regime_panel_confirmed(regime_path, 100, 3, calendar=cal)

        if name == "OM25v3":
            cols = [c for c in close.columns if c in ctx["n250_all"]]
            rets = close[cols].pct_change(fill_method=None)
            sf = make_om25_tilt_score(rets, regime, bull_w_uc=0.5, bull_w_cr=0.5,
                                      bear_w_uc=0.0, bear_w_cr=1.0,
                                      return_filter=True, lookback=252,
                                      min_obs=220,
                                      candidate_fn=ctx["n250_candidate_fn"])
            return run_strategy(entry_signal_dates=bi, weekly_signal_dates=wk,
                                signal_function=sf, top_n=25, exit_buffer=20,
                                atr_mult=0.0, atr_min_floor=0.20,
                                use_trailing_stop=True, use_dma_exit=False,
                                weekly_rank_check=False, regime_panel=None,
                                bear_exposure=0.0,
                                membership_fn=ctx["n250_membership_fn"], **common)

        if name == "COMBO":
            lp = build_momentum_panels(close, lookback_days=126)
            l6 = make_momentum_score(lp, vol_floor=0.05, vol_power=1.0,
                                     cross_sectional_zscore=True,
                                     candidate_fn=cand_nse)
            cols = [c for c in close.columns if c in ctx["n250_all"]]
            rets = close[cols].pct_change(fill_method=None)
            om = make_om25_tilt_score(rets, regime, bull_w_uc=0.5, bull_w_cr=0.5,
                                      bear_w_uc=0.0, bear_w_cr=1.0,
                                      return_filter=True, lookback=252,
                                      min_obs=220,
                                      candidate_fn=ctx["n250_candidate_fn"])
            sf = make_combo_score_fn([("L6", l6), ("OM25", om)], n_per=12)
            return run_strategy(entry_signal_dates=bi, weekly_signal_dates=wk,
                                signal_function=sf, top_n=24, exit_buffer=0,
                                atr_mult=0.0, atr_min_floor=0.0,
                                use_trailing_stop=False, use_dma_exit=False,
                                weekly_rank_check=False, regime_panel=regime,
                                bear_exposure=0.5, min_hold_days=8,
                                membership_fn=union_membership_fns(
                                    [mem_nse, ctx["n250_membership_fn"]]),
                                **common)
        raise ValueError(name)
    return go


def build_full_context(mcsv, n250csv):
    ctx = build_context(membership_csv=mcsv, min_stage_age=0)
    n250 = load_membership(n250csv)
    ctx["n250_all"] = all_ever_members(n250)
    ctx["n250_membership_fn"] = make_membership_fn(n250)
    ctx["n250_candidate_fn"] = make_candidate_fn(n250)
    return ctx


def curves_and_books(ctx, regime_path, start, end):
    out = {}
    for nm in ("TL25v3", "L6v2", "OM25v3", "COMBO"):
        out[nm] = native(ctx, nm, regime_path)(start, end)
    out["S2v2"] = run_one(ctx, start=start, end=end, **S2V2)
    return out


def main():
    basis = sys.argv[1] if len(sys.argv) > 1 else "survivorship_free"
    mcsv, n250 = ((MEMBERSHIP_RECON, N250_RECON) if basis == "survivorship_free"
                  else (MEMBERSHIP_PROD, N250_PROD))
    ctx = build_full_context(mcsv, n250)
    reg = stitched_nifty100(ctx["prices"]["calendar"])
    bench = ctx["benchmark"]
    rows = {}
    print(f"=== {basis} : full lineup, identical data, 2010-2026 ===")
    print(f"  {'book':9s} | {'IS CAGR':>8s} {'IS DD':>8s} {'IS Sh':>6s} {'IS Cal':>7s} |"
          f" {'OOS CAGR':>9s} {'OOS DD':>8s} {'OOS Sh':>7s} {'OOS Cal':>8s}"
          f" {'hold':>6s} {'turn':>5s}")
    books = {}
    for win, (s, e) in (("IS", IS), ("OOS", OOS)):
        books[win] = curves_and_books(ctx, reg, s, e)
    for nm in ("OM25v3", "TL25v3", "L6v2", "COMBO", "S2v2"):
        mi = metrics(books["IS"][nm], benchmark=bench)
        mo = metrics(books["OOS"][nm], benchmark=bench)
        h = books["OOS"][nm]["exits"]["hold_days"].dropna()
        n = {"OM25v3": 25, "TL25v3": 25, "L6v2": 24, "COMBO": 24, "S2v2": 20}[nm]
        print(f"  {nm:9s} | {mi['cagr_pct']:7.2f}% {mi['max_dd_pct']:7.2f}%"
              f" {mi['sharpe']:6.2f} {mi['calmar']:7.2f} | {mo['cagr_pct']:8.2f}%"
              f" {mo['max_dd_pct']:7.2f}% {mo['sharpe']:7.2f} {mo['calmar']:8.2f}"
              f" {h.median():5.0f}d {mo['buys_per_year']/n:5.1f}")
        rows[nm] = dict(basis=basis, book=nm,
                        **{f"IS_{k}": v for k, v in mi.items() if not isinstance(v, dict)},
                        **{f"OOS_{k}": v for k, v in mo.items() if not isinstance(v, dict)},
                        median_hold=float(h.median()),
                        turnover_x=round(mo["buys_per_year"] / n, 1))
    pd.DataFrame(rows.values()).to_csv(
        HERE.parent / "data" / f"lineup_{basis}.csv", index=False)

    # ---- differentiation + marginal value (OOS) ---------------------------
    names = ["OM25v3", "TL25v3", "L6v2", "COMBO", "S2v2"]
    eq = {}
    for nm in names:
        e = books["OOS"][nm]["equity"].copy()
        e["date"] = pd.to_datetime(e["date"])
        eq[nm] = e.set_index("date")["pv"]
    wk = pd.DataFrame(eq).resample("W-FRI").last()
    r = wk.pct_change(fill_method=None).dropna()
    print("\n--- OOS weekly return correlation ---")
    print(r.corr().round(3).to_string())
    r.corr().to_csv(HERE.parent / "data" / f"lineup_corr_{basis}.csv")

    def snaps(res):
        tr = res["trades"].copy(); tr["date"] = pd.to_datetime(tr["date"])
        pos, out = {}, {}
        for d, g in tr.groupby("date"):
            for _, t in g.iterrows():
                s_ = t["symbol"]
                pos[s_] = pos.get(s_, 0) + (t["shares"] if t["side"] == "BUY"
                                            else -t["shares"])
                if pos[s_] <= 0:
                    pos.pop(s_, None)
            out[d] = set(pos)
        return out
    sn = {nm: snaps(books["OOS"][nm]) for nm in names}
    alld = sorted(set().union(*[set(v) for v in sn.values()]))
    me = set(pd.DatetimeIndex(alld).to_period("M").to_timestamp("M"))
    ov = pd.DataFrame(index=names, columns=names, dtype=float)
    for a in names:
        for b in names:
            vals, pa, pb = [], set(), set()
            for d in alld:
                pa = sn[a].get(d, pa); pb = sn[b].get(d, pb)
                if (pa or pb):
                    vals.append(len(pa & pb) / max(1, len(pa | pb)))
            ov.loc[a, b] = round(float(np.mean(vals)), 3)
    print("\n--- OOS holdings overlap (mean Jaccard) ---")
    print(ov.to_string())
    ov.to_csv(HERE.parent / "data" / f"lineup_overlap_{basis}.csv")

    # marginal value: equal-weight blend of the 4 production books +/- S2
    print("\n--- marginal value: equal-weight blend of the production books ---")
    def blend_stats(cols):
        b = r[cols].mean(axis=1)
        cum = (1 + b).cumprod()
        yrs = (cum.index[-1] - cum.index[0]).days / 365.25
        cagr = cum.iloc[-1] ** (1 / yrs) - 1
        vol = b.std() * np.sqrt(52)
        dd = (cum / cum.cummax()).min() - 1
        return cagr * 100, dd * 100, (cagr / vol), cagr / abs(dd)
    prod = ["OM25v3", "TL25v3", "L6v2", "COMBO"]
    for label, cols in (("4 production books", prod),
                        ("+ S2-v2 (5-way)", prod + ["S2v2"])):
        c, d, sh, cal = blend_stats(cols)
        print(f"  {label:22s} CAGR {c:6.2f}%  DD {d:7.2f}%  Sharpe {sh:5.2f}  Calmar {cal:5.2f}")
    print(f"\n  S2v2 corr to the 4-book blend: "
          f"{r['S2v2'].corr(r[prod].mean(axis=1)):.3f}")
    (ROOT / "tmp_nifty100_stitched.csv").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
