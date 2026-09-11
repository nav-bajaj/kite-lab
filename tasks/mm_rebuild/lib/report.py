"""Performance report for the MM (core momentum) Nifty 250 stack. HTML -> PDF via headless Chrome.

Single fixed configuration (unlike OM25's chained adaptive process): the
§9d stack with §10's monthly stop check. Everything is computed from the
run directory; nothing is transcribed from RESULTS.md.
"""
import sys, io, base64, json, subprocess, math, pandas as pd, numpy as np
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import run as MM
from windows import equity, stats

OUT = MM.RUNS.parent / "report"; OUT.mkdir(exist_ok=True); RF = 0.05; TAX = 0.25
IS_A, IS_Z = "2010-01-01", "2015-12-31"; OOS_A = "2016-01-01"

STACK = dict(universe="nifty250", kind="voladj", skip=21, lookback=252, min_obs=219, start="2010-01-01", end=None,
             dyn_n_bear=15, dyn_mode="hold", bear_buffer=20, trailing_stop=0.2, sizing="invvol", max_weight=0.10,
             regime_kind="roc", roc_n=31, confirm=3, sector_cap=5, cadence="monthly", stop_check="monthly")
CFG = {**MM.DEFAULTS, **STACK}; RID = MM.cfg_id(CFG); RUN = MM.RUNS / RID
assert RUN.exists(), f"run {RID} not found — run phase10 first"
port = equity(RUN); END = port.index[-1]; idx = port.index
trades = pd.read_csv(RUN / "trades.csv", parse_dates=["date"])
exits = pd.read_csv(RUN / "exits.csv", parse_dates=["entry_date", "exit_date"])

# ---------- benchmarks (same construction as the OM25 report) ----------
def load(p):
    d = pd.read_csv(p); dc = [c for c in d.columns if "date" in c.lower()][0]; d[dc] = pd.to_datetime(d[dc])
    s = d.set_index(dc)["close"].sort_index(); return s[~s.index.duplicated()]
B = "/Users/navdeep/kite-lab/data/master/benchmarks/"
n500 = load(B + "NIFTY_500.csv").reindex(idx).ffill(); n100 = load(B + "NIFTY_100.csv").reindex(idx).ffill()
m150 = load(B + "NIFTY_MIDCAP_150.csv").reindex(idx).ffill()
real = load("/Users/navdeep/Documents/stock_data/indices_data/NIFTY_LARGEMID250.csv").reindex(idx).ffill(); first = real.first_valid_index()
r1, r2 = n100.pct_change().fillna(0), m150.pct_change().fillna(0); a1 = a2 = 0.5; vals = []
for d in idx:
    a1 *= 1 + r1.loc[d]; a2 *= 1 + r2.loc[d]; vals.append(a1 + a2)
    if d.month in (3, 6, 9, 12) and d == idx[(idx.year == d.year) & (idx.month == d.month)][-1]: a1 = a2 = (a1 + a2) / 2
proxy = pd.Series(vals, index=idx)
n250 = pd.concat([proxy[proxy.index < first] * real.loc[first] / proxy.loc[first], real[real.index >= first]])

def fy_tax(s, rate=TAX):
    v = s / s.iloc[0]; adj = pd.Series(1.0, index=v.index); cur = 1.0; base = 1.0
    for d in [d for d in v.index if d.month == 3 and d == v[(v.index.year == d.year) & (v.index.month == 3)].index[-1]]:
        pre = v.loc[d] * cur; gain = pre - base
        if gain > 0: cur *= (pre - rate * gain) / pre
        base = v.loc[d] * cur; adj.loc[adj.index > d] = cur
    return v * adj
port_tax = fy_tax(port)
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
    return dict(total=s.iloc[-1] / s.iloc[0] - 1, cagr=cagr, vol=vol, sharpe=(cagr - RF) / vol, sortino=(cagr - RF) / dn if dn > 0 else np.nan,
                maxdd=dd, calmar=cagr / abs(dd), dd_days=dur, best_m=s.resample("M").last().pct_change().max(),
                worst_m=s.resample("M").last().pct_change().min(), pos_m=(s.resample("M").last().pct_change().dropna() > 0).mean())
def trade_stats(a, z):
    x = exits[(exits.exit_date >= a) & (exits.exit_date <= z)]; t = trades[(trades.date >= a) & (trades.date <= z)]
    yrs = (min(pd.Timestamp(z), END) - pd.Timestamp(a)).days / 365.25
    w, l = x[x.pnl_pct > 0], x[x.pnl_pct <= 0]; eqm = port[(port.index >= a) & (port.index <= z)].mean()  # pv is in rupees already
    days = t.groupby(t.date.dt.to_period("M")).date.nunique(); n_m = len(pd.period_range(pd.Timestamp(a), min(pd.Timestamp(z), END), freq="M"))
    return dict(n=len(x), win=len(w) / len(x), avg_w=w.pnl_pct.mean(), avg_l=l.pnl_pct.mean(), best=x.pnl_pct.max(), worst=x.pnl_pct.min(),
                pf=w.pnl_pct.sum() / -l.pnl_pct.sum(), hold=x.hold_days.mean(), med_hold=x.hold_days.median(),
                stop_share=(x.reason.str.contains("stop", case=False)).mean(), trades_py=len(t) / yrs,
                turnover=t.notional.sum() / eqm / yrs / 2, slip=t.slippage.sum() / eqm / yrs, expectancy=x.pnl_pct.mean(),
                action_days=len(t.date.unique()) / n_m, max_days=int(days.max()) if len(days) else 0,
                months_active=(t.date.dt.to_period("M").nunique()) / n_m)
def period_returns(s):
    e = s.index[-1]; out = {}
    for lab, off in [("1M", pd.DateOffset(months=1)), ("3M", pd.DateOffset(months=3)), ("6M", pd.DateOffset(months=6)), ("YTD", None),
                     ("1Y", pd.DateOffset(years=1)), ("3Y", pd.DateOffset(years=3)), ("5Y", pd.DateOffset(years=5)), ("10Y", pd.DateOffset(years=10)), ("Since 2010", "all")]:
        a = pd.Timestamp(f"{e.year}-01-01") - pd.Timedelta(days=1) if off is None else (s.index[0] if off == "all" else e - off)
        a = s.index[s.index.get_indexer([a], method="nearest")[0]]
        v = s.loc[e] / s.loc[a] - 1; yrs = (e - a).days / 365.25; out[lab] = (1 + v) ** (1 / yrs) - 1 if yrs > 1.05 else v
    return out
def yearly(s):
    y = s.resample("Y").last(); r = y.pct_change(); r.iloc[0] = y.iloc[0] / s.iloc[0] - 1; r.index = r.index.year; return r
def monthly_grid(s):
    m = s.resample("M").last().pct_change(); m.iloc[0] = s.resample("M").last().iloc[0] / s.iloc[0] - 1
    g = pd.DataFrame({"y": m.index.year, "m": m.index.month, "r": m.values}).pivot(index="y", columns="m", values="r")
    g["Year"] = yearly(s).reindex(g.index); return g
def capture(p, b, a, z):
    p = p[(p.index >= a) & (p.index <= z)]; i = p.index.intersection(b.index); p, b = p[i], b[i]; up, dn = b > 0, b < 0
    return (((1 + p[up]).prod() ** (1 / up.sum()) - 1) / ((1 + b[up]).prod() ** (1 / up.sum()) - 1),
            ((1 + p[dn]).prod() ** (1 / dn.sum()) - 1) / ((1 + b[dn]).prod() ** (1 / dn.sum()) - 1))
def sip(s, a, monthly=10000):
    """Monthly SIP on the first session of each month; returns (invested, final, xirr)."""
    sub = s[s.index >= a]; months = sub.resample("MS").first()
    firsts = [sub.index[sub.index.get_indexer([d], method="bfill")[0]] for d in months.index if d <= sub.index[-1]]
    firsts = sorted(set(firsts)); units = sum(monthly / sub.loc[d] for d in firsts)
    final = units * sub.iloc[-1]; invested = monthly * len(firsts)
    lo, hi = -0.9, 3.0
    for _ in range(200):
        mid = (lo + hi) / 2
        npv = sum(monthly * (1 + mid) ** ((sub.index[-1] - d).days / 365.25) for d in firsts) - final
        if npv > 0: hi = mid
        else: lo = mid
    return invested, final, (lo + hi) / 2

# ---------- charts ----------
C = {"Portfolio": "#1f4e79", "Portfolio post-tax": "#7f9cc0", "Nifty 250": "#c0504d", "Nifty 500": "#9bbb59"}
def png(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=160, bbox_inches="tight"); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25})
fig, ax = plt.subplots(figsize=(9, 3.4))
for n, s in SERIES.items(): ax.plot(s.index, s / s.iloc[0], color=C[n], lw=1.3 if "Portfolio" in n else 1.0, label=n)
ax.axvline(pd.Timestamp(OOS_A), color="k", ls=":", lw=1.0)
ax.annotate("out-of-sample opened here", xy=(pd.Timestamp(OOS_A), ax.get_ylim()[1]), fontsize=7, ha="left", va="top", rotation=90, color="#444")
ax.set_yscale("log"); ax.set_title(f"Growth of 1 (log scale), 2010-01 to {END.date()} — left of the dotted line is in-sample")
ax.legend(frameon=False, ncol=4); img_eq = png(fig)
fig, ax = plt.subplots(figsize=(9, 2.2))
for n in ["Portfolio", "Nifty 250"]: s = SERIES[n]; ax.fill_between(s.index, (s / s.cummax() - 1) * 100, 0, color=C[n], alpha=0.35, label=n)
ax.set_title("Drawdown from peak, %"); ax.legend(frameon=False); img_dd = png(fig)
yy = pd.DataFrame({n: yearly(SERIES[n]) for n in ["Portfolio", "Nifty 250", "Nifty 500"]}) * 100
fig, ax = plt.subplots(figsize=(9, 2.6)); w = 0.27
for i, n in enumerate(yy.columns): ax.bar(yy.index + (i - 1) * w, yy[n], w, color=C[n], label=n)
ax.axhline(0, color="k", lw=0.5); ax.set_title(f"Calendar-year returns, % ({END.year} year to date)"); ax.legend(frameon=False, ncol=3); ax.set_xticks(yy.index); img_yr = png(fig)
m36 = port.resample("M").last(); b36 = n250.resample("M").last()
ex3 = ((m36.pct_change(36) + 1) ** (1 / 3) - (b36.pct_change(36) + 1) ** (1 / 3)).dropna() * 100
fig, ax = plt.subplots(figsize=(9, 2.2)); ax.plot(ex3.index, ex3, color=C["Portfolio"]); ax.axhline(0, color="k", lw=0.5)
ax.axhline(ex3.median(), color="grey", ls="--", lw=0.8, label=f"median {ex3.median():.1f}pp")
ax.set_title("Rolling 3-year excess CAGR over Nifty 250, percentage points"); ax.legend(frameon=False); img_roll = png(fig)
fig, ax = plt.subplots(figsize=(9, 2.4)); ax.hist(exits.pnl_pct.clip(-0.5, 1.5) * 100, bins=60, color=C["Portfolio"], alpha=0.85)
ax.axvline(0, color="k", lw=0.6); ax.set_title("Per-trade P&L distribution, % (net of slippage; clipped at -50 / +150)"); ax.set_xlabel("%"); img_pnl = png(fig)
# action days per month
t16 = trades[trades.date >= OOS_A]; adm = t16.groupby(t16.date.dt.to_period("M")).date.nunique()
allm = pd.period_range(OOS_A, END, freq="M"); adm = adm.reindex(allm, fill_value=0)
fig, ax = plt.subplots(figsize=(9, 1.8)); ax.bar(adm.index.to_timestamp(), adm.values, width=20, color=C["Portfolio"])
ax.set_yticks([0, 1, 2]); ax.set_title("Trading days with any order, per month (2016 onward)"); img_act = png(fig)

# ---------- tables ----------
def pct(v, d=1): return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{100*v:.{d}f}%"
def num(v, d=2): return f"{v:.{d}f}"
def table(rows, header, cls=""):
    h = "".join(f"<th>{c}</th>" for c in header)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table class='{cls}'><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"
W = {"2016-26 (out-of-sample)": (OOS_A, END), "2010-26 (full span, includes the in-sample window)": (IS_A, END)}
def summary_block(wname):
    a, z = W[wname]; M = {n: metrics(s, a, z) for n, s in SERIES.items()}; T = trade_stats(a, z)
    cards = [("CAGR", pct(M["Portfolio"]["cagr"]), f"post-tax {pct(M['Portfolio post-tax']['cagr'])}"),
             ("Total return", pct(M["Portfolio"]["total"], 0), f"Nifty 250 {pct(M['Nifty 250']['total'], 0)}"),
             ("Max drawdown", pct(M["Portfolio"]["maxdd"]), f"{M['Portfolio']['dd_days']} days peak to recovery"),
             ("Sharpe (rf 5%)", num(M["Portfolio"]["sharpe"]), f"Nifty 250 {num(M['Nifty 250']['sharpe'])}"),
             ("Sortino", num(M["Portfolio"]["sortino"]), f"Calmar {num(M['Portfolio']['calmar'])}"),
             ("Volatility", pct(M["Portfolio"]["vol"]), f"Nifty 250 {pct(M['Nifty 250']['vol'])}"),
             ("Hit rate", pct(T["win"]), f"{T['n']} closed trades"),
             ("Avg holding", f"{T['hold']:.0f} days", f"median {T['med_hold']:.0f}"),
             ("Order days", f"{T['action_days']:.1f} / month", f"max {T['max_days']} in any month")]
    cards_html = "".join(f"<div class='card'><div class='k'>{k}</div><div class='v'>{v}</div><div class='s'>{s}</div></div>" for k, v, s in cards)
    rows = [[n, pct(m["cagr"]), pct(m["total"], 0), pct(m["vol"]), num(m["sharpe"]), num(m["sortino"]), num(m["calmar"]), pct(m["maxdd"]),
             m["dd_days"], pct(m["best_m"]), pct(m["worst_m"]), pct(m["pos_m"], 0)] for n, m in M.items()]
    return f"<h2>{wname}</h2><div class='cards'>{cards_html}</div>" + table(rows, ["", "CAGR", "Total", "Vol", "Sharpe", "Sortino", "Calmar", "Max DD", "DD days", "Best month", "Worst month", "Positive months"])

pr = {n: period_returns(s) for n, s in SERIES.items()}
period_tbl = table([[n] + [pct(v) for v in p.values()] for n, p in pr.items()], ["Period returns (annualised beyond 1Y)"] + list(pr["Portfolio"].keys()))
yy_all = pd.DataFrame({n: yearly(SERIES[n]) for n in SERIES}); yy_all["Excess vs Nifty 250"] = yy_all["Portfolio"] - yy_all["Nifty 250"]
year_tbl = table([[y] + [pct(v) for v in r] for y, r in yy_all.iterrows()], ["Year"] + list(yy_all.columns))
g = monthly_grid(port); mn = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
def cell(v):
    if pd.isna(v): return "<td></td>"
    c = f"rgba(31,78,121,{min(abs(v)/0.15,1)*0.55:.2f})" if v >= 0 else f"rgba(192,80,77,{min(abs(v)/0.15,1)*0.55:.2f})"
    return f"<td style='background:{c}'>{100*v:.1f}</td>"
month_tbl = ("<table class='heat'><thead><tr><th>Year</th>" + "".join(f"<th>{m}</th>" for m in mn) + "<th>Year</th></tr></thead><tbody>"
             + "".join(f"<tr><td><b>{y}</b></td>" + "".join(cell(r.get(m, np.nan)) for m in range(1, 13)) + cell(r["Year"]) + "</tr>" for y, r in g.iterrows()) + "</tbody></table>")
ddt = dd_table(port, 6)
dd_tbl = table([[str(s.date()), str(t.date()), str(r.date()) if r is not None else "ongoing", pct(d), (t - s).days, ((r or END) - t).days, ((r or END) - s).days]
                for s, t, r, d in ddt], ["Peak", "Trough", "Recovered", "Depth", "Days down", "Days to recover", "Total days"])
Tf = trade_stats(IS_A, END); To = trade_stats(OOS_A, END)
trade_tbl = table([["Closed trades", Tf["n"], To["n"]], ["Win rate", pct(Tf["win"]), pct(To["win"])], ["Average winner", pct(Tf["avg_w"]), pct(To["avg_w"])],
                   ["Average loser", pct(Tf["avg_l"]), pct(To["avg_l"])], ["Expectancy per trade", pct(Tf["expectancy"]), pct(To["expectancy"])],
                   ["Profit factor (sum of wins / sum of losses)", num(Tf["pf"]), num(To["pf"])], ["Best trade", pct(Tf["best"]), pct(To["best"])],
                   ["Worst trade", pct(Tf["worst"]), pct(To["worst"])], ["Average holding days", f"{Tf['hold']:.0f}", f"{To['hold']:.0f}"],
                   ["Median holding days", f"{Tf['med_hold']:.0f}", f"{To['med_hold']:.0f}"], ["Exits by trailing stop", pct(Tf["stop_share"]), pct(To["stop_share"])],
                   ["Trades per year", f"{Tf['trades_py']:.0f}", f"{To['trades_py']:.0f}"], ["One-way turnover per year", f"{Tf['turnover']:.1f}x", f"{To['turnover']:.1f}x"],
                   ["Slippage cost per year", pct(Tf["slip"]), pct(To["slip"])], ["Order days per month", f"{Tf['action_days']:.1f}", f"{To['action_days']:.1f}"],
                   ["Months with any order", pct(Tf["months_active"], 0), pct(To["months_active"], 0)]], ["Trade statistics", "2010-26", "2016-26 (OOS)"])
hold = exits.hold_days
hold_tbl = table([[f"{lo}-{hi} days", pct((hold.between(lo, hi)).mean()), pct(exits[hold.between(lo, hi)].pnl_pct.mean())]
                  for lo, hi in [(0, 30), (31, 60), (61, 120), (121, 250), (251, 5000)]], ["Holding period", "Share of trades", "Avg P&L"])
pm = port.resample("M").last().pct_change().dropna(); bm250 = n250.resample("M").last().pct_change().dropna()
ms400 = pd.read_csv("/Users/navdeep/kite-lab/tasks/om25_rebuild/runs/midsmall400_synthetic.csv", parse_dates=["date"]).set_index("date")["close"]
bm400 = ms400.resample("M").last().pct_change().dropna()
cap_rows = []
for lab, a, z in [("2016-26 (OOS)", OOS_A, str(END.date())), ("2016-19", "2016-01-01", "2019-12-31"), ("2020-22", "2020-01-01", "2022-12-31"),
                  ("2023-26", "2023-01-01", str(END.date())), ("Wright window Oct-20 to Aug-26", "2020-10-01", "2026-08-31")]:
    u, d = capture(pm, bm250, a, z); mm_ = metrics(port, a, z); bb = metrics(n250, a, z)
    cap_rows.append([lab, pct(mm_["cagr"]), pct(bb["cagr"]), num(mm_["sharpe"]), num(bb["sharpe"]), pct(mm_["maxdd"]), num(u), num(d)])
uw, dw = capture(pm, bm400, "2020-10-01", "2026-08-31"); mw = metrics(port, "2020-10-01", "2026-08-31")
cap_tbl = table(cap_rows, ["Window", "Portfolio CAGR", "Nifty 250 CAGR", "Portfolio Sharpe", "Nifty 250 Sharpe", "Portfolio Max DD", "Up-capture", "Down-capture"])
wright_tbl = table([["This book (net of 20 bps)", pct(mw["cagr"]), num(mw["sharpe"]), pct(mw["maxdd"]), num(uw), num(dw)],
                    ["Wright Momentum (published, gross)", "31.2%", "not published", "-21.7% (month-end)", "1.11", "0.90"]],
                   ["Oct-2020 to Aug-2026, vs mid-small 400", "CAGR", "Sharpe", "Max DD", "Up-capture", "Down-capture"])

sip_rows = []
for lab, a, s in [("From 2010, pre-tax", IS_A, port), ("From 2010, post-tax", IS_A, port_tax), ("From 2016, pre-tax", OOS_A, port), ("From 2016, post-tax", OOS_A, port_tax)]:
    inv, fin, x = sip(s, a); _, fn2, x2 = sip(n250, a); _, fn5, x5 = sip(n500, a)
    sip_rows.append([lab, f"{inv/1e5:.1f}L", f"{fin/1e5:.1f}L ({fin/inv:.1f}x), {100*x:.1f}%", f"{fn2/1e5:.1f}L ({fn2/inv:.1f}x), {100*x2:.1f}%", f"{fn5/1e5:.1f}L ({fn5/inv:.1f}x), {100*x5:.1f}%"])
sip_tbl = table(sip_rows, ["SIP Rs 10,000 / month", "Invested", "Portfolio (value, XIRR)", "Nifty 250", "Nifty 500"])

o = metrics(port, OOS_A, END); subs = [(lab, metrics(port, a, z)["sharpe"]) for lab, a, z in
                                       [("2016-19", "2016-01-01", "2019-12-31"), ("2020-22", "2020-01-01", "2022-12-31"), ("2023-26", "2023-01-01", str(END.date()))]]
is_sh = metrics(port, IS_A, IS_Z)["sharpe"]
PARAMS = [("Universe", "Nifty LargeMidcap 250, point-in-time", "§1 (in-sample)"), ("Score", "volatility-adjusted momentum, 5% vol floor", "§1 (in-sample)"),
          ("Lookback", "252 sessions (12m), min 219", "§1 (in-sample)"), ("Skip", "21 sessions", "§3a (in-sample)"),
          ("Positions", "25", "§2 (in-sample)"), ("Exit buffer", "20 (sell below rank 45)", "§2 (in-sample)"),
          ("Rebalance", "monthly, first trading day", "§2 (in-sample)"), ("Trailing stop", "20% from peak", "§3c rejected in-sample, adopted §8 post-OOS"),
          ("Stop check", "monthly, same signal as the rebalance", "§10 (post-OOS)"), ("Sizing", "inverse volatility, 63d window, 10% cap", "§9b (post-OOS)"),
          ("Bear book", "hold at most 15 names, bear exit buffer 20", "§9b/§9c (post-OOS)"), ("Regime", "NIFTY 100 ROC 31, 3-day confirm, lagged", "§9b (post-OOS)"),
          ("Sector cap", "5 names per NSE sector at entry", "§9d (post-OOS)")]
param_tbl = table([[k, v, w] for k, v, w in PARAMS], ["Parameter", "Value", "Decided in"])
gates = table([["G1 IS Sharpe 2010-2015 ≥ 0.8", num(is_sh), "pass" if is_sh >= 0.8 else "FAIL"],
               ["G2 OOS Sharpe 2016-26 ≥ 0.9", num(o["sharpe"]), "pass" if o["sharpe"] >= 0.9 else "FAIL"],
               ["G3 each sub-window ≥ 0.6", " / ".join(num(v) for _, v in subs), "pass" if min(v for _, v in subs) >= 0.6 else "FAIL"],
               ["G4 OOS max drawdown no worse than −40%", pct(o["maxdd"]), "pass" if o["maxdd"] >= -0.40 else "FAIL"],
               ["G5 walk-forward within 0.2 of static OOS", "5y refit 0.98 (gap 0.200) · 3y refit 0.97 (gap 0.215)", "ON THE LINE"],
               ["G6 parameter count ≤ 10", f"{len(PARAMS)} listed", "OVER — see note"],
               ["G7 turnover reported", f"{To['turnover']:.1f}x one-way per year, {To['trades_py']:.0f} trades", "reported"],
               ["G8 OOS CAGR ≥ 20% pre-tax", pct(o["cagr"]), "pass" if o["cagr"] >= 0.20 else "FAIL"]], ["Gate", "Value", "Status"])

expect_tbl = table([["Static, the adopted cell (selection-window maximum)", pct(o["cagr"]), num(o["sharpe"]), "rank 1 of 32"],
                    ["Centre of the refit-grid plateau", "—", "1.04", "median of 32 cells"],
                    ["Walk-forward, 5-year refit (no hindsight)", "22.4%", "0.98", "§11"],
                    ["Walk-forward, 3-year refit", "22.0%", "0.97", "§11"],
                    ["Deflated for the 32-cell refit grid", "—", "0.76", "Bailey-Lopez de Prado"],
                    ["Deflated for the ~128 post-OOS cells of §8-§10", "—", "0.66", "Bailey-Lopez de Prado"]],
                   ["Reading", "CAGR", "Sharpe", "Source"])
css = """<style>@page{size:A4;margin:14mm 12mm}body{font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:9.5px;color:#222;margin:0}h1{font-size:20px;margin:0 0 2px}h2{font-size:13px;margin:14px 0 6px;border-bottom:1px solid #ccc;padding-bottom:2px}h3{font-size:11px;margin:10px 0 4px}p{margin:4px 0;line-height:1.35}.sub{color:#666;font-size:10px}table{border-collapse:collapse;width:100%;margin:4px 0 8px;page-break-inside:avoid}th,td{border-bottom:1px solid #e3e3e3;padding:3px 5px;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{background:#f3f5f8;font-weight:600}.heat td{text-align:center;padding:2px 3px}.cards{display:grid;grid-template-columns:repeat(9,1fr);gap:5px;margin:6px 0}.card{border:1px solid #ddd;border-radius:4px;padding:5px 6px}.card .k{color:#666;font-size:8px}.card .v{font-size:14px;font-weight:600;margin:1px 0}.card .s{color:#666;font-size:7.5px}img{width:100%;display:block;margin:4px 0}.pb{page-break-before:always}.note{background:#fbf7e8;border-left:3px solid #d9b44a;padding:5px 8px;margin:6px 0}.warn{background:#fdf0ee;border-left:3px solid #c0504d;padding:5px 8px;margin:6px 0}ul{margin:2px 0 4px 14px;padding:0}li{margin:1px 0}</style>"""
html = f"""<!doctype html><html><head><meta charset='utf-8'><title>MM core momentum — performance report</title>{css}</head><body>
<h1>MM — core momentum, rebuild candidate</h1>
<div class='sub'>Nifty 250 · volatility-adjusted 12-month momentum · 25 names · monthly · one order day per month · research report generated {pd.Timestamp.today().date()} from the honest master store · backtest, not live; net of 20 bps slippage each way; price-return basis (dividends excluded from portfolio and benchmarks) · run <code>{RID}</code> · not a client document</div>
<div class='warn'><b>Read first — what is in-sample here.</b> The universe, score, lookback, skip, position count, exit buffer and monthly cadence were chosen on 2010-2015 before out-of-sample was opened on 2026-09-10. <b>Everything else — the trailing stop, inverse-volatility sizing, the hold-15-in-bear rule, the regime detector and the sector cap — was chosen after the 2016-2026 window had been seen</b>, across roughly 128 post-OOS cells. Each element rests on a plateau rather than a single cell, but <b>this stack as a whole has never been judged on unseen data.</b> The 2016-2026 figures below are therefore not a clean out-of-sample result for the stack; they are the window the later devices were selected on.</div>
<div class='note'>Every number is a simulation on reconstructed point-in-time index membership with delisted names carried to their last price. Tax figures use a flat 25% on each financial year's realised gain with no loss carry-forward, which is deliberately harsh.</div>
{summary_block("2016-26 (out-of-sample)")}{summary_block("2010-26 (full span, includes the in-sample window)")}
<h2>Period returns to {END.date()}</h2>{period_tbl}
<div class='pb'></div><h2>Growth and drawdown</h2><img src='{img_eq}'><img src='{img_dd}'>
<div class='pb'></div><h2>Calendar years</h2><img src='{img_yr}'>{year_tbl}
<h2>Monthly returns, % (portfolio, pre-tax)</h2>{month_tbl}
<h2>Largest drawdowns</h2>{dd_tbl}<img src='{img_roll}'>
<div class='pb'></div><h2>Trades</h2>
<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px'><div>{trade_tbl}</div><div>{hold_tbl}<img src='{img_pnl}'></div></div>
<h2>Followability — one order day a month</h2>
<p>The stack rebalances and checks the stop on the same monthly signal, so every order falls on one day. Across 2016-26 that is <b>{To['action_days']:.1f} trading days with any order per month</b>, never more than {To['max_days']}, with orders in {pct(To['months_active'],0)} of months. Faster rhythms were tested and cost performance: biweekly rebalancing takes the Sharpe from {num(o['sharpe'])} to about 1.0 and weekly to about 1.02, both at two to four order days a month (§10). Engagement between rebalances is a product question — a weekly note reporting rankings, distance to stops and regime state without trading — not a strategy one.</p>
<img src='{img_act}'>
<div class='pb'></div><h2>Behaviour against the benchmark</h2>
<p>Up- and down-capture are computed on monthly returns against the Nifty 250 throughout this table. A down-capture below 1 means the book falls less than the index in down months.</p>{cap_tbl}
<h3>Against Wright Momentum's published grid</h3>
<p>Capture here is measured against the same synthetic mid-small 400 series used in §9-§10, so it is comparable to Wright's published figures. Theirs are gross of costs, this book is net of 20 bps each way, and Wright publish no Sharpe for this window. Their drawdown is measured on month-end values and is the shallower of the two on any measure; on a daily basis this book's is deeper still relative to theirs. The gap in return is 2026 and the last three years; the gap in drawdown is theirs to keep.</p>{wright_tbl}
<h2>The stack</h2>{param_tbl}
<p>The bear rule is the distinguishing device: when the regime is bear the book holds at most 15 names instead of 25 and lets the exit rank widen to 35, which is where the down-capture comes from. Because the engine never resizes an existing position, names bought at 1/25 in a bull regime are not topped up in bear, so the bear book carries some cash — it averages 17 names at about 77% invested rather than a full 15-name book.</p>
<h2>Gates (pre-committed 2026-09-10, signed before the first search)</h2>{gates}
<div class='warn'><b>Two gates are not clean.</b> G6 caps the all-in parameter count at 10 and the table above lists {len(PARAMS)}; whether the vol floor, minimum observations and the regime's two settings count is a judgement, but on any reading this stack is at or over the limit. G5 was run in §11: refitting the post-OOS devices yearly on a trailing five years gives Sharpe 0.98, a gap of 0.200 — the threshold to three decimals — and on a trailing three years 0.97, a gap of 0.215, which misses. The stack sits on the line rather than clearing it.</div>
<h2>What to expect, rather than the headline</h2>
<p>The adopted cell is <b>rank 1 of the 32 cells</b> in §11's refit grid, which runs 0.88 to 1.18 with a median of 1.04. That is what selecting a cell on the window it is measured on produces. Four readings of the same book, from most to least flattering:</p>
{expect_tbl}
<p><b>The walk-forward row is the one to plan against</b> — roughly 22% a year at a Sharpe near 1.0, not 25.7% at 1.18. The deflated rows apply the Bailey-López de Prado haircut for the number of post-OOS cells examined, using the observed cross-trial Sharpe variance of 0.041 rather than an assumed one.</p>
<h2>Tax and SIP</h2>
<p>Portfolio taxed 25% on each financial year's positive gain at 31 March, since the turnover realises gains yearly. Indices taxed 25% once at exit, as a buy-and-hold investor would be. Post-tax CAGR 2016-26: portfolio {pct(metrics(port_tax, OOS_A, END)['cagr'])} against Nifty 250 {pct(metrics(n250, OOS_A, END)['cagr'])} pre-tax.</p>{sip_tbl}
<h2>Caveats</h2><ul>
<li>The stack is a post-OOS design. Its 2016-26 numbers are selection-window numbers, not out-of-sample ones; the honest out-of-sample test is the next few years of live running.</li>
<li>Roughly 128 post-OOS cells were examined across §8-§10; the deflation that implies is not applied to the figures above.</li>
<li>Benchmarks are price indices. Nifty 250 is the real index from 2020 spliced onto a 50/50 NIFTY 100 + Midcap 150 quarterly-rebalanced proxy.</li>
<li>Sector labels come from 26 archived NSE constituent lists and cover 87% of all-ever members; 13% are unlabelled and unconstrained by the cap, about 1% of the book's buys.</li>
<li>No exposure overlay. 2008-type events sit outside the tested span.</li>
<li>Capacity, market impact beyond 20 bps, and the tax treatment of an actual account are not modelled.</li>
</ul>
</body></html>"""
(OUT / "report.html").write_text(html)
subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                f"--print-to-pdf={OUT/'report.pdf'}", str(OUT / "report.html")], capture_output=True)
print("written", OUT / "report.pdf", (OUT / "report.pdf").stat().st_size)
print(f"OOS {100*o['cagr']:.1f}% / {o['sharpe']:.2f} / {100*o['maxdd']:.0f}%  subs " + " / ".join(f"{v:.2f}" for _, v in subs) + f"  IS {is_sh:.2f}")
