from __future__ import annotations
import numpy as np, pandas as pd

R = pd.read_parquet("tasks/exit_asymmetry_2026/data/sims.parquet")
R["yr"] = pd.to_datetime(R.entry_date).dt.year
R = R[R.yr >= 2021]

def grab(fam, par, bs, tag):
    x = R[(R.fam == fam) & (R.params == par) & (R.backstop == bs)]
    return x.set_index(["symbol", "entry_date"])[
        ["exit_date", "ret", "hold", "why", "peak_gain", "closed"]].add_suffix("_" + tag)

x0 = grab("X0", "—", False, "x0")
w = grab("X1", "A=25 k=50", False, "win")       # nominal grid winner
b = grab("X1", "A=25 k=50", True, "winbs")      # same parameters, ma150 backstop
c = x0.join(w).join(b).reset_index().sort_values("entry_date")
c["d_ret_win"] = c.ret_win - c.ret_x0
c["d_ret_winbs"] = c.ret_winbs - c.ret_x0
c["kept_x0"] = np.where(c.peak_gain_x0 > 0, c.ret_x0 / c.peak_gain_x0, np.nan)
c["kept_win"] = np.where(c.peak_gain_win > 0, c.ret_win / c.peak_gain_win, np.nan)
c.to_csv("tasks/exit_asymmetry_2026/data/best_vs_x0_2021.csv", index=False)

print("2021+ all calls:", len(c))
for tag in ("x0", "win", "winbs"):
    z = c[c[f"closed_{tag}"]][f"ret_{tag}"]
    print(f"{tag:6s} closed={len(z):4d} open={int((~c[f'closed_{tag}']).sum()):3d} "
          f"win={round((z>0).mean()*100,1)} exp={round(z.mean()*100,2)} "
          f"ALLexp={round(c[f'ret_{tag}'].mean()*100,2)} medhold={int(c[f'hold_{tag}'].median())}")
print("\nsame-call comparison, ALL 2021+ calls marked at exit or at end:")
print("  X0", round(c.ret_x0.mean()*100, 2), " win(nobs)", round(c.ret_win.mean()*100, 2),
      " win+backstop", round(c.ret_winbs.mean()*100, 2))
print("  X1 nobs beats X0 on", round((c.ret_win > c.ret_x0).mean()*100, 1), "% of calls")
print("  X1+bs beats X0 on", round((c.ret_winbs > c.ret_x0).mean()*100, 1), "% of calls")
print("\nopen-position bias on the nominal winner:")
o = c[~c.closed_win]
print("  still open n=", len(o), " their X0 outcome exp=", round(o.ret_x0.mean()*100, 2),
      " their mark exp=", round(o.ret_win.mean()*100, 2))
