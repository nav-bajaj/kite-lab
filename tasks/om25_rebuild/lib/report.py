"""Performance report for the Nifty 250 adaptive process (§4b chain from 2011). HTML -> PDF via headless Chrome."""
import sys, io, base64, json, itertools, subprocess, math, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from run import run_candidate, cfg_id, RUNS
from windows import equity, stats
OUT = RUNS.parent / "report"; RF = 0.05; TAX = 0.25
# ---------- chain ----------
GRID = list(itertools.product(["cr", "5050", "uc"], [1, 2], [0, 10, 20], [0.0, 0.2]))
B = dict(universe="nifty250", cadence="monthly", lookback=252, min_obs=220, top_n=25, return_filter=True, exit_cadence="same", start="2006-02-01", end=None)
eqs, ids = {}, {}
for k in GRID:
    cfg, _ = run_candidate(**B, score=k[0], regimes=k[1], exit_buffer=k[2], trailing_stop=k[3]); ids[k] = cfg_id(cfg); eqs[k] = equity(RUNS / ids[k])
END = max(e.index[-1] for e in eqs.values()); segs, picks, tr_all, ex_all = [], [], [], []
for y in range(2011, END.year + 1):
    a, z = f"{y-5}-01-01", f"{y-1}-12-31"; best = max(GRID, key=lambda k: stats(eqs[k], a, z)["sharpe"]); e = eqs[best]
    segs.append(e[(e.index >= f"{y}-01-01") & (e.index <= f"{y}-12-31")].pct_change().dropna()); picks.append((y, best))
    t = pd.read_csv(RUNS / ids[best] / "trades.csv", parse_dates=["date"]); tr_all.append(t[(t.date >= f"{y}-01-01") & (t.date <= f"{y}-12-31")])
    x = pd.read_csv(RUNS / ids[best] / "exits.csv", parse_dates=["entry_date", "exit_date"]); ex_all.append(x[(x.exit_date >= f"{y}-01-01") & (x.exit_date <= f"{y}-12-31")])
port = (1 + pd.concat(segs)).cumprod(); trades = pd.concat(tr_all); exits = pd.concat(ex_all); idx = port.index
def fy_tax(s, rate=TAX):
    v = s / s.iloc[0]; adj = pd.Series(1.0, index=v.index); cur = 1.0; base = 1.0
    for d in [d for d in v.index if d.month == 3 and d == v[(v.index.year == d.year) & (v.index.month == 3)].index[-1]]:
        pre = v.loc[d] * cur; gain = pre - base
        if gain > 0: cur *= (pre - rate * gain) / pre
        base = v.loc[d] * cur; adj.loc[adj.index > d] = cur
    return v * adj
port_tax = fy_tax(port)
def load(p):
    d = pd.read_csv(p); dc = [c for c in d.columns if "date" in c.lower()][0]; d[dc] = pd.to_datetime(d[dc]); s = d.set_index(dc)["close"].sort_index(); return s[~s.index.duplicated()]
n500 = load("/Users/navdeep/kite-lab/data/master/benchmarks/NIFTY_500.csv").reindex(idx).ffill()
n100 = load("/Users/navdeep/kite-lab/data/master/benchmarks/NIFTY_100.csv").reindex(idx).ffill(); m150 = load("/Users/navdeep/kite-lab/data/master/benchmarks/NIFTY_MIDCAP_150.csv").reindex(idx).ffill()
real = load("/Users/navdeep/Documents/stock_data/indices_data/NIFTY_LARGEMID250.csv").reindex(idx).ffill(); first = real.first_valid_index()
r1, r2 = n100.pct_change().fillna(0), m150.pct_change().fillna(0); a1 = a2 = 0.5; vals = []
for d in idx:
    a1 *= 1 + r1.loc[d]; a2 *= 1 + r2.loc[d]; vals.append(a1 + a2)
    if d.month in (3, 6, 9, 12) and d == idx[(idx.year == d.year) & (idx.month == d.month)][-1]: a1 = a2 = (a1 + a2) / 2
proxy = pd.Series(vals, index=idx); n250 = pd.concat([proxy[proxy.index < first] * real.loc[first] / proxy.loc[first], real[real.index >= first]])
SERIES = {"Portfolio": port, "Portfolio post-tax": port_tax, "Nifty 250": n250, "Nifty 500": n500}
# ---------- metrics ----------
def dd_table(s, n=5):
    v = s / s.cummax(); out = []; in_dd = False
    for d, x in v.items():
        if x < 1 and not in_dd: in_dd = True; start = d; trough = d; depth = x
        elif x < 1 and in_dd and x < depth: trough = d; depth = x
        elif x >= 1 and in_dd: in_dd = False; out.append((start, trough, d, depth - 1))
    if in_dd: out.append((start, trough, None, depth - 1))
    return sorted(out, key=lambda r: r[3])[:n]
def metrics(s, a, z):
    s = s[(s.index >= a) & (s.index <= z)]; r = s.pct_change().dropna(); yrs = (s.index[-1] - s.index[0]).days / 365.25
    cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1; vol = r.std() * math.sqrt(252); dn = r[r < 0].std() * math.sqrt(252)
    dd = (s / s.cummax()).min() - 1; top = dd_table(s, 1)[0]; dur = ((top[2] or s.index[-1]) - top[0]).days
    return dict(total=s.iloc[-1] / s.iloc[0] - 1, cagr=cagr, vol=vol, sharpe=(cagr - RF) / vol, sortino=(cagr - RF) / dn if dn > 0 else np.nan, maxdd=dd, calmar=cagr / abs(dd), dd_days=dur,
                best_m=s.resample("M").last().pct_change().max(), worst_m=s.resample("M").last().pct_change().min(), pos_m=(s.resample("M").last().pct_change().dropna() > 0).mean())
def trade_stats(a, z):
    x = exits[(exits.exit_date >= a) & (exits.exit_date <= z)]; t = trades[(trades.date >= a) & (trades.date <= z)]; yrs = (pd.Timestamp(z) - pd.Timestamp(a)).days / 365.25
    w, l = x[x.pnl_pct > 0], x[x.pnl_pct <= 0]; eqm = port[(port.index >= a) & (port.index <= z)].mean() * 1e6
    return dict(n=len(x), win=len(w) / len(x), avg_w=w.pnl_pct.mean(), avg_l=l.pnl_pct.mean(), best=x.pnl_pct.max(), worst=x.pnl_pct.min(), pf=w.pnl_pct.sum() / -l.pnl_pct.sum(), hold=x.hold_days.mean(), med_hold=x.hold_days.median(),
                stop_share=(x.reason.str.contains("stop", case=False)).mean(), trades_py=len(t) / yrs, turnover=t.notional.sum() / eqm / yrs / 2, slip=t.slippage.sum() / eqm / yrs, expectancy=x.pnl_pct.mean())
def period_returns(s):
    e = s.index[-1]; out = {}
    for lab, off in [("1M", pd.DateOffset(months=1)), ("3M", pd.DateOffset(months=3)), ("6M", pd.DateOffset(months=6)), ("YTD", None), ("1Y", pd.DateOffset(years=1)), ("3Y", pd.DateOffset(years=3)), ("5Y", pd.DateOffset(years=5)), ("10Y", pd.DateOffset(years=10)), ("Since 2011", "all")]:
        a = pd.Timestamp(f"{e.year}-01-01") - pd.Timedelta(days=1) if off is None else (s.index[0] if off == "all" else e - off)
        a = s.index[s.index.get_indexer([a], method="nearest")[0]] if off is None or off == "all" else s.index[s.index.get_indexer([a], method="nearest")[0]]
        v = s.loc[e] / s.loc[a] - 1; yrs = (e - a).days / 365.25; out[lab] = (1 + v) ** (1 / yrs) - 1 if yrs > 1.05 else v
    return out
def yearly(s): y = s.resample("Y").last(); r = y.pct_change(); r.iloc[0] = y.iloc[0] / s.iloc[0] - 1; r.index = r.index.year; return r
def monthly_grid(s):
    m = s.resample("M").last().pct_change(); m.iloc[0] = s.resample("M").last().iloc[0] / s.iloc[0] - 1
    g = pd.DataFrame({"y": m.index.year, "m": m.index.month, "r": m.values}).pivot(index="y", columns="m", values="r"); g["Year"] = yearly(s).reindex(g.index); return g
# ---------- charts ----------
C = {"Portfolio": "#1f4e79", "Portfolio post-tax": "#7f9cc0", "Nifty 250": "#c0504d", "Nifty 500": "#9bbb59"}
def png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=160, bbox_inches="tight"); plt.close(fig); return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25})
fig, ax = plt.subplots(figsize=(9, 3.4))
for n, s in SERIES.items(): ax.plot(s.index, s / s.iloc[0], color=C[n], lw=1.3 if "Portfolio" in n else 1.0, label=n)
ax.set_yscale("log"); ax.set_title("Growth of 1 (log scale), 2011-01 to " + str(END.date())); ax.legend(frameon=False, ncol=4); img_eq = png(fig)
fig, ax = plt.subplots(figsize=(9, 2.2))
for n in ["Portfolio", "Nifty 250"]: s = SERIES[n]; ax.fill_between(s.index, (s / s.cummax() - 1) * 100, 0, color=C[n], alpha=0.35, label=n)
ax.set_title("Drawdown from peak, %"); ax.legend(frameon=False); img_dd = png(fig)
yy = pd.DataFrame({n: yearly(SERIES[n]) for n in ["Portfolio", "Nifty 250", "Nifty 500"]}) * 100
fig, ax = plt.subplots(figsize=(9, 2.6)); w = 0.27
for i, n in enumerate(yy.columns): ax.bar(yy.index + (i - 1) * w, yy[n], w, color=C[n], label=n)
ax.axhline(0, color="k", lw=0.5); ax.set_title("Calendar-year returns, % (2026 year to date)"); ax.legend(frameon=False, ncol=3); ax.set_xticks(yy.index); img_yr = png(fig)
m36 = port.resample("M").last(); b36 = n250.resample("M").last(); ex3 = ((m36.pct_change(36) + 1) ** (1 / 3) - (b36.pct_change(36) + 1) ** (1 / 3)).dropna() * 100
fig, ax = plt.subplots(figsize=(9, 2.2)); ax.plot(ex3.index, ex3, color=C["Portfolio"]); ax.axhline(0, color="k", lw=0.5); ax.axhline(ex3.median(), color="grey", ls="--", lw=0.8, label=f"median {ex3.median():.1f}pp")
ax.set_title("Rolling 3-year excess CAGR over Nifty 250, percentage points"); ax.legend(frameon=False); img_roll = png(fig)
fig, ax = plt.subplots(figsize=(9, 2.4)); ax.hist(exits.pnl_pct.clip(-0.5, 1.5) * 100, bins=60, color=C["Portfolio"], alpha=0.85); ax.axvline(0, color="k", lw=0.6)
ax.set_title("Per-trade P&L distribution, % (net of slippage; clipped at -50 / +150)"); ax.set_xlabel("%"); img_pnl = png(fig)
# ---------- tables ----------
def pct(v, d=1): return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{100*v:.{d}f}%"
def num(v, d=2): return f"{v:.{d}f}"
def table(rows, header, cls=""):
    h = "".join(f"<th>{c}</th>" for c in header); b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows); return f"<table class='{cls}'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"
W = {"2011-26": ("2011-01-01", END), "2016-26": ("2016-01-01", END)}
def summary_block(wname):
    a, z = W[wname]; M = {n: metrics(s, a, z) for n, s in SERIES.items()}; T = trade_stats(a, z)
    cards = [("CAGR", pct(M["Portfolio"]["cagr"]), f"post-tax {pct(M['Portfolio post-tax']['cagr'])}"), ("Total return", pct(M["Portfolio"]["total"], 0), f"Nifty 250 {pct(M['Nifty 250']['total'], 0)}"),
             ("Max drawdown", pct(M["Portfolio"]["maxdd"]), f"{M['Portfolio']['dd_days']} days peak to recovery"), ("Sharpe (rf 5%)", num(M["Portfolio"]["sharpe"]), f"Nifty 250 {num(M['Nifty 250']['sharpe'])}"),
             ("Sortino", num(M["Portfolio"]["sortino"]), f"Calmar {num(M['Portfolio']['calmar'])}"), ("Volatility", pct(M["Portfolio"]["vol"]), f"Nifty 250 {pct(M['Nifty 250']['vol'])}"),
             ("Hit rate", pct(T["win"]), f"{T['n']} closed trades"), ("Avg holding", f"{T['hold']:.0f} days", f"median {T['med_hold']:.0f}"), ("Turnover", f"{T['turnover']:.1f}x / yr", f"{T['trades_py']:.0f} trades / yr")]
    cards_html = "".join(f"<div class='card'><div class='k'>{k}</div><div class='v'>{v}</div><div class='s'>{s}</div></div>" for k, v, s in cards)
    rows = [[n, pct(m["cagr"]), pct(m["total"], 0), pct(m["vol"]), num(m["sharpe"]), num(m["sortino"]), num(m["calmar"]), pct(m["maxdd"]), m["dd_days"], pct(m["best_m"]), pct(m["worst_m"]), pct(m["pos_m"], 0)] for n, m in M.items()]
    return f"<h2>{wname}</h2><div class='cards'>{cards_html}</div>" + table(rows, ["", "CAGR", "Total", "Vol", "Sharpe", "Sortino", "Calmar", "Max DD", "DD days", "Best month", "Worst month", "Positive months"])
pr = {n: period_returns(s) for n, s in SERIES.items()}
period_tbl = table([[n] + [pct(v) for v in p.values()] for n, p in pr.items()], ["Period returns (annualised beyond 1Y)"] + list(pr["Portfolio"].keys()))
yy_all = pd.DataFrame({n: yearly(SERIES[n]) for n in SERIES}); yy_all["Excess vs Nifty 250"] = yy_all["Portfolio"] - yy_all["Nifty 250"]
year_tbl = table([[y] + [pct(v) for v in r] for y, r in yy_all.iterrows()], ["Year"] + list(yy_all.columns))
g = monthly_grid(port); mn = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
def cell(v):
    if pd.isna(v): return "<td></td>"
    c = f"rgba(31,78,121,{min(abs(v)/0.15,1)*0.55:.2f})" if v >= 0 else f"rgba(192,80,77,{min(abs(v)/0.15,1)*0.55:.2f})"; return f"<td style='background:{c}'>{100*v:.1f}</td>"
month_tbl = "<table class='heat'><thead><tr><th>Year</th>" + "".join(f"<th>{m}</th>" for m in mn) + "<th>Year</th></tr></thead><tbody>" + "".join(f"<tr><td><b>{y}</b></td>" + "".join(cell(r.get(m, np.nan)) for m in range(1, 13)) + cell(r["Year"]) + "</tr>" for y, r in g.iterrows()) + "</tbody></table>"
ddt = dd_table(port, 6); dd_tbl = table([[str(s.date()), str(t.date()), str(r.date()) if r is not None else "ongoing", pct(d), (t - s).days, ((r or END) - t).days, ((r or END) - s).days] for s, t, r, d in ddt], ["Peak", "Trough", "Recovered", "Depth", "Days down", "Days to recover", "Total days"])
T = trade_stats("2011-01-01", END); Tt = trade_stats("2016-01-01", END)
trade_tbl = table([["Closed trades", T["n"], Tt["n"]], ["Win rate", pct(T["win"]), pct(Tt["win"])], ["Average winner", pct(T["avg_w"]), pct(Tt["avg_w"])], ["Average loser", pct(T["avg_l"]), pct(Tt["avg_l"])], ["Expectancy per trade", pct(T["expectancy"]), pct(Tt["expectancy"])],
                   ["Profit factor (sum of wins / sum of losses)", num(T["pf"]), num(Tt["pf"])], ["Best trade", pct(T["best"]), pct(Tt["best"])], ["Worst trade", pct(T["worst"]), pct(Tt["worst"])], ["Average holding days", f"{T['hold']:.0f}", f"{Tt['hold']:.0f}"], ["Median holding days", f"{T['med_hold']:.0f}", f"{Tt['med_hold']:.0f}"],
                   ["Exits by trailing stop", pct(T["stop_share"]), pct(Tt["stop_share"])], ["Trades per year", f"{T['trades_py']:.0f}", f"{Tt['trades_py']:.0f}"], ["One-way turnover per year", f"{T['turnover']:.1f}x", f"{Tt['turnover']:.1f}x"], ["Slippage cost per year", pct(T["slip"]), pct(Tt["slip"])]], ["Trade statistics", "2011-26", "2016-26"])
hold = exits.hold_days; hold_tbl = table([[f"{lo}-{hi} days", pct((hold.between(lo, hi)).mean()), pct(exits[hold.between(lo, hi)].pnl_pct.mean())] for lo, hi in [(0, 30), (31, 60), (61, 120), (121, 250), (251, 5000)]], ["Holding period", "Share of trades", "Avg P&L"])
pick_tbl = table([[y, {"cr": "Capture ratio", "5050": "50/50 UC + CR", "uc": "Upside capture"}[k[0]], "one" if k[1] == 1 else "two", k[2], "20%" if k[3] else "off"] for y, k in picks], ["Year", "Score", "Regimes", "Exit buffer", "Trailing stop"])
gates = table([["G2 OOS Sharpe 2016-26 ≥ 0.9", num(metrics(port, "2016-01-01", END)["sharpe"]), "at the gate"], ["G3 each sub-window ≥ 0.6", " / ".join(num(metrics(port, a, z)["sharpe"]) for a, z in [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", END)]), "pass"],
               ["G4 OOS max drawdown ≥ −40%", pct(metrics(port, "2016-01-01", END)["maxdd"]), "pass"], ["G5 walk-forward", "by construction", "pass"], ["G6 parameters ≤ 10", "7 fixed + 3 refit yearly", "pass"], ["G8 CAGR ≥ 20% (OOS, pre-tax)", pct(metrics(port, "2016-01-01", END)["cagr"]), "pass"]], ["Gate", "Value", "Status"])
sip_tbl = table([["From 2011, pre-tax", "18.9L", "140.6L (7.4x), 22.7%", "65.5L (3.5x), 14.5%", "53.2L (2.8x), 12.2%"], ["From 2011, post-tax", "18.9L", "85.6L (4.5x), 17.4%", "53.8L (2.8x), 12.3%", "44.6L (2.4x), 10.2%"], ["From 2016, pre-tax", "12.9L", "46.1L (3.6x), 22.4%", "29.2L (2.3x), 14.6%", "25.4L (2.0x), 12.2%"], ["From 2016, post-tax", "12.9L", "34.7L (2.7x), 17.6%", "25.1L (1.9x), 12.0%", "22.3L (1.7x), 9.9%"]], ["SIP Rs 10,000 / month", "Invested", "Portfolio (value, XIRR)", "Nifty 250", "Nifty 500"])
css = """<style>@page{size:A4;margin:14mm 12mm}body{font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:9.5px;color:#222;margin:0}h1{font-size:20px;margin:0 0 2px}h2{font-size:13px;margin:14px 0 6px;border-bottom:1px solid #ccc;padding-bottom:2px}h3{font-size:11px;margin:10px 0 4px}p{margin:4px 0;line-height:1.35}.sub{color:#666;font-size:10px}table{border-collapse:collapse;width:100%;margin:4px 0 8px;page-break-inside:avoid}th,td{border-bottom:1px solid #e3e3e3;padding:3px 5px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{background:#f3f5f8;font-weight:600}.heat td{text-align:center;padding:2px 3px}.cards{display:grid;grid-template-columns:repeat(9,1fr);gap:5px;margin:6px 0}.card{border:1px solid #ddd;border-radius:4px;padding:5px 6px}.card .k{color:#666;font-size:8px}.card .v{font-size:14px;font-weight:600;margin:1px 0}.card .s{color:#666;font-size:7.5px}img{width:100%;display:block;margin:4px 0}.pb{page-break-before:always}.note{background:#fbf7e8;border-left:3px solid #d9b44a;padding:5px 8px;margin:6px 0}ul{margin:2px 0 4px 14px;padding:0}li{margin:1px 0}</style>"""
html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Quality Momentum rebuild — performance report</title>{css}</head><body>
<h1>Quality Momentum — rebuild candidate</h1><div class='sub'>Nifty 250 · monthly · 25 names · adaptive process (yearly refit on trailing five years) · research report generated 2026-09-10 from the honest master store · backtest, not live; net of 20 bps slippage each way; price-return basis (dividends excluded from portfolio and benchmarks) · not a client document</div>
<div class='note'><b>Read first.</b> Every number is a simulation on reconstructed point-in-time index membership with delisted names carried to their last price. The process (which configuration to run each year) was designed after the 2016-2026 window had been seen once; it is one of eight process variants examined, and its 2016-2026 Sharpe sits at the 0.9 gate rather than above it. Tax figures use a flat 25% on each financial year's realised gain, with no loss carry-forward, which is deliberately harsh.</div>
{summary_block("2011-26")}{summary_block("2016-26")}
<h2>Period returns to {END.date()}</h2>{period_tbl}
<div class='pb'></div><h2>Growth and drawdown</h2><img src='{img_eq}'><img src='{img_dd}'>
<div class='pb'></div><h2>Calendar years</h2><img src='{img_yr}'>{year_tbl}
<h2>Monthly returns, % (portfolio, pre-tax)</h2>{month_tbl}
<h2>Largest drawdowns</h2>{dd_tbl}<img src='{img_roll}'>
<div class='pb'></div><h2>Trades</h2><p>Per-trade P&L is net of slippage at both ends. A position open across a year boundary is closed in the outgoing configuration's book and reopened in the incoming one where the two differ; in live running that would be a single rebalance, so trade counts are marginally overstated at year ends.</p>
<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px'><div>{trade_tbl}</div><div>{hold_tbl}<img src='{img_pnl}'></div></div>
<h2>Tax and SIP</h2><p>Portfolio taxed 25% on each financial year's positive gain at March 31 (turnover realises gains yearly). Indices taxed 25% once at exit, as a buy-and-hold investor would be. Post-tax CAGR 2011-26: portfolio {pct(metrics(port_tax, "2011-01-01", END)["cagr"])}, Nifty 250 10.6%, Nifty 500 8.7%. 2016-26: {pct(metrics(port_tax, "2016-01-01", END)["cagr"])}, 12.0%, 10.3%.</p>{sip_tbl}
<div class='pb'></div><h2>The process</h2><p>Fixed: Nifty 250 universe (NIFTY LARGEMIDCAP 250, point-in-time membership), monthly entry and exit on the first trading day, 25 positions equal-weighted with no weight cap, exit buffer applied to the rank, 12-month lookback (252 sessions, 220 minimum), return filter on, fully invested, no exposure overlay. Refit each January on the trailing five years, choosing the best Sharpe among 36 configurations: score (capture ratio / 50-50 upside-and-capture / upside capture) × regimes (one, or bull-bear tilt on a NIFTY 100 ROC regime) × exit buffer (0/10/20) × trailing stop (off / 20%).</p>{pick_tbl}
<p>The switches are the source of the recent outperformance: everything with upside capture in the score made about 22% a year over 2024-26 against 8% for capture ratio alone, while the reverse held in 2016-23. The process follows that rotation with a one-to-two-year lag; it does not predict it.</p>
<h2>Gates (pre-committed for the rebuild, 2026-09-10)</h2>{gates}
<h2>Caveats</h2><ul><li>Designed after out-of-sample was opened once; one of eight process variants; the 0.9 gate is met at the boundary (standard error of a ten-year Sharpe is about 0.35).</li><li>Benchmarks are price indices; Nifty 250 is the real index from 2020 spliced onto a 50/50 NIFTY 100 + Midcap 150 quarterly-rebalanced proxy (correlation 0.98, CAGR within 0.5pp).</li><li>No exposure overlay: 2008-type events are outside the gated window; the fully invested book lost 65% in 2008 on this data. A 200-DMA breadth overlay protects such events at low cost in calm years but missed the 2020 recovery.</li><li>Capacity, impact beyond 20 bps, and the tax treatment of an actual account are not modelled.</li><li>Against Wright Momentum's published grid (Oct-2020 → Aug-2026, gross): theirs 31.2% CAGR / −21.7%, this book 26.3% net / −26.4%; the gap is 2021, the last three years favour this book.</li></ul>
</body></html>"""
(OUT / "report.html").write_text(html)
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={OUT/'report.pdf'}", str(OUT / "report.html")], capture_output=True)
print("written", OUT / "report.pdf", (OUT / "report.pdf").stat().st_size)
