"""Tables for RESULTS.md from runs/. Prints markdown; also writes runs/report_tables.md."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import panels, load_equity, equity_stats, trade_stats, trade_stats_by_year, fmt, RUNS, MM_BASE, LEGS, W

cal = panels()["close"].index
lines = []
P = lambda s="": lines.append(s)
pc = lambda x: f"{100*x:.1f}%"
NAMES = {"s2": "Stage-2 (S2-v2)", "dip": "Dip feed (dip25_ts20)"}
UNI = {"nse500": "NSE 500", "nifty250": "Nifty 250"}
res = {}
for strat in ("s2", "dip"):
    for uni in ("nse500", "nifty250"):
        name = f"{strat}_{uni}"
        eq = load_equity(name)
        calls = pd.read_csv(RUNS / name / "calls.csv", parse_dates=["entry_date", "exit_date"])
        es = equity_stats(eq)
        months = (eq.index[-1] - eq.index[0]).days / 30.4375
        ts = trade_stats(calls, months, cal)
        ty = trade_stats_by_year(calls, cal, es["years"])
        extra = {}
        if strat == "dip":
            eqd = pd.read_csv(RUNS / name / "equity.csv", parse_dates=["date"]).set_index("date")
            extra["gross"] = equity_stats(eqd["pv_gross_slot"].astype(float))
            extra["holdings"] = float(eqd["holdings"].mean()); extra["pct_full"] = float((eqd["holdings"] >= 25).mean())
        else:
            eqd = pd.read_csv(RUNS / name / "equity.csv", parse_dates=["date"]).set_index("date")
            extra["holdings"] = float(eqd["holdings"].mean()); extra["invested"] = float((1 - eqd["cash_pct"]).mean())
            extra["pct_under50"] = float(((1 - eqd["cash_pct"]) < 0.5).mean())
        res[name] = dict(es=es, ts=ts, ty=ty, calls=calls, extra=extra, end=str(eq.index[-1].date()))

P("## Headline windows (CAGR / Sharpe rf 5% / max drawdown)"); P()
P("| Strategy | Universe | IS 2010-15 | OOS 2016-26 | 2016-19 | 2020-22 | 2023-26 | Wright Oct-20 to Aug-26 | Calls/month |")
P("|---|---|---|---|---|---|---|---|---|")
for strat in ("s2", "dip"):
    for uni in ("nse500", "nifty250"):
        r = res[f"{strat}_{uni}"]; es = r["es"]
        P(f"| {NAMES[strat]} | {UNI[uni]} | {fmt(es['IS 2010-15'])} | **{fmt(es['OOS 2016-26'])}** | {fmt(es['2016-19'])} | {fmt(es['2020-22'])} | {fmt(es['2023-26'])} | {fmt(es['Wright Oct-20 to Aug-26'])} | {r['ts']['calls_per_month']:.1f} |")
for uni in ("nse500", "nifty250"):
    b = MM_BASE[uni]
    P(f"| MM base (mm_rebuild §9) | {UNI[uni]} | - | **{b['cagr']:.1f}% / {b['sharpe']:.2f} / {b['maxdd']:.0f}%** | {b['subs'][0]:.2f} | {b['subs'][1]:.2f} | {b['subs'][2]:.2f} | {b['wright'][0]:.1f}% / {b['wright'][1]:.2f} / {b['wright'][2]:.0f}% | {b['trades']/12:.1f} (trades) |")
P()
P("Dip feed, the branch's gross slot curve (raw closes, no slippage) on the same honest panel, for comparison with the earlier 37.8% / 1.65:"); P()
P("| Universe | IS 2010-15 | OOS 2016-26 | 2016-19 | 2020-22 | 2023-26 | Full 2010-26 |")
P("|---|---|---|---|---|---|---|")
for uni in ("nse500", "nifty250"):
    g = res[f"dip_{uni}"]["extra"]["gross"]
    eqg = pd.read_csv(RUNS / f"dip_{uni}" / "equity.csv", parse_dates=["date"]).set_index("date")["pv_gross_slot"].astype(float)
    full = W.stats(eqg, "2010-01-01", "2099-12-31")
    P(f"| {UNI[uni]} | {fmt(g['IS 2010-15'])} | {fmt(g['OOS 2016-26'])} | {fmt(g['2016-19'])} | {fmt(g['2020-22'])} | {fmt(g['2023-26'])} | {fmt(full)} |")
P()
P("## Up / down capture vs MidSmall 400 (monthly; compound mean in the index's up / down months, portfolio over index)"); P()
P("| Strategy | Universe | Wright window up | down | beats index in up / down months | Long run 2011-26 up | down |")
P("|---|---|---|---|---|---|---|")
for strat in ("s2", "dip"):
    for uni in ("nse500", "nifty250"):
        es = res[f"{strat}_{uni}"]["es"]; cw, cl = es["capture_wright"], es["capture_long"]
        P(f"| {NAMES[strat]} | {UNI[uni]} | {cw[0]:.2f} | **{cw[1]:.2f}** | {100*cw[2]:.0f}% / {100*cw[3]:.0f}% | {cl[0]:.2f} | {cl[1]:.2f} |")
for uni in ("nse500", "nifty250"):
    b = MM_BASE[uni]; P(f"| MM base | {UNI[uni]} | {b['capture'][0]:.2f} | {b['capture'][1]:.2f} | 58% / 35% | 1.08 | 0.80 |" if uni == "nse500" else f"| MM base | {UNI[uni]} | {b['capture'][0]:.2f} | {b['capture'][1]:.2f} | 51% / 52% | 0.94 | 0.66 |")
P("| Wright (ex-costs) | - | 1.11 | 0.90 | 62% / 57% | - | - |")
P()
P("## Leg returns, % (MidSmall 400 legs as in mm_rebuild §7)"); P()
hdr = " | ".join(l for l, _, _ in LEGS)
P(f"| Book | {hdr} | Calendar 2021 |"); P("|---|" + "---|" * (len(LEGS) + 1))
li = res["s2_nse500"]["es"]["legs_index"]
P("| MidSmall 400 | " + " | ".join(f"{li[l]:.1f}" for l, _, _ in LEGS) + " | 51.3 |")
for strat in ("s2", "dip"):
    for uni in ("nse500", "nifty250"):
        es = res[f"{strat}_{uni}"]["es"]; lg = es["legs"]
        P(f"| {NAMES[strat]}, {UNI[uni]} | " + " | ".join(f"{lg[l]:.1f}" for l, _, _ in LEGS) + f" | {es['years'].get(2021, np.nan):.1f} |")
for uni in ("nse500", "nifty250"):
    b = MM_BASE[uni]; P(f"| MM base, {UNI[uni]} | " + " | ".join(f"{v:.0f}" for v in b["legs"]) + (" | 69.7 |" if uni == "nse500" else " | 56.8 |"))
P()
P("## Trade-level statistics, 2010-01 to store end (P&L net of 20 bps each way)"); P()
P("| Strategy | Universe | Calls | Calls/month | Open at end | Win rate | Avg winner | Avg loser | Expectancy | Median call | p5 / p95 | Calls > +50% | Hold median / mean (cal days) | Hold median / mean (sessions) | Exits by stop / rule | Open book mean P&L |")
P("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for strat in ("s2", "dip"):
    for uni in ("nse500", "nifty250"):
        t = res[f"{strat}_{uni}"]["ts"]
        P(f"| {NAMES[strat]} | {UNI[uni]} | {t['n_calls']} | {t['calls_per_month']:.1f} | {t['n_open']} | {pc(t['win_rate'])} | {pc(t['avg_win'])} | {pc(t['avg_loss'])} | {pc(t['expectancy'])} | {pc(t['median_pnl'])} | {pc(t['p5'])} / {pc(t['p95'])} | {pc(t['pct_gt_50'])} | {t['median_hold_cd']:.0f} / {t['mean_hold_cd']:.0f} | {t['median_hold_td']:.0f} / {t['mean_hold_td']:.0f} | {pc(t['pct_stop'])} / {pc(t['pct_rule'])} | {pc(t['open_mean_pnl'])} |")
P()
P("Book shape: " + "; ".join(f"{NAMES[s]} {UNI[u]} mean holdings {res[f'{s}_{u}']['extra']['holdings']:.1f}" + (f", invested {pc(res[f'{s}_{u}']['extra']['invested'])}, under 50% invested {pc(res[f'{s}_{u}']['extra']['pct_under50'])} of days" if s == "s2" else f", at cap {pc(res[f'{s}_{u}']['extra']['pct_full'])} of days") for s in ("s2", "dip") for u in ("nse500", "nifty250")) + ".")
P()
for strat in ("s2", "dip"):
    for uni in ("nse500", "nifty250"):
        r = res[f"{strat}_{uni}"]; ty = r["ty"]
        P(f"### By calendar year of entry: {NAMES[strat]}, {UNI[uni]}"); P()
        P("| Year | Calls | Win rate | Avg winner | Avg loser | Expectancy | Median hold (cal days) | Exits by stop | Portfolio return |"); P("|---|---|---|---|---|---|---|---|---|")
        for _, y in ty.iterrows():
            P(f"| {int(y['year'])} | {int(y['calls'])} | {pc(y['win_rate'])} | {pc(y['avg_win']) if y['avg_win'] == y['avg_win'] else '-'} | {pc(y['avg_loss']) if y['avg_loss'] == y['avg_loss'] else '-'} | {pc(y['expectancy'])} | {y['median_hold_cd']:.0f} | {pc(y['pct_stop'])} | {y['port_ret']:.1f}% |")
        P()
        ex = r["calls"][r["calls"]["status"] == "closed"]["reason"].value_counts()
        P("Exit mix (closed calls): " + ", ".join(f"{k} {v}" for k, v in ex.items()) + f". Store end {r['end']}."); P()
txt = "\n".join(lines); (RUNS / "report_tables.md").write_text(txt); print(txt)
