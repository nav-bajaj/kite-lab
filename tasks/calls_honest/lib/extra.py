"""(a) Why the S2 engine and the production engine differ by 0.8% in the equivalence check: tie ordering in the
percentile score (sort_values vs nlargest) and the trade-price fallback. (b) Like-for-like windows against the
earlier publications (stage2_portfolio RESULTS.md used IS 2010-01-04..2016-12-31 / OOS 2017+ with Sharpe at rf 0;
dip_vs_breakout_calls used 2010-06-01..2026-08-19 with tail from 2023-07-01)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import panels, universe, om, RUNS, W, load_equity, trade_stats, fmt
import s2 as S2

P = panels(); close = P["close"]; cal = close.index
cols, mfn, cfn, mask = universe("nse500")
sp = S2.build_stage2_panels(close[cols], mask, None, min_stage_age=0)
sf = S2.make_s2_score(sp, candidate_fn=cfn, hold_mode="strict", **S2.VARIANTS["E_rs_unext"])
wk = om.fridays(cal); wk = wk[(wk >= "2010-01-01") & (wk <= "2013-12-31")]
n_tie_dates = n_dates = 0; n_top_diff = 0
for d in wk:
    sc = sf(d).dropna()
    if sc.empty: continue
    n_dates += 1
    a = sc.sort_values(ascending=False).index[:20].tolist(); b = sc.nlargest(60).index[:20].tolist()
    if a != b: n_tie_dates += 1
    if set(a) != set(b): n_top_diff += 1
    if sc.duplicated().any(): pass
ties = sum(sf(d).dropna().duplicated().any() for d in wk[:50])
print(f"(a) {n_dates} signal dates: top-20 ORDER differs between sort_values and nlargest on {n_tie_dates}; top-20 SET differs on {n_top_diff}; tied scores present on {ties} of the first 50 dates")
nan_trade = int((P["trade"][cols].isna() & close[cols].notna()).loc["2010":"2013"].sum().sum())
print(f"    sessions 2010-13 with a close but no trade price: {nan_trade}")

print("(b) like-for-like windows")
for uni in ("nse500", "nifty250"):
    e = load_equity(f"s2_{uni}")
    for rf in (0.05, 0.0):
        a = W.stats(e, "2010-01-04", "2016-12-31", rf=rf); b = W.stats(e, "2017-01-01", "2099-12-31", rf=rf); c = W.stats(e, "2020-01-01", "2099-12-31", rf=rf)
        print(f"  S2 {uni} rf {rf:.0%}: IS 2010-01-04..2016 {fmt(a)} | OOS 2017-26 {fmt(b)} | 2020+ {fmt(c)}")
for uni in ("nse500", "nifty250"):
    eqd = pd.read_csv(RUNS / f"dip_{uni}" / "equity.csv", parse_dates=["date"]).set_index("date")
    for col, lab in (("pv", "net"), ("pv_gross_slot", "gross slot")):
        e = eqd[col].astype(float)
        full = W.stats(e, "2010-06-01", "2026-08-19"); tail = W.stats(e, "2023-07-01", "2026-08-19")
        w = [W.stats(e, a, b) for a, b in (("2010-06-01", "2016-12-31"), ("2017-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", "2099-12-31"))]
        print(f"  Dip {uni} {lab}: 2010-06..2026-08-19 {fmt(full)} | tail 2023-07+ {fmt(tail)} | IS 10-16 {fmt(w[0])} | 17-19 {fmt(w[1])} | 20-22 {fmt(w[2])} | 23-26 {fmt(w[3])}")
    calls = pd.read_csv(RUNS / f"dip_{uni}" / "calls.csv", parse_dates=["entry_date", "exit_date", "signal_date"])
    c = calls[(calls["signal_date"] >= "2010-06-01") & (calls["signal_date"] <= "2026-08-19")]
    t = trade_stats(c, (pd.Timestamp("2026-08-19") - pd.Timestamp("2010-06-01")).days / 30.4375, cal)
    print(f"    calls/yr {12*t['calls_per_month']:.1f}, win {100*t['win_rate']:.1f}%, mean {100*t['expectancy']:+.1f}%, median {100*t['median_pnl']:+.1f}%, p5 {100*t['p5']:.1f} p95 {100*t['p95']:.1f}, hold {t['median_hold_td']:.0f} td, stop exits {100*t['pct_stop']:.0f}%  (earlier biased: 58.5/yr, 51.6%, +20.1, +1.1, -21.2/+120.7, 76 td, 67%)")
