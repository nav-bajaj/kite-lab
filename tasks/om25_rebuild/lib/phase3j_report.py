"""§3j summary: best cell per indicator and universe against the fully invested book and the acceptance bands."""
import sys
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
import pandas as pd
from run import RUNS
pd.set_option("display.width", 250, "display.max_rows", 500, "display.max_columns", 30)
d = pd.read_csv(RUNS / "3j_summary.csv").drop_duplicates(subset=["id_cost", "id_pre"], keep="last")
base = d[d.kind == "none"].set_index("universe")
d = d[d.kind != "none"].copy()
d["d_cagr"] = d.cost_cagr - d.universe.map(base.cost_cagr)
d["d_sharpe"] = d.cost_sharpe - d.universe.map(base.cost_sharpe)
d["cost_ok"] = (d.d_cagr >= -2.0) & (d.d_sharpe >= -0.10)
d["prot_ok"] = d.pre_maxdd >= -40.0
d["accept"] = d.cost_ok & d.prot_ok
print("cells", len(d), " cost_ok", int(d.cost_ok.sum()), " prot_ok", int(d.prot_ok.sum()), " accept", int(d.accept.sum()))
print("\nBASELINES\n", base[["cost_cagr", "cost_sharpe", "cost_maxdd", "pre_cagr", "pre_sharpe", "pre_maxdd"]].to_string())
cols = ["stage", "kind", "len", "mode", "thresh", "confirm", "bear_exposure", "reenter", "cost_cagr", "cost_sharpe", "cost_maxdd", "d_cagr", "d_sharpe", "pre_cagr", "pre_sharpe", "pre_maxdd", "weak_cost", "weak_pre", "cost_ok", "prot_ok"]
for uni in ["nifty250", "nse500"]:
    u = d[d.universe == uni]
    print(f"\n=== {uni}: best pre_maxdd among cost_ok cells, per indicator ===")
    ok = u[u.cost_ok].sort_values("pre_maxdd", ascending=False).groupby("kind").head(1)
    print(ok[cols].to_string(index=False) if len(ok) else "none")
    print(f"\n=== {uni}: best pre_maxdd per indicator, any cost ===")
    print(u.sort_values("pre_maxdd", ascending=False).groupby("kind").head(1)[cols].to_string(index=False))
    print(f"\n=== {uni}: cells with pre_maxdd >= -40 (protection met), sorted by cost ===")
    p = u[u.prot_ok].sort_values("d_sharpe", ascending=False)
    print(p[cols].head(15).to_string(index=False) if len(p) else "none")
    print(f"\n=== {uni}: accepted cells ===")
    print(u[u.accept][cols].to_string(index=False) if u.accept.any() else "none")
if len(sys.argv) > 1 and sys.argv[1] == "all":
    print("\n=== ALL CELLS ===")
    print(d.sort_values(["universe", "kind", "len", "mode", "thresh", "bear_exposure"])[["universe"] + cols].to_string(index=False))
