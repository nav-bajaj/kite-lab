"""§3j main grid — momentum-strength overlay. Each cell is run fresh on two windows:
cost 2010-01-01 -> 2015-12-31 and protection 2006-02-01 -> 2009-12-31, `end` passed so
nothing later is simulated. Both runs are registered (phase 3j); the protection run has
no 2010-2015 path so its registry stats are blank. Settings chosen from runs/3j_diag.csv."""
import sys, csv, itertools, os
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/om25_rebuild/lib")
import pandas as pd
from run import run_candidate, cfg_id, RUNS, strength_series
from windows import equity, stats, register, fmt
WIN = {"cost": ("2010-01-01", "2015-12-31"), "pre": ("2006-02-01", "2009-12-31")}
SUMMARY = RUNS / "3j_summary.csv"
COLS = ["stage", "universe", "cadence", "kind", "len", "mode", "thresh", "confirm", "bear_exposure", "reenter",
        "cost_cagr", "cost_sharpe", "cost_maxdd", "pre_cagr", "pre_sharpe", "pre_maxdd", "weak_cost", "weak_pre", "id_cost", "id_pre"]
BOOK = dict(score="cr", regimes=1, top_n=25, exit_buffer=20, return_filter=True)
SETTINGS = [
    ("breadth", 126, "abs", 0.3), ("breadth", 63, "abs", 0.3), ("breadth", 252, "abs", 0.4), ("breadth", 126, "pct", 0.1), ("breadth", 63, "pct", 0.2),
    ("breadth_ma", 200, "abs", 0.3), ("breadth_ma", 100, "abs", 0.3), ("breadth_ma", 200, "pct", 0.1), ("breadth_ma", 100, "pct", 0.2), ("breadth_ma", 200, "abs", 0.4),
    ("disp", 252, "pct", 0.1), ("disp", 252, "pct", 0.2), ("disp", 126, "pct", 0.1), ("disp", 252, "abs", 0.40), ("disp", 252, "abs", 0.35),
    ("factor", 63, "abs", 0.0), ("factor", 63, "abs", -0.05), ("factor", 42, "abs", -0.05), ("factor", 63, "pct", 0.2),
    ("leaders", 63, "abs", -0.02), ("leaders", 42, "abs", -0.02), ("leaders", 63, "pct", 0.2), ("leaders", 63, "abs", 0.0),
    ("persist", 63, "pct", 0.2), ("persist", 63, "pct", 0.3), ("persist", 63, "abs", 0.70), ("persist", 63, "abs", 0.65),
    ("capture", 126, "pct", 0.3), ("capture", 126, "pct", 0.2), ("capture", 252, "pct", 0.1), ("capture", 126, "abs", 1.6), ("capture", 252, "abs", 1.4),
    ("breadth_d", 63, "abs", -0.1), ("breadth_d", 63, "pct", 0.1), ("breadth_d", 21, "pct", 0.1),
]
UNIS = [("nifty250", "monthly"), ("nse500", "biweekly")]


def cell(stage, uni, cad, kind=None, L=None, mode=None, th=None, confirm=3, be=1.0, reenter=False):
    row = dict(stage=stage, universe=uni, cadence=cad, kind=kind or "none", len=L, mode=mode, thresh=th, confirm=confirm, bear_exposure=be, reenter=reenter)
    for w, (a, b) in WIN.items():
        kw = dict(BOOK, universe=uni, cadence=cad, start=a, end=b)
        if kind:
            kw.update(overlay=True, regime_kind="strength", str_kind=kind, str_len=L, str_mode=mode, str_thresh=th, confirm=confirm, bear_exposure=be, reenter_on_flip=reenter)
        cfg, _ = run_candidate(**kw)
        eq = equity(RUNS / cfg_id(cfg))
        st = stats(eq, a, b); register(cfg, cfg_id(cfg), stats(eq, *WIN["cost"]), "3j")
        row.update({f"{w}_cagr": round(100 * st["cagr"], 2), f"{w}_sharpe": round(st["sharpe"], 3), f"{w}_maxdd": round(100 * st["maxdd"], 2), f"id_{w}": cfg_id(cfg)})
        if kind:
            r = strength_series(uni, kind, L, th, mode, confirm, pd.Timestamp(b)); row[f"weak_{w}"] = round(float((~r[a:b]).mean()), 3)
        else:
            row[f"weak_{w}"] = 0.0
    new = not SUMMARY.exists()
    with open(SUMMARY, "a", newline="") as f:
        w_ = csv.DictWriter(f, fieldnames=COLS); (w_.writeheader() if new else None); w_.writerow(row)
    print(f"{stage} {uni} {cad} {row['kind']} L={L} {mode} {th} c={confirm} be={be} re={reenter} | cost {row['cost_cagr']:.1f}/{row['cost_sharpe']:.2f}/{row['cost_maxdd']:.1f} weak {row['weak_cost']:.2f} | pre {row['pre_cagr']:.1f}/{row['pre_sharpe']:.2f}/{row['pre_maxdd']:.1f} weak {row['weak_pre']:.2f}", flush=True)
    return row


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "grid"
    if stage == "grid":
        for uni, cad in UNIS:
            cell("base", uni, cad)
        for (kind, L, mode, th), be, (uni, cad) in itertools.product(SETTINGS, [0.5, 0.0], UNIS):
            cell("grid", uni, cad, kind, L, mode, th, 3, be)
    print("done", flush=True)
