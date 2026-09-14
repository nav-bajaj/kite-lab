"""§0 — what a longer beta-estimation window would cost us in eligibility.

RM-12 scores off the same 252/21 window MM already needs, so it adds no history
requirement. RM-24 and RM-36 need 504 and 756 priced sessions. This measures what
those two would drop from the *top-45 buffer* — the only names that can reach the
book — and what those names went on to return. Close-to-close forward returns; the
book executes at the next session's trade price, so these are indicative, not P&L.
"""
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent; TASK = HERE.parent; REPO = TASK.parent.parent
OM_LIB = REPO / "tasks/om25_rebuild/lib"; sys.path.insert(0, str(OM_LIB))
_spec = importlib.util.spec_from_file_location("om25_run", OM_LIB / "run.py")
om = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(om)
from regime import membership_mask  # noqa: E402

REPORT = TASK / "report"; REPORT.mkdir(exist_ok=True)
LOOKBACK, SKIP, MIN_OBS = 252, 21, 219   # MM's standing score window and eligibility rule
TOP_N, BUFFER = 25, 45
THRESHOLDS = {"rm24": 504, "rm36": 756}  # priced sessions of history the longer windows need
HORIZONS = {"fwd_1m": 21, "fwd_12m": 252}
START = "2016-01-01"


def mm_score(window: pd.DataFrame, vol_floor: float = 0.05) -> pd.Series:
    """MM's locked score: trailing return over the window / annualised daily vol, vol floored."""
    mom = (1 + window.fillna(0)).prod() - 1
    vol = (window.std() * np.sqrt(252)).clip(lower=vol_floor)
    return (mom / vol).dropna()


def main() -> None:
    p = om.panels(); close = p["close"]; cal = close.index
    members = membership_mask(om.MEMBERSHIP["nifty250"], close)
    returns = close.pct_change()
    history = close.notna().cumsum()          # priced sessions available up to and including each date
    dates = om.monthly_on_or_after(cal, 1)
    dates = dates[(dates >= pd.Timestamp(START)) & (dates <= cal[-1])]

    rows, excluded = [], []
    for d in dates:
        idx = cal.get_loc(d)
        if idx < LOOKBACK + SKIP:
            continue
        window = returns.iloc[idx - LOOKBACK - SKIP + 1: idx - SKIP + 1]
        elig = (window.notna().sum() >= MIN_OBS) & members.loc[d]
        cands = window.loc[:, elig[elig].index]
        if cands.shape[1] == 0:
            continue
        score = mm_score(cands)
        buf = score.nlargest(BUFFER)
        hist = history.loc[d]

        fwd = {}
        for name, h in HORIZONS.items():
            j = min(idx + h, len(cal) - 1)
            fwd[name] = (close.iloc[j] / close.iloc[idx] - 1) if j > idx else pd.Series(dtype=float)

        row = {"date": d, "members": int(members.loc[d].sum()), "scoreable": int(elig.sum()), "buffer": len(buf)}
        for tag, need in THRESHOLDS.items():
            drop = buf.index[hist.reindex(buf.index) < need]
            row[f"{tag}_drop_scoreable"] = int((elig & (hist < need)).sum())
            row[f"{tag}_drop_buffer"] = len(drop)
            row[f"{tag}_drop_top{TOP_N}"] = int((hist.reindex(buf.nlargest(TOP_N).index) < need).sum())
            for name in HORIZONS:
                row[f"{tag}_{name}"] = fwd[name].reindex(drop).mean() if len(drop) else np.nan
            for sym in drop:
                excluded.append({"date": d, "rule": tag, "symbol": sym, "rank": int(buf.index.get_loc(sym)) + 1,
                                 "sessions": int(hist[sym]), "score": float(buf[sym]),
                                 **{n: (float(fwd[n][sym]) if sym in fwd[n] and pd.notna(fwd[n][sym]) else np.nan) for n in HORIZONS}})
        for name in HORIZONS:
            row[f"buffer_{name}"] = fwd[name].reindex(buf.index).mean()
        rows.append(row)

    df = pd.DataFrame(rows).set_index("date")
    ex = pd.DataFrame(excluded)
    df.to_csv(REPORT / "eligibility_by_rebalance.csv")
    ex.to_csv(REPORT / "eligibility_excluded_names.csv", index=False)

    print(f"{len(df)} rebalances, {df.index[0].date()} to {df.index[-1].date()}\n")
    print("Mean per rebalance")
    print(f"  Nifty 250 members            {df['members'].mean():6.1f}")
    print(f"  scoreable under MM's rule    {df['scoreable'].mean():6.1f}")
    for tag, need in THRESHOLDS.items():
        print(f"\n{tag.upper()} ({need} sessions of history)")
        print(f"  dropped from scoreable     {df[f'{tag}_drop_scoreable'].mean():6.1f}"
              f"  ({df[f'{tag}_drop_scoreable'].mean() / df['scoreable'].mean() * 100:.1f}% of the pool)")
        print(f"  dropped from top-45 buffer {df[f'{tag}_drop_buffer'].mean():6.2f}"
              f"  (max {int(df[f'{tag}_drop_buffer'].max())}, zero at {(df[f'{tag}_drop_buffer'] == 0).mean() * 100:.0f}% of rebalances)")
        print(f"  dropped from top-25        {df[f'{tag}_drop_top{TOP_N}'].mean():6.2f}"
              f"  (max {int(df[f'{tag}_drop_top{TOP_N}'].max())})")
        for name in HORIZONS:
            e, b = df[f"{tag}_{name}"].mean(), df[f"buffer_{name}"].mean()
            print(f"  {name:8s} excluded {e * 100:6.2f}%  vs buffer {b * 100:6.2f}%  ->  {(e - b) * 100:+.2f} pp")

    yr = df.groupby(df.index.year).agg(
        {"scoreable": "mean", **{f"{t}_drop_buffer": "mean" for t in THRESHOLDS},
         **{f"{t}_drop_scoreable": "mean" for t in THRESHOLDS}}).round(2)
    yr.to_csv(REPORT / "eligibility_by_year.csv")
    print("\nBy year — mean names dropped from the top-45 buffer")
    print(yr[[f"{t}_drop_buffer" for t in THRESHOLDS]].to_string())


if __name__ == "__main__":
    main()
