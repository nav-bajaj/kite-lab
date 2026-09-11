"""Summarise the cadence x universe runs: window metrics + post-tax overlay.

Reads every runs/<universe>_<cadence>/ produced by _cadence_run.py and emits:

  summary_windows.csv   per-run, per-window CAGR / Sharpe / Vol / MaxDD
  summary_headline.csv  one row per run: OOS_full metrics, turnover, tax
  summary_tax.csv       per-run, per-FY tax detail

Post-tax model is tasks/tax_study/tax_engine.py + forced_sale.py, with the
forced-sale slippage rate set to this study's 20 bps (the tax study used 30).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tasks" / "tax_study"))

from multi_window_oos_eval import evaluate_all_windows, passes_criteria  # noqa: E402
from tax_engine import compute_tax_per_fy, match_lots, fy_tax_to_dataframe  # noqa: E402
from forced_sale import build_tax_events  # noqa: E402

SLIPPAGE = 0.002  # matches the backtest

# Windows: the v3 retune's, with the tail extended to the panel end.
WINDOWS = [
    ("IS",       "2010-01-01", "2016-12-31"),
    ("OOS_A",    "2017-01-01", "2019-12-31"),
    ("OOS_B",    "2020-01-01", "2022-12-31"),
    ("OOS_C",    "2023-01-01", "2026-12-31"),
    ("OOS_full", "2017-01-01", "2026-12-31"),
]

ORDER = [
    ("nifty250", "weekly"), ("nifty250", "biweekly"), ("nifty250", "monthly"),
    ("nse500", "weekly"), ("nse500", "biweekly"), ("nse500", "monthly"),
]


def cagr(pv: pd.Series) -> float:
    yrs = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    return (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1


def main():
    runs_dir = HERE / "runs"
    win_rows, head_rows, tax_rows = [], [], []

    for uni, cad in ORDER:
        d = runs_dir / f"{uni}_{cad}"
        if not (d / "equity.csv").exists():
            print(f"  [skip] {uni}/{cad} — no equity.csv")
            continue
        label = f"{uni}/{cad}"
        meta = json.loads((d / "meta.json").read_text())
        eq = pd.read_csv(d / "equity.csv", parse_dates=["date"])
        trades = pd.read_csv(d / "trades.csv", parse_dates=["date"])
        exits = pd.read_csv(d / "exits.csv", parse_dates=["entry_date", "exit_date"])

        # ---- per-window metrics (pre-tax) ----
        wdf = evaluate_all_windows(eq, WINDOWS)
        wdf.insert(0, "run", label)
        win_rows.append(wdf)
        ok, reasons = passes_criteria(wdf)

        # ---- tax ----
        realized, open_pos = match_lots(trades)
        fys = compute_tax_per_fy(realized)
        events, scale = build_tax_events(fys, eq, slip_rate=SLIPPAGE)
        tdf = fy_tax_to_dataframe(fys)
        tdf.insert(0, "run", label)
        tax_rows.append(tdf)

        eq_i = eq.set_index("date")
        pv = eq_i["pv"].astype(float)
        scale.index = pv.index
        pv_post = pv * scale

        # OOS_full slice for both curves
        m = (pv.index >= pd.Timestamp("2017-01-01"))
        pre_oos, post_oos = pv[m], pv_post[m]

        yrs_full = (pv.index[-1] - pv.index[0]).days / 365.25
        total_tax = sum(e.total_drag for e in events)
        st_share = (sum(f.st_gross for f in fys if f.st_gross > 0) /
                    max(sum(f.st_gross for f in fys if f.st_gross > 0) +
                        sum(f.lt_gross for f in fys if f.lt_gross > 0), 1e-9))
        st_lots = [r for r in realized if r.bucket == "ST"]
        avg_hold = (sum(r.holding_days * r.shares for r in realized) /
                    max(sum(r.shares for r in realized), 1e-9))

        oos_row = wdf.set_index("window").loc["OOS_full"]
        head_rows.append({
            "run": label,
            "universe": uni,
            "cadence": cad,
            "n_entries": meta["n_entry_dates"],
            "oos_cagr_pct": oos_row["cagr_pct"],
            "oos_posttax_cagr_pct": round(cagr(post_oos) * 100, 2),
            "oos_sharpe": oos_row["sharpe"],
            "oos_maxdd_pct": oos_row["max_dd_pct"],
            "oos_vol_pct": oos_row["vol_pct"],
            "tax_drag_pp": round((cagr(pre_oos) - cagr(post_oos)) * 100, 2),
            "passes": "PASS" if ok else "FAIL",
            "fails": "; ".join(r for r in reasons if r.startswith("FAIL")) or "-",
            "buys": meta["n_buys"],
            "sells": meta["n_sells"],
            "roundtrips_per_yr": round(meta["n_sells"] / yrs_full, 1),
            "n_exits": len(exits),
            "exit_rank_pct": round(100 * (exits["reason"] == "rank").mean(), 1),
            "exit_stop_pct": round(100 * (exits["reason"] != "rank").mean(), 1),
            "exit_hit_rate_pct": round(100 * (exits["pnl_pct"] > 0).mean(), 1),
            "exit_med_pnl_pct": round(100 * exits["pnl_pct"].median(), 2),
            "avg_hold_days": round(avg_hold, 0),
            "st_gain_share_pct": round(st_share * 100, 1),
            "st_lot_share_pct": round(100 * len(st_lots) / max(len(realized), 1), 1),
            "total_tax_lakh": round(total_tax / 1e5, 1),
            "final_pv_pretax_cr": round(float(pv.iloc[-1]) / 1e7, 2),
            "final_pv_posttax_cr": round(float(pv_post.iloc[-1]) / 1e7, 2),
        })
        print(f"  [ok] {label:22s} OOS CAGR {oos_row['cagr_pct']:6.2f}%  "
              f"Sharpe {oos_row['sharpe']:.2f}  DD {oos_row['max_dd_pct']:7.2f}%  "
              f"post-tax {cagr(post_oos)*100:6.2f}%  {('PASS' if ok else 'FAIL')}")

    pd.concat(win_rows).to_csv(HERE / "summary_windows.csv", index=False)
    hdf = pd.DataFrame(head_rows)
    hdf.to_csv(HERE / "summary_headline.csv", index=False)
    pd.concat(tax_rows).to_csv(HERE / "summary_tax.csv", index=False)

    print("\n=== Headline (OOS_full 2017 → panel end) ===")
    cols = ["run", "n_entries", "oos_cagr_pct", "oos_posttax_cagr_pct",
            "oos_sharpe", "oos_maxdd_pct", "tax_drag_pp",
            "roundtrips_per_yr", "avg_hold_days", "st_gain_share_pct", "passes"]
    print(hdf[cols].to_string(index=False))

    print("\n=== Per-window Sharpe ===")
    allw = pd.concat(win_rows)
    print(allw.pivot(index="run", columns="window", values="sharpe")
          .reindex([f"{u}/{c}" for u, c in ORDER])
          [[w[0] for w in WINDOWS]].to_string())

    print("\n=== Per-window CAGR % ===")
    print(allw.pivot(index="run", columns="window", values="cagr_pct")
          .reindex([f"{u}/{c}" for u, c in ORDER])
          [[w[0] for w in WINDOWS]].to_string())

    print("\n=== Per-window MaxDD % ===")
    print(allw.pivot(index="run", columns="window", values="max_dd_pct")
          .reindex([f"{u}/{c}" for u, c in ORDER])
          [[w[0] for w in WINDOWS]].to_string())

    print(f"\n[wrote] {HERE}/summary_*.csv")


if __name__ == "__main__":
    main()
