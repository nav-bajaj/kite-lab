"""§12 — Wright's Sharpe from their printed grid, the three-year comparison against the old books, and the medium-term hold diagnostic.

No new backtest parameters are searched here. L6 v2 and the OM25 current pick
are reproductions of existing books on the honest store, already registered.
"""
import sys, math, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
import run as MM, windows as W
import importlib.util
sp = importlib.util.spec_from_file_location("om25_run", "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib/run.py")
OM = importlib.util.module_from_spec(sp); sp.loader.exec_module(OM)
RF = 0.05

# ---------------- 1. Wright Momentum's Sharpe, from the factsheet grid ----------------
# Month-on-month performance, M-PDF p2 (percent). Zeros before Oct-2020 are pre-inception.
GRID = {2020: [0, 0, 0, 0, 0, 0, 0, 0, 0, 1.70, 5.20, 8.30],
        2021: [2.60, 15.60, 6.20, 8.30, 7.70, 3.70, 6.00, 0.60, 6.30, 2.00, 0.50, 8.10],
        2022: [1.10, -7.30, 9.10, -2.20, -8.90, -2.40, 11.60, 8.40, -2.20, -0.60, 1.80, -0.60],
        2023: [-3.40, -2.20, -1.40, 6.00, 5.30, 8.20, 8.60, 4.60, 3.00, -2.10, 10.40, 4.60],
        2024: [11.60, -4.60, -0.10, 5.50, -0.50, 6.50, 8.60, 4.00, 2.50, 1.60, -4.40, 0.30],
        2025: [-10.30, -9.00, 7.10, 2.60, 4.90, 4.50, 0.30, -5.60, 4.00, 2.70, -0.40, -1.50],
        2026: [-5.90, 1.90, -10.60, 17.20, 4.60, -0.60, -3.70, 8.30, None, None, None, None]}
wr = pd.Series({pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0): v / 100
                for y, vs in GRID.items() for m, v in enumerate(vs, 1) if v is not None})
wr = wr[wr.index >= "2020-10-01"].sort_index()

def monthly_stats(r, label):
    """Stats from monthly returns: CAGR, annualised monthly vol, Sharpe on that vol, month-end max DD."""
    cum = (1 + r).cumprod(); yrs = len(r) / 12
    cagr = cum.iloc[-1] ** (1 / yrs) - 1
    vol = r.std(ddof=1) * math.sqrt(12); dn = r[r < 0].std(ddof=1) * math.sqrt(12)
    dd = (cum / cum.cummax()).min() - 1
    return dict(book=label, months=len(r), cagr=100 * cagr, vol=100 * vol, sharpe=(cagr - RF) / vol,
                sortino=(cagr - RF) / dn, maxdd=100 * dd, calmar=cagr / abs(dd),
                best=100 * r.max(), worst=100 * r.min(), pos=100 * (r > 0).mean())

# our books on the same 71 months, same monthly basis
STACK = dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None,
             dyn_n_bear=15, dyn_mode="hold", bear_buffer=20, trailing_stop=0.2, sizing="invvol", max_weight=0.10,
             regime_kind="roc", roc_n=31, confirm=3, sector_cap=5, cadence="monthly", stop_check="monthly")
OM_PICK = dict(universe="nifty250", score="5050", regimes=1, top_n=25, exit_buffer=10, trailing_stop=0.2,
               return_filter=True, lookback=252, min_obs=220, exit_cadence="same", start="2010-01-01", end=None)
L6 = dict(kind="voladj", lookback=126, min_obs=110, skip=0, top_n=24, exit_buffer=0, min_hold_days=8,
          max_weight=0.075, cadence="weekly_thu", exit_cadence="same", trailing_stop=0.0, start="2010-01-01", end=None)

def mm_eq(**kw):
    cfg, _ = MM.run_candidate(**kw); return W.equity(MM.RUNS / MM.cfg_id(cfg)), MM.cfg_id(cfg)
def om_eq(**kw):
    cfg, _ = OM.run_candidate(**kw); return W.equity(OM.RUNS / OM.cfg_id(cfg)), OM.cfg_id(cfg)

books = {}
books["MM stack (Nifty 250)"], mm_id = mm_eq(**STACK)
books["OM25 current pick (Nifty 250)"], _ = om_eq(**OM_PICK)
books["L6 v2 rules (NSE 500)"], _ = mm_eq(**L6, universe="nse500")
books["L6 v2 rules (Nifty 250)"], _ = mm_eq(**L6, universe="nifty250")
END = min(e.index[-1] for e in books.values())

def load(p):
    d = pd.read_csv(p); dc = [c for c in d.columns if "date" in c.lower()][0]; d[dc] = pd.to_datetime(d[dc])
    s = d.set_index(dc)["close"].sort_index(); return s[~s.index.duplicated()]
ms400 = load("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv")
n500 = load("/Users/navdeep/kite-lab/data/master/benchmarks/NIFTY_500.csv")

print("=" * 100)
print("1. WRIGHT MOMENTUM'S SHARPE  (Oct-2020 to Aug-2026, from the printed month-on-month grid, M-PDF p2)")
print("   All rows on the SAME basis: monthly returns, rf 5%, annualised monthly vol, month-end drawdown.")
print("   Wright is gross of costs and fees; our books are net of 20 bps each way.")
print("=" * 100)
rows = [monthly_stats(wr, "Wright Momentum (published, gross)")]
for name, e in books.items():
    m = e.resample("ME").last().pct_change().dropna()
    m = m[(m.index >= "2020-10-01") & (m.index <= "2026-08-31")]
    rows.append(monthly_stats(m, name + " (net)"))
for lab, s in [("MidSmall 400 (synthetic)", ms400), ("Nifty 500", n500)]:
    m = s.resample("ME").last().pct_change().dropna(); m = m[(m.index >= "2020-10-01") & (m.index <= "2026-08-31")]
    rows.append(monthly_stats(m, lab))
w = pd.DataFrame(rows).set_index("book")
print(w.round(2).to_string())
print("\nNOTE: our project convention elsewhere is Sharpe on DAILY volatility, which is not the same number.")
for name, e in list(books.items())[:1]:
    d = e[(e.index >= "2020-10-01") & (e.index <= "2026-08-31")]
    r = d.pct_change().dropna(); yrs = (d.index[-1] - d.index[0]).days / 365.25
    cagr = (d.iloc[-1] / d.iloc[0]) ** (1 / yrs) - 1; dv = r.std() * math.sqrt(252)
    print(f"  {name}: daily-vol Sharpe {(cagr-RF)/dv:.2f} vs monthly-vol Sharpe {w.loc[name+' (net)','sharpe']:.2f}")

# ---------------- 2. three-year comparison ----------------
print("\n" + "=" * 100)
print(f"2. THE LAST THREE YEARS  (2023-01-01 to {END.date()}) — new book against the old ones, honest store, all net of 20 bps")
print("=" * 100)
def daily_stats(e, a, z, label):
    s = e[(e.index >= a) & (e.index <= z)]; r = s.pct_change().dropna()
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1; vol = r.std() * math.sqrt(252)
    dn = r[r < 0].std() * math.sqrt(252); dd = (s / s.cummax()).min() - 1
    return dict(book=label, cagr=100 * cagr, vol=100 * vol, sharpe=(cagr - RF) / vol, sortino=(cagr - RF) / dn,
                maxdd=100 * dd, calmar=cagr / abs(dd), total=100 * (s.iloc[-1] / s.iloc[0] - 1))
for a, z, tag in [("2023-01-01", str(END.date()), "last 3 years"), ("2016-01-01", str(END.date()), "2016-26 for reference")]:
    print(f"\n--- {tag} ({a} to {z}) ---")
    rr = [daily_stats(e, a, z, n) for n, e in books.items()]
    for lab, s in [("MidSmall 400 (synthetic)", ms400), ("Nifty 500", n500)]:
        rr.append(daily_stats(s.reindex(books["MM stack (Nifty 250)"].index).ffill().dropna(), a, z, lab))
    print(pd.DataFrame(rr).set_index("book").round(2).to_string())

# ---------------- 3. medium-term hold diagnostic ----------------
print("\n" + "=" * 100)
print("3. THE MEDIUM-TERM HOLD PROBLEM — MM stack, why 61-120 day trades average negative")
print("=" * 100)
x = pd.read_csv(MM.RUNS / mm_id / "exits.csv", parse_dates=["entry_date", "exit_date"])
x["bucket"] = pd.cut(x.hold_days, [0, 30, 60, 120, 250, 10000], labels=["0-30", "31-60", "61-120", "121-250", "251+"])
x["stop"] = x.reason.str.contains("stop", case=False)
g = x.groupby("bucket", observed=True).agg(n=("pnl_pct", "size"), share=("pnl_pct", lambda s: 100 * len(s) / len(x)),
                                           avg=("pnl_pct", lambda s: 100 * s.mean()), med=("pnl_pct", lambda s: 100 * s.median()),
                                           win=("pnl_pct", lambda s: 100 * (s > 0).mean()), stop_share=("stop", lambda s: 100 * s.mean()))
print("\nBy holding bucket (all exits, 2010-26):"); print(g.round(1).to_string())
print("\nSplit by exit reason inside each bucket — avg P&L %, and n:")
pv = x.pivot_table(index="bucket", columns=x.stop.map({True: "stop exit", False: "rank exit"}), values="pnl_pct",
                   aggfunc=[lambda s: 100 * s.mean(), "size"], observed=True)
pv.columns = [f"{b} {a.replace('<lambda>','avg')}" for a, b in pv.columns]
print(pv.round(1).to_string())
print("\nContribution to total P&L (sum of pnl_pct, a rough proxy — positions are not equal-sized):")
c = x.groupby("bucket", observed=True).pnl_pct.sum() * 100
print(c.round(0).to_string())
print("\nSame table restricted to 2016-26:")
x2 = x[x.exit_date >= "2016-01-01"]
g2 = x2.groupby("bucket", observed=True).agg(n=("pnl_pct", "size"), avg=("pnl_pct", lambda s: 100 * s.mean()),
                                             med=("pnl_pct", lambda s: 100 * s.median()), win=("pnl_pct", lambda s: 100 * (s > 0).mean()),
                                             stop_share=("stop", lambda s: 100 * s.mean()))
print(g2.round(1).to_string())
print("\ndone")
