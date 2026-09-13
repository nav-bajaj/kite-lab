"""Runner for §2-§5. Writes JSON/CSV artefacts under data/ for RESULTS.md."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from regimes import (ALL_VARS, BREADTH_VARS, DATA, FIT_END, ROOT, START,
                     agreement, c3_asymmetric, detection_lag, fitted_labels,
                     hysteresis, majority_vote, persistence, realtime_labels,
                     risk_map, runs, zigzag)

V = pd.read_parquet(os.path.join(DATA, "state_vars.parquet"))
sig = pd.read_parquet(os.path.join(ROOT, "tasks/regime_allocation_2026/data/signals.parquet"))
V["composite"] = sig["composite"].reindex(V.index)
V = V.loc[START:]

CORE = ["pct_above_200", "pct_leading", "net_highs", "breadth_dd", "divergence",
        "dispersion", "correlation", "vol21", "vol_ratio", "trend_quality", "part_skew"]
S1 = V[CORE].describe().T[["mean", "std", "min", "max", "count"]]
S1["first_valid"] = [str(V[c].first_valid_index().date()) for c in CORE]
S1.round(4).to_csv(os.path.join(DATA, "s1_state_vars.csv"))
print(S1.round(4).to_string(), flush=True)

tps = zigzag(V.index_close.dropna())
tps.to_csv(os.path.join(DATA, "turning_points.csv"), index=False)
print("turning points:", tps.kind.value_counts().to_dict(), flush=True)

CANDS: dict[str, pd.Series] = {}
CANDS["C1 hyst40/60 pct_above_200"] = hysteresis(V.pct_above_200, 0.60, 0.40)
CANDS["C2 hyst40/60 composite"] = hysteresis(V.composite, 0.60, 0.40)
CANDS["C3 asymmetric divergence"] = c3_asymmetric(V)
for k in (2, 3, 4):
    CANDS[f"C4 kmeans k={k}"] = fitted_labels(V, ALL_VARS, "kmeans", k)
for k in (2, 3):
    CANDS[f"C5 GMM k={k} all"] = fitted_labels(V, ALL_VARS, "gmm", k)
    CANDS[f"C6 GMM k={k} breadth"] = fitted_labels(V, BREADTH_VARS, "gmm", k)

lab_df = pd.DataFrame(CANDS)
lab_df.to_parquet(os.path.join(DATA, "candidate_labels.parquet"))

C1 = CANDS["C1 hyst40/60 pct_above_200"]
C1_MAP = risk_map(C1, V)

rows, detail = [], {}
for name, lab in CANDS.items():
    p = persistence(lab)
    rmap = risk_map(lab, V)
    d = detection_lag(lab, tps, rmap)
    # window-matched benchmark: C1 scored over this candidate's own valid span,
    # so R3 never compares a short-history candidate against a longer one
    bm = detection_lag(C1.reindex(lab.dropna().index), tps, C1_MAP)
    rows.append(dict(candidate=name, states=p["n_states"], median_run=p["median_run"],
                     share_le5=p["share_le5"], flips_yr=p["flips_yr"],
                     lag_peaks=d["lag_peaks"], lag_troughs=d["lag_troughs"],
                     cens_peaks=d["cens_peaks"], cens_troughs=d["cens_troughs"],
                     bm_peaks=bm["lag_peaks"], bm_troughs=bm["lag_troughs"],
                     bm_cens_p=bm["cens_peaks"], bm_cens_t=bm["cens_troughs"],
                     n_ev_p=d["n_peaks"], n_ev_t=d["n_troughs"],
                     n_runs=p["n_runs"], first=str(p["first"].date()), last=str(p["last"].date())))
    detail[name] = {"persistence": {k: (str(v) if isinstance(v, pd.Timestamp) else v)
                                    for k, v in p.items()},
                    "risk_map": rmap, "lag": {k: v for k, v in d.items()},
                    "benchmark_matched": {k: v for k, v in bm.items()}}

T = pd.DataFrame(rows)
T["R1"] = T.median_run >= 60
T["R2"] = T.share_le5 <= 0.15
beats_p = (T.lag_peaks < T.bm_peaks) & (T.cens_peaks <= T.bm_cens_p)
beats_t = (T.lag_troughs < T.bm_troughs) & (T.cens_troughs <= T.bm_cens_t)
T["R3"] = T.R1 & T.R2 & (beats_p | beats_t)
T.loc[T.candidate.str.startswith("C1"), "R3"] = False  # C1 is the benchmark
T["pass"] = T.R1 & T.R2 & T.R3
T.to_csv(os.path.join(DATA, "gate_table.csv"), index=False)
print(T.to_string(), flush=True)

with open(os.path.join(DATA, "gate_detail.json"), "w") as f:
    json.dump(detail, f, indent=1, default=str)

# ---- §4 real-time identifiability, survivors only -------------------------
surv = T[T["pass"]].candidate.tolist()
rt_rows = []
for name in surv:
    if name.startswith(("C1", "C2", "C3")):
        rt_rows.append(dict(candidate=name, agree=1.0, catchup=0.0, n=int(CANDS[name].notna().sum()),
                            note="rule-based, no fitted parameters: causal by construction"))
        continue
    kind = "kmeans" if name.startswith("C4") else "gmm"
    k = int(name.split("k=")[1].split()[0])
    cols = BREADTH_VARS if "breadth" in name else ALL_VARS
    ref, rt = realtime_labels(V, cols, kind, k)
    a = agreement(ref, rt)
    rt_rows.append(dict(candidate=name, agree=a["agree"], catchup=a["catchup"], n=a["n"], note=""))
R4 = pd.DataFrame(rt_rows)
if not R4.empty:
    R4["pass"] = R4.agree >= 0.80
    R4.to_csv(os.path.join(DATA, "realtime_table.csv"), index=False)
    print(R4.to_string(), flush=True)

# ---- §5 characterisation of §4 survivors ----------------------------------
ir = V.index_close.pct_change()
char = {}
for name in (R4[R4["pass"]].candidate.tolist() if not R4.empty else []):
    lab = CANDS[name].dropna()
    r = runs(lab)
    out = {}
    for st, g in lab.groupby(lab):
        d = g.index
        sub_r = ir.reindex(d)
        eq = (1 + sub_r.fillna(0)).cumprod()
        out[st] = dict(
            days=int(len(d)), freq=float(len(d) / len(lab)),
            median_run=float(r[r.state == st].n.median()), n_runs=int((r.state == st).sum()),
            ann_ret=float((1 + sub_r.mean()) ** 252 - 1),
            ann_vol=float(sub_r.std() * np.sqrt(252)),
            mean_dd_in_state=float(V.idx_dd.reindex(d).mean()),
            worst_dd_in_state=float(V.idx_dd.reindex(d).min()),
            pct_above_200=float(V.pct_above_200.reindex(d).mean()),
            dispersion=float(V.dispersion.reindex(d).mean()),
            correlation=float(V.correlation.reindex(d).mean()),
            vol21=float(V.vol21.reindex(d).mean()),
            trend_quality=float(V.trend_quality.reindex(d).mean()),
        )
    nxt = lab.shift(-1)
    tm = pd.crosstab(lab, nxt, normalize="index")
    char[name] = {"states": out, "transition": tm.round(4).to_dict()}
with open(os.path.join(DATA, "characterisation.json"), "w") as f:
    json.dump(char, f, indent=1, default=str)
print("done", flush=True)
