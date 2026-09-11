"""Day-by-day review of the last 120 trading days: the two new books, the two legacy production books, benchmarks. HTML -> PDF."""
import sys, io, base64, subprocess, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
import run as MM; import windows as W, importlib.util
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sp = importlib.util.spec_from_file_location("om25_run", "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib/run.py"); OM = importlib.util.module_from_spec(sp); sp.loader.exec_module(OM)
OUT = MM.RUNS.parent / "report"; OUT.mkdir(exist_ok=True)
MMS = dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None, dyn_n_bear=15, dyn_mode="hold", bear_buffer=20, trailing_stop=0.2, sizing="invvol", max_weight=0.10, regime_kind="roc", roc_n=31, confirm=3, sector_cap=5, cadence="monthly", stop_check="monthly")
OMC = dict(universe="nifty250", score="5050", regimes=1, top_n=25, exit_buffer=10, trailing_stop=0.2, return_filter=True, lookback=252, min_obs=220, exit_cadence="same", start="2010-01-01", end=None)
L6 = dict(universe="nse500", kind="voladj", lookback=126, min_obs=110, skip=0, top_n=24, exit_buffer=0, cadence="weekly_thu", exit_cadence="same", max_weight=0.075, min_hold_days=8, trailing_stop=0.0, start="2010-01-01", end=None)
def run(mod, cfg): c, _ = mod.run_candidate(**cfg); rid = mod.cfg_id(c); d = mod.RUNS / rid; return pd.read_csv(d / "equity.csv", parse_dates=["date"]).set_index("date"), pd.read_csv(d / "trades.csv", parse_dates=["date"])
mm_eq, mm_tr = run(MM, MMS); om_eq, om_tr = run(OM, OMC); l6h_eq, l6h_tr = run(MM, L6)
def load(p, col="close"):
    d = pd.read_csv(p); dc = [c for c in d.columns if "date" in c.lower()][0]; d[dc] = pd.to_datetime(d[dc]); s = d.set_index(dc)[col].sort_index(); return s[~s.index.duplicated()]
prod_l6 = load("/Users/navdeep/kite-lab/data/l6_v2_portfolios/l6_v2_portfolio_20260823_173015/l6_equity.csv", "pv"); prod_om = load("/Users/navdeep/kite-lab/data/om25_v3_portfolios/om25_v3_portfolio_20260823_172947/om25_equity.csv", "pv")
prod_l6_tr = pd.read_csv("/Users/navdeep/kite-lab/data/l6_v2_portfolios/l6_v2_portfolio_20260823_173015/l6_trades.csv", parse_dates=["date"]); prod_om_tr = pd.read_csv("/Users/navdeep/kite-lab/data/om25_v3_portfolios/om25_v3_portfolio_20260823_172947/om25_trades.csv", parse_dates=["date"])
n500 = load("/Users/navdeep/kite-lab/data/master/benchmarks/NIFTY_500.csv"); n100 = load("/Users/navdeep/kite-lab/data/master/benchmarks/NIFTY_100.csv"); ms = load("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv")
cal = mm_eq.index; days = cal[-120:]; a, z = days[0], days[-1]
S = {"MM (new)": mm_eq.pv, "OM25 (new, 2026 pick)": om_eq.pv, "L6 v2 production": prod_l6, "OM25 v3 production": prod_om, "L6 v2 rules, honest store": l6h_eq.pv, "Nifty 500": n500, "MidSmall 400": ms, "NIFTY 100": n100}
REAL_END = {k: v.index[v.index <= z][-1] for k, v in S.items()}   # last real observation per series; production files end 2026-08-21
S = {k: v.reindex(days).ffill().where(pd.Series(days, index=days) <= REAL_END[k]) for k, v in S.items()}
roc = OM.roc_regime(OM.REGIME_INDEX, 31, 3, cal).reindex(days).ffill().fillna(True).astype(bool)
# ---- stats
def stats(s):
    s = s.dropna(); r = s.pct_change().dropna(); hw = s.cummax(); dd = s / hw - 1
    neg = (r < 0).astype(int); streak = (neg * (neg.groupby((neg != neg.shift()).cumsum()).cumcount() + 1)).max()
    return dict(ret=100 * (s.iloc[-1] / s.iloc[0] - 1), maxdd=100 * dd.min(), worst=100 * r.min(), best=100 * r.max(), pos=100 * (r > 0).mean(), streak=int(streak), below=int((dd < 0).sum()), n=len(r), vol=100 * r.std() * np.sqrt(252), last=str(s.index[-1].date()))
ST = {k: stats(v) for k, v in S.items()}
# ---- actions
def actions(tr, name):
    t = tr[(tr.date >= a) & (tr.date <= z)].copy(); t["book"] = name; return t
A = pd.concat([actions(mm_tr, "MM"), actions(om_tr, "OM25"), actions(prod_l6_tr, "L6 prod"), actions(prod_om_tr, "OM25 v3 prod")])
act = A.groupby(["book", A.date.dt.date]).agg(buys=("side", lambda x: (x == "BUY").sum()), sells=("side", lambda x: (x == "SELL").sum()), names=("symbol", lambda x: ", ".join(sorted(set(x))[:8]) + (" …" if len(set(x)) > 8 else "")), reasons=("reason", lambda x: ", ".join(sorted(set(x))))).reset_index()
act_days = act.groupby("book").date.nunique().to_dict(); n_orders = act.groupby("book").apply(lambda g: int(g.buys.sum() + g.sells.sum())).to_dict()
# ---- charts
C = {"MM (new)": "#1f4e79", "OM25 (new, 2026 pick)": "#2e8b57", "L6 v2 production": "#c0504d", "OM25 v3 production": "#e8a33d", "L6 v2 rules, honest store": "#e0a0a0", "Nifty 500": "#7f7f7f", "MidSmall 400": "#9bbb59", "NIFTY 100": "#bfbfbf"}
def png(fig): b = io.BytesIO(); fig.savefig(b, format="png", dpi=160, bbox_inches="tight"); plt.close(fig); return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25})
fig, ax = plt.subplots(figsize=(9.5, 3.6))
for k, s in S.items(): s = s.dropna(); ax.plot(s.index, 100 * (s / s.iloc[0] - 1), color=C[k], lw=1.6 if "new" in k else 1.0, ls="--" if "production" in k or "honest" in k else "-", label=k)
bear = ~roc; 
for i in range(len(days)):
    if bear.iloc[i]: ax.axvspan(days[i] - pd.Timedelta(hours=12), days[i] + pd.Timedelta(hours=12), color="#f4d6d6", alpha=0.35, lw=0)
ax.set_title(f"Last 120 trading days, {a.date()} → {z.date()}: cumulative return, % (shaded = ROC31 regime bear)"); ax.legend(frameon=False, ncol=4, fontsize=7); img1 = png(fig)
fig, ax = plt.subplots(figsize=(9.5, 2.4))
for k in ["MM (new)", "OM25 (new, 2026 pick)", "L6 v2 production", "OM25 v3 production", "Nifty 500"]: s = S[k].dropna(); ax.plot(s.index, 100 * (s / s.cummax() - 1), color=C[k], lw=1.2, label=k)
ax.set_title("Drawdown from the window's running high, %"); ax.legend(frameon=False, ncol=5, fontsize=7); img2 = png(fig)
fig, ax = plt.subplots(figsize=(9.5, 2.0)); ax.plot(days, mm_eq.holdings.reindex(days), color=C["MM (new)"], label="MM names held"); ax.plot(days, om_eq.holdings.reindex(days), color=C["OM25 (new, 2026 pick)"], label="OM25 names held"); ax2 = ax.twinx(); ax2.plot(days, 100 * mm_eq.cash_pct.reindex(days), color=C["MM (new)"], ls=":", label="MM cash %"); ax2.set_ylim(0, 60)
ax.set_title("Names held (left) and MM cash % (right, dotted)"); ax.legend(frameon=False, loc="lower left", fontsize=7); img3 = png(fig)
# ---- tables
def pct(v, d=1): return f"{v:+.{d}f}%"
summ = "<table><thead><tr><th>Series</th><th>120-day return</th><th>Max DD in window</th><th>Worst day</th><th>Best day</th><th>Up days</th><th>Longest losing streak</th><th>Days below running high</th><th>Ann. vol</th><th>Order days</th><th>Orders</th><th>Data to</th></tr></thead><tbody>"
for k, s in ST.items():
    b = {"MM (new)": "MM", "OM25 (new, 2026 pick)": "OM25", "L6 v2 production": "L6 prod", "OM25 v3 production": "OM25 v3 prod"}.get(k)
    summ += f"<tr><td>{k}</td><td>{pct(s['ret'])}</td><td>{s['maxdd']:.1f}%</td><td>{s['worst']:.1f}%</td><td>{pct(s['best'])}</td><td>{s['pos']:.0f}%</td><td>{s['streak']}</td><td>{s['below']} of {s['n']}</td><td>{s['vol']:.0f}%</td><td>{act_days.get(b, '') if b else ''}</td><td>{n_orders.get(b, '') if b else ''}</td><td>{s['last']}</td></tr>"
summ += "</tbody></table>"
acts = "<table><thead><tr><th>Date</th><th>Book</th><th>Buys</th><th>Sells</th><th>Reasons</th><th>Names</th></tr></thead><tbody>" + "".join(f"<tr><td>{r.date}</td><td>{r.book}</td><td>{r.buys}</td><td>{r.sells}</td><td>{r.reasons}</td><td style='white-space:normal;text-align:left'>{r.names}</td></tr>" for _, r in act.sort_values(["date", "book"]).iterrows()) + "</tbody></table>"
R = pd.DataFrame({k: 100 * v.pct_change() for k, v in S.items()}).loc[days]; CUM = pd.DataFrame({k: 100 * (v / v.iloc[0] - 1) for k, v in S.items()}).loc[days]
mmact = act[act.book == "MM"].set_index("date"); omact = act[act.book == "OM25"].set_index("date")
def cell(v): 
    if pd.isna(v): return "<td></td>"
    c = f"rgba(31,78,121,{min(abs(v)/3,1)*0.5:.2f})" if v >= 0 else f"rgba(192,80,77,{min(abs(v)/3,1)*0.5:.2f})"; return f"<td style='background:{c}'>{v:+.1f}</td>"
cols = ["MM (new)", "OM25 (new, 2026 pick)", "L6 v2 production", "OM25 v3 production", "Nifty 500", "MidSmall 400"]
daily = "<table class='heat'><thead><tr><th>Date</th><th>Regime</th>" + "".join(f"<th>{c}<br>day / cum</th>" for c in cols) + "<th>MM orders</th><th>OM25 orders</th></tr></thead><tbody>"
for d in days:
    dd = d.date(); mo = mmact.loc[dd] if dd in mmact.index else None; oo = omact.loc[dd] if dd in omact.index else None
    daily += f"<tr><td>{dd}</td><td>{'bull' if roc.loc[d] else '<b>bear</b>'}</td>" + "".join(cell(R.loc[d, c]) + f"<td class='cum'>{CUM.loc[d, c]:+.1f}</td>" for c in cols) + f"<td>{'' if mo is None else f'{int(mo.buys)}B/{int(mo.sells)}S'}</td><td>{'' if oo is None else f'{int(oo.buys)}B/{int(oo.sells)}S'}</td></tr>"
daily += "</tbody></table>"
css = "<style>@page{size:A4 landscape;margin:10mm}body{font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:8.5px;color:#222;margin:0}h1{font-size:18px;margin:0 0 2px}h2{font-size:12px;margin:12px 0 5px;border-bottom:1px solid #ccc}p{margin:3px 0;line-height:1.35}.sub{color:#666;font-size:9px}table{border-collapse:collapse;width:100%;margin:4px 0 8px;page-break-inside:auto}th,td{border-bottom:1px solid #e6e6e6;padding:2px 4px;text-align:right;white-space:nowrap}th{background:#f3f5f8;font-weight:600;font-size:7.5px}th:first-child,td:first-child{text-align:left}.heat td{padding:1px 3px;font-size:7.5px}.heat td.cum{color:#555}img{width:100%;display:block;margin:4px 0}.pb{page-break-before:always}.note{background:#fbf7e8;border-left:3px solid #d9b44a;padding:5px 8px;margin:6px 0}</style>"
html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Last 120 trading days — day by day</title>{css}</head><body>
<h1>Last 120 trading days, day by day</h1><div class='sub'>{a.date()} → {z.date()} · new books from the honest store (net 20 bps); production books from their own pipeline files (to 2026-08-21, own price panel); benchmarks are price indices; MidSmall 400 real index to 2026-05 then spliced · generated 2026-09-11</div>
<div class='note'>Production series end on 2026-08-21 (their pipeline's last run), so their figures cover the window to that date; the new books and benchmarks run to 2026-09-09. The MidSmall 400 is the real index to 2026-05-08, then Midcap 150 plus the real Smallcap 250 to 2026-08-21, then Midcap 150 plus the point-in-time small-cap basket. Regime shading is the MM book's ROC31/c3 state as known each morning.</div>
<h2>Summary</h2>{summ}
<img src='{img1}'><img src='{img2}'><img src='{img3}'>
<div class='pb'></div><h2>Every order day in the window</h2>{acts}
<div class='pb'></div><h2>Day by day — daily return (coloured) and cumulative since day 1</h2>{daily}
</body></html>"""
(OUT / "review120.html").write_text(html)
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={OUT/'review120.pdf'}", str(OUT / "review120.html")], capture_output=True)
print("window", a.date(), z.date()); print(pd.DataFrame(ST).T[["ret", "maxdd", "worst", "pos", "streak", "below", "n", "last"]].round(1).to_string()); print("order days:", act_days, "orders:", n_orders)
print("bear days in window:", int((~roc).sum()), "| bear spells:", [(str(g.index[0].date()), str(g.index[-1].date())) for _, g in (~roc)[~roc].groupby(((~roc) != (~roc).shift()).cumsum())] if (~roc).any() else [])
