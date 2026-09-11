"""Look-ahead and engine self-checks. Prints what RESULTS.md quotes.

1. Truncation: rebuild both strategies' signal panels from a close panel cut at a signal date D and compare the
   scores / candidate lists at D with the full-panel values. Identical means nothing at D reads past D.
2. Execution lag: every fill is on a session strictly after its signal date.
3. Engine: with exit confirmation 1, strict hold gate, drift, no stop, the carried S2 engine and the production
   scripts/_clean_engine.run_strategy produce the same equity path on the same score (2010-2013, NSE 500).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import panels, universe, om, RUNS, REPO
import s2 as S2
import dip as DIPM
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "scripts"))
from scripts._clean_engine import run_strategy  # noqa: E402

P = panels(); close = P["close"]
D = pd.Timestamp("2019-06-28")   # a Friday
cut = close[close.index <= D]

print("== 1. truncation at", D.date())
for uni in ("nse500", "nifty250"):
    sp_full, mfn, cfn = S2.s2_context(uni)
    sp_cut, _, _ = S2.s2_context(uni, close=cut)
    sf = S2.make_s2_score(sp_full, candidate_fn=cfn, hold_mode="tiered", **S2.VARIANTS["E_rs_unext"])(D).dropna()
    sc = S2.make_s2_score(sp_cut, candidate_fn=cfn, hold_mode="tiered", **S2.VARIANTS["E_rs_unext"])(D).dropna()
    same = sf.index.equals(sc.index) and np.allclose(sf.values, sc.values)
    print(f"  S2 {uni}: {len(sf)} scored names at D; full == truncated: {same}; top-5 {list(sf.sort_values(ascending=False).index[:5])}")
    gf, gc = sp_full["gate"].loc[D], sp_cut["gate"].loc[D]
    print(f"    gate passers full {int(gf.sum())} / truncated {int(gc.sum())}, equal: {gf.equals(gc)}")
    df_full = DIPM.dip_panels(uni); df_cut = DIPM.dip_panels(uni, close=cut)
    rf, rc = df_full["rank"].loc[D].dropna(), df_cut["rank"].loc[D].dropna()
    cand_f = sorted(df_full["sig"].loc[D][df_full["sig"].loc[D]].index); cand_c = sorted(df_cut["sig"].loc[D][df_cut["sig"].loc[D]].index)
    print(f"  Dip {uni}: rank equal {rf.index.equals(rc.index) and np.allclose(rf.values, rc.values)}; dip signals at D full {len(cand_f)} / truncated {len(cand_c)}, equal {cand_f == cand_c}")

print("== 2. execution lag")
cal = close.index
for name in ("s2_nse500", "s2_nifty250"):
    tr = pd.read_csv(RUNS / name / "trades.csv", parse_dates=["date"])
    prev = pd.Series(cal, index=cal).shift(1).reindex(tr["date"])
    ok = (prev.dt.dayofweek == 4).mean()      # the session before every fill is a Friday (the signal day)
    print(f"  {name}: {len(tr)} fills; share whose previous session is a Friday: {100*ok:.1f}%; fills on a Friday: {int((tr['date'].dt.dayofweek == 4).sum())}")
for name in ("dip_nse500", "dip_nifty250"):
    c = pd.read_csv(RUNS / name / "calls.csv", parse_dates=["signal_date", "entry_date", "exit_date"])
    pos = pd.Series(np.arange(len(cal)), index=cal)
    lag = pos.reindex(c["entry_date"]).to_numpy() - pos.reindex(c["signal_date"]).to_numpy()
    print(f"  {name}: entry session minus signal session: min {lag.min()} max {lag.max()} (must be 1)")

print("== 3. engine equivalence, NSE 500 2010-01-01 to 2013-12-31, strict gate / confirm 1 / drift / no stop")
uni = "nse500"; cols, mfn, cfn, mask = universe(uni)
sp = S2.build_stage2_panels(close[cols], mask, None, min_stage_age=0)
score_fn = S2.make_s2_score(sp, candidate_fn=cfn, hold_mode="strict", **S2.VARIANTS["E_rs_unext"])
start, end = pd.Timestamp("2010-01-01"), pd.Timestamp("2013-12-31")
wk = om.fridays(cal); wk = wk[(wk >= start) & (wk <= end)]
a = S2.run_s2_strategy(close_panel=close[cols], trade_panel=P["trade"][cols], calendar=cal, benchmark_aligned=P["bench"], signal_dates=wk,
                       score_fn=score_fn, top_n=20, exit_buffer=40, max_weight=0.075, slippage=0.002, stop=0.0, weight_mode="drift",
                       exit_confirm_weeks=1, membership_fn=mfn, end=end)
cal2 = cal[cal <= end]
b = run_strategy(close_panel=close[cols].loc[cal2], trade_panel=P["trade"][cols].loc[cal2], calendar=cal2, benchmark_aligned=P["bench"].loc[cal2],
                 entry_signal_dates=wk, weekly_signal_dates=wk, signal_function=score_fn, signal_function_args={},
                 sma_200_panel=P["sma200"][cols].loc[cal2], atr_20_panel=P["atr20"][cols].loc[cal2], top_n=20, exit_buffer=40,
                 atr_mult=0.0, atr_min_floor=0.0, max_weight=0.075, slippage=0.002, use_trailing_stop=False, use_dma_exit=False,
                 weekly_rank_check=False, membership_fn=mfn, initial_capital=1_000_000)
ea = a["equity"].set_index("date")["pv"]; eb = b["equity"].set_index("date")["pv"]
i = ea.index.intersection(eb.index)
print(f"  S2 engine end pv {ea.iloc[-1]:.0f}, clean engine {eb.iloc[-1]:.0f}; max abs rel diff on common dates {float((ea[i]/eb[i]-1).abs().max()):.2e}; trades {len(a['trades'])} vs {len(b['trades'])}")
