"""§1d — do the residual scores behave? Rank correlations between the five candidate scores, and the
degeneracy tell: a residual score that has collapsed into a one-month reversal signal shows a strongly
negative rank correlation against the trailing 21-session return (PLAN.md).
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent; TASK = HERE.parent; REPO = TASK.parent.parent
sys.path.insert(0, str(REPO))
OM_LIB = REPO / "tasks/om25_rebuild/lib"; sys.path.insert(0, str(OM_LIB))
_spec = importlib.util.spec_from_file_location("om25_run", OM_LIB / "run.py")
om = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(om)
from regime import membership_mask  # noqa: E402
from data_pipeline.strategies.momentum import make_momentum_score  # noqa: E402
from data_pipeline.strategies.sectors import load_sector_map  # noqa: E402
sys.path.insert(0, str(HERE))
from residual import make_residual_score  # noqa: E402

REPORT = TASK / "report"; REPORT.mkdir(exist_ok=True)
LOOKBACK, SKIP, MIN_OBS = 252, 21, 219
START = "2016-01-01"


def build(returns, bench, smap, members, candidate_fn):
    common = dict(lookback=LOOKBACK, skip=SKIP, min_obs=MIN_OBS, candidate_fn=candidate_fn)
    res = dict(member_mask=members, **common)
    return {
        "M12": make_momentum_score(returns, kind="abs", **common),
        "MM": make_momentum_score(returns, kind="voladj", vol_floor=0.05, **common),
        "RM12": make_residual_score(returns, bench, smap, mode="alpha", **res),
        "RM24": make_residual_score(returns, bench, smap, mode="resid", est_window=504, **res),
        "RM36": make_residual_score(returns, bench, smap, mode="resid", est_window=756, **res),
    }


def main() -> None:
    p = om.panels(); close = p["close"]; cal = close.index
    members = membership_mask(om.MEMBERSHIP["nifty250"], close)
    cols = [c for c in close.columns if members[c].any()]      # ever-members; candidate_fn applies PIT membership
    close, members = close[cols], members[cols]
    returns = close.pct_change()
    bench = p["bench"].pct_change()
    smap = load_sector_map()

    def candidate_fn(d):
        return set(members.columns[members.loc[d]])

    scores = build(returns, bench, smap, members, candidate_fn)
    names = list(scores)
    dates = om.monthly_on_or_after(cal, 1)
    dates = dates[(dates >= pd.Timestamp(START)) & (dates <= cal[-1])]

    corr_rows, cov_rows, tell_rows = [], [], []
    for d in dates:
        idx = cal.get_loc(d)
        if idx < 756:
            continue
        vals = {n: f(d) for n, f in scores.items()}
        if any(len(v) < 50 for v in vals.values()):
            continue
        df = pd.DataFrame(vals).dropna()
        corr_rows.append(df.rank().corr().stack().rename(d))
        cov_rows.append(pd.Series({n: len(v) for n, v in vals.items()}, name=d))
        # degeneracy tell: trailing 21 sessions (the skipped month) and the formation-window return
        r21 = (1 + returns.iloc[idx - SKIP + 1: idx + 1].fillna(0)).prod() - 1
        rform = (1 + returns.iloc[idx - LOOKBACK - SKIP + 1: idx - SKIP + 1].fillna(0)).prod() - 1
        rk = df.rank()
        r21r, rformr = r21.reindex(df.index).rank(), rform.reindex(df.index).rank()
        tell_rows.append(pd.Series({
            **{f"{n}_vs_r21": rk[n].corr(r21r) for n in names},
            **{f"{n}_vs_rform": rk[n].corr(rformr) for n in names},
        }, name=d))

    corr = pd.concat(corr_rows, axis=1).T
    cov = pd.DataFrame(cov_rows)
    tell = pd.DataFrame(tell_rows)
    corr.mean().unstack().to_csv(REPORT / "score_rank_correlation.csv")
    cov.to_csv(REPORT / "score_coverage.csv")
    tell.to_csv(REPORT / "score_degeneracy_tell.csv")

    print(f"{len(cov)} rebalances, {cov.index[0].date()} to {cov.index[-1].date()}\n")
    print("Mean names scored per rebalance")
    print(cov.mean().round(1).to_string())
    print("\nMean Spearman rank correlation between scores")
    print(corr.mean().unstack().loc[names, names].round(3).to_string())
    print("\nDegeneracy tell — rank correlation vs the SKIPPED trailing 21 sessions")
    print("  (strongly negative => the score has collapsed into a one-month reversal)")
    for n in names:
        s = tell[f"{n}_vs_r21"]
        print(f"  {n:5s} mean {s.mean():+.3f}   min {s.min():+.3f}   max {s.max():+.3f}")
    print("\nRank correlation vs the formation-window total return")
    for n in names:
        s = tell[f"{n}_vs_rform"]
        print(f"  {n:5s} mean {s.mean():+.3f}")


if __name__ == "__main__":
    main()
