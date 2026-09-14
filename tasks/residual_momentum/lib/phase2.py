"""§2 — the five score arms through the identical locked MM machinery.

Config is §22's adopted cell verbatim (voladj / buffer 20 / stop 0.2 / invvol / bear 15 / sector cap 5)
with only `kind` swapped, so MM is a live control: if the MM arm does not reproduce its registry number,
the comparison is void.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent; TASK = HERE.parent; REPO = TASK.parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tasks/mm_rebuild/lib"))
import run as MM                                    # noqa: E402
import windows as W                                 # noqa: E402
from data_pipeline.strategies.sectors import load_sector_map   # noqa: E402
from residual import make_residual_score            # noqa: E402
sys.path.insert(0, str(REPO / "tasks/om25_rebuild/lib"))
from regime import membership_mask                  # noqa: E402

REPORT = TASK / "report"; REPORT.mkdir(exist_ok=True)
RM_KINDS = {"rm12": dict(mode="alpha"), "rm24": dict(mode="resid", est_window=504), "rm36": dict(mode="resid", est_window=756)}

_orig_score = MM.make_momentum_score
_ctx = {}


def _patched(returns_universe, *, kind="abs", lookback=252, min_obs=219, skip=0, candidate_fn=None, **kw):
    """Route rm* kinds to the residual score; everything else to the production momentum score untouched."""
    if kind not in RM_KINDS:
        return _orig_score(returns_universe, kind=kind, lookback=lookback, min_obs=min_obs, skip=skip,
                           candidate_fn=candidate_fn, **kw)
    if "bench" not in _ctx:
        _ctx["bench"] = MM.om.panels()["bench"].pct_change()
        _ctx["smap"] = load_sector_map()
    mask = membership_mask(MM.om.MEMBERSHIP["nifty250"], returns_universe)
    return make_residual_score(returns_universe, _ctx["bench"], _ctx["smap"], lookback=lookback, skip=skip,
                               min_obs=min_obs, member_mask=mask, candidate_fn=candidate_fn, **RM_KINDS[kind])


MM.make_momentum_score = _patched

BASE = dict(universe="nifty250", lookback=252, min_obs=220, top_n=25, cadence="monthly", exit_cadence="same",
            stop_check="monthly", fill_from_buffer=True, start="2006-02-01", end=None,
            regime_kind="roc", roc_n=31, confirm=3)
CELL = dict(exit_buffer=20, trailing_stop=0.2, sizing="invvol", max_weight=0.10,
            dyn_n_bear=15, dyn_mode="hold", bear_buffer=20, sector_cap=5)
ARMS = {"M12": "abs", "MM": "voladj", "RM12": "rm12", "RM24": "rm24", "RM36": "rm36"}
SUBS = [("2016-01-01", "2019-12-31"), ("2020-01-01", "2022-12-31"), ("2023-01-01", None)]


def turnover(run_dir: Path, eq: pd.Series) -> float:
    """One-way annual turnover: buy notional per year over mean portfolio value, 2016 onward."""
    f = run_dir / "trades.csv"
    if not f.exists():
        return np.nan
    t = pd.read_csv(f, parse_dates=["date"])
    t = t[(t.date >= "2016-01-01") & (t.side == "BUY")]
    e = eq[eq.index >= "2016-01-01"]
    if t.empty or e.empty:
        return np.nan
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    return t.notional.sum() / e.mean() / yrs


def main() -> None:
    rows, curves = [], {}
    for arm, kind in ARMS.items():
        cfg, _ = MM.run_candidate(**BASE, **CELL, kind=kind, skip=21)
        rid = MM.cfg_id(cfg); d = MM.RUNS / rid
        eq = W.equity(d); curves[arm] = eq
        end = str(eq.index[-1].date())
        st = W.stats(eq, "2016-01-01", end)
        row = {"arm": arm, "id": rid, "cagr": st["cagr"], "sharpe": st["sharpe"], "maxdd": st["maxdd"],
               "vol": st["vol"], "skew": st["skew"], "kurt": st["kurt"], "turnover": turnover(d, eq)}
        for a, z in SUBS:
            row[f"sh_{a[:4]}"] = W.stats(eq, a, z or end)["sharpe"]
        rows.append(row); print(f"  {arm} done ({rid})", flush=True)

    df = pd.DataFrame(rows).set_index("arm")
    df.to_csv(REPORT / "phase2_headline.csv")
    pd.DataFrame(curves).to_csv(REPORT / "phase2_equity.csv")

    print("\nStatic 2016 -> today, locked MM machinery, 20 bps each way\n")
    print(f"{'arm':6s} {'CAGR':>7s} {'Sharpe':>7s} {'maxDD':>7s} {'vol':>6s} {'skew':>6s} {'kurt':>6s} {'turn':>6s}"
          f" {'16-19':>6s} {'20-22':>6s} {'23-26':>6s}")
    for arm, r in df.iterrows():
        print(f"{arm:6s} {r['cagr']*100:6.1f}% {r['sharpe']:7.2f} {r['maxdd']*100:6.0f}% {r['vol']*100:5.1f}% "
              f"{r['skew']:6.2f} {r['kurt']:6.1f} {r['turnover']:5.2f}x "
              f"{r['sh_2016']:6.2f} {r['sh_2020']:6.2f} {r['sh_2023']:6.2f}")
    print(f"\nMM control target (MECHANICS.md): 25.2% / 1.15 / -27%")
    json.dump({k: {kk: (None if pd.isna(vv) else float(vv)) for kk, vv in v.items()}
               for k, v in df.drop(columns=["id"]).iterrows()}, open(REPORT / "phase2_headline.json", "w"), indent=1)


if __name__ == "__main__":
    main()
