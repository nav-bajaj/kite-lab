"""Windows, gates and the candidate registry.

IS 2006-2015. OOS 2016-today with sub-windows 2016-19, 2020-22, 2023-26.
Every candidate evaluated is appended to runs/registry.csv; the count is
what deflates the IS Sharpe (Bailey & Lopez de Prado deflated Sharpe: the
expected maximum Sharpe of N unrelated trials is subtracted before the
gate is applied). Gates G1-G7 as signed 2026-09-10 (TASKS.md s0).
"""
from __future__ import annotations

import csv, json, math, os
from pathlib import Path

import numpy as np
import pandas as pd

RUNS = Path(__file__).resolve().parent.parent / "runs"
REG = RUNS / "registry.csv"
WINDOWS = {"IS": ("2006-01-01", "2015-12-31"), "OOS": ("2016-01-01", "2099-12-31"),
           "OOS_a": ("2016-01-01", "2019-12-31"), "OOS_b": ("2020-01-01", "2022-12-31"), "OOS_c": ("2023-01-01", "2099-12-31")}
GATES = dict(G1_is_sharpe_deflated=0.9, G2_oos_sharpe=0.9, G3_sub_sharpe=0.6, G4_oos_maxdd=-0.40, G5_wf_gap=0.2, G6_params=8)


def stats(eq: pd.Series, a: str, b: str, rf=0.05) -> dict:
    s = eq[(eq.index >= a) & (eq.index <= b)]
    if len(s) < 60:
        return dict(cagr=np.nan, sharpe=np.nan, maxdd=np.nan, vol=np.nan, n=len(s))
    yrs = (s.index[-1] - s.index[0]).days / 365.25
    cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1
    r = s.pct_change().dropna(); vol = r.std() * math.sqrt(252)
    return dict(cagr=cagr, sharpe=(cagr - rf) / vol if vol > 0 else np.nan, maxdd=(s / s.cummax()).min() - 1, vol=vol,
                skew=float(r.skew()), kurt=float(r.kurt()) + 3, n=len(r))


def equity(cfg_dir) -> pd.Series:
    d = pd.read_csv(Path(cfg_dir) / "equity.csv", parse_dates=["date"]).set_index("date")
    return d["pv" if "pv" in d.columns else "portfolio_value"].astype(float)


def register(cfg: dict, cfg_id: str, st_is: dict, phase: str):
    new = not REG.exists()
    with open(REG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["phase", "id", "config", "is_cagr", "is_sharpe", "is_maxdd"])
        w.writerow([phase, cfg_id, json.dumps(cfg, sort_keys=True), round(st_is["cagr"], 4), round(st_is["sharpe"], 4), round(st_is["maxdd"], 4)])


def n_trials() -> int:
    if not REG.exists():
        return 0
    return len(set(r["id"] for r in csv.DictReader(open(REG))))   # a rerun after an interrupt must not double-count


def _phi_inv(p):   # Acklam's approximation, enough for N in the hundreds
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p)); return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1 - 0.02425:
        q = math.sqrt(-2 * math.log(1 - p)); return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5; r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def deflated_sharpe(sr_annual: float, n_obs: int, n_trials: int, skew: float, kurt: float, sr_var_annual: float = 0.25) -> tuple:
    """-> (haircut Sharpe, probability the observed Sharpe beats the expected
    max of n_trials unrelated trials). Annual Sharpe converted to per-period."""
    sr = sr_annual / math.sqrt(252); v = sr_var_annual / 252
    g = 0.5772156649
    if n_trials <= 1:
        e_max = 0.0
    else:
        e_max = math.sqrt(v) * ((1 - g) * _phi_inv(1 - 1 / n_trials) + g * _phi_inv(1 - 1 / (n_trials * math.e)))
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr * sr))
    z = (sr - e_max) * math.sqrt(max(n_obs - 1, 1)) / denom
    p = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return (sr - e_max) * math.sqrt(252), p


def observed_sr_var() -> float:
    """Variance of annual IS Sharpe across every registered trial — the V in
    the deflated-Sharpe formula, measured rather than assumed."""
    if not REG.exists():
        return 0.25
    v = pd.read_csv(REG)["is_sharpe"].astype(float).var()
    return float(v) if v == v and v > 0 else 0.25


def evaluate(cfg_dir, n_params: int, trials: int | None = None) -> dict:
    eq = equity(cfg_dir); out = {}
    for k, (a, b) in WINDOWS.items():
        out[k] = stats(eq, a, b)
    t = trials if trials is not None else max(n_trials(), 1)
    hs, p = deflated_sharpe(out["IS"]["sharpe"], out["IS"]["n"], t, out["IS"].get("skew", 0), out["IS"].get("kurt", 3),
                            sr_var_annual=observed_sr_var())
    out["IS_deflated_sharpe"], out["IS_dsr_prob"], out["trials"] = hs, p, t
    out["gates"] = dict(G1=hs >= GATES["G1_is_sharpe_deflated"], G2=out["OOS"]["sharpe"] >= GATES["G2_oos_sharpe"],
                        G3=all(out[k]["sharpe"] >= GATES["G3_sub_sharpe"] for k in ("OOS_a", "OOS_b", "OOS_c")),
                        G4=out["OOS"]["maxdd"] >= GATES["G4_oos_maxdd"], G6=n_params <= GATES["G6_params"])
    return out


def fmt(st):
    return f"{100*st['cagr']:5.1f}% / {st['sharpe']:4.2f} / {100*st['maxdd']:6.1f}%"
