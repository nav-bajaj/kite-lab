"""C8.1 validity studies for the stock-level cohorts.

Reuses the run_study core from
tasks/insight_engine/pattern_validity_study.py (same sampling, same
matched NSE 500 unconditional baseline, same forward horizons) but feeds
it three insights_v2 cohorts whose "detector" is defined here:

  inflection     — the 21td rank-improvers cohort (rs_rank)
  rs_top_decile  — the strongest names by composite RS rank
  extension_high — names scoring Extension Risk ≥ High (framed as a RISK:
                   do stretched names underperform the baseline forward?)

Writes an honest report per cohort under tasks/insights_v2/VALIDITY/,
applying the VALIDITY_PROTOCOL.md tiers. A null/negative result is a
publishable finding, not a failure — thresholds are never massaged.

    python tasks/insights_v2/run_validity_studies.py [inflection|rs_top_decile|extension_high|all]
"""
from __future__ import annotations

import sys
from collections import namedtuple
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KITE_API = REPO / "kite-api"
for p in (KITE_API, REPO / "tasks" / "insight_engine"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pandas as pd  # noqa: E402

from app.insights import rs_rank, scores, stock_metrics, watchlists  # noqa: E402
from pattern_validity_study import HORIZONS, run_study  # noqa: E402

Fire = namedtuple("Fire", ["symbol", "score"])
_CLOSE: pd.DataFrame | None = None


def _close() -> pd.DataFrame:
    global _CLOSE
    if _CLOSE is None:
        _CLOSE = watchlists._stock_panel()
    return _CLOSE


def inflection_detector(asof, limit=25, **_):
    return rs_rank.get_inflection_cohort(asof, _close(), top_n=limit)


def rs_top_decile_detector(asof, limit=25, **_):
    table = rs_rank.compute_rs_table(asof, _close())
    ranked = [e for e in table.values() if e.rank is not None]
    ranked.sort(key=lambda e: e.rank)
    if not ranked:
        return []
    decile = max(1, int(0.10 * len(ranked)))
    return ranked[:min(limit, decile)]


def extension_high_detector(asof, limit=25, **_):
    metrics = stock_metrics.get_stock_metrics(asof)
    scored = []
    for sym, m in metrics.items():
        ext = scores._extension_risk(m)
        if ext is not None and ext >= 50.0:      # High or Very high band
            scored.append(Fire(sym, ext))
    scored.sort(key=lambda f: f.score, reverse=True)
    return scored[:limit]


COHORTS = {
    "inflection": inflection_detector,
    "rs_top_decile": rs_top_decile_detector,
    "extension_high": extension_high_detector,
}

# Framing per cohort: RS/inflection are momentum-positive claims; extension
# is a risk claim (we WANT to know if extended names lag).
RISK_FRAMED = {"extension_high"}


def _tier_and_verdict(name: str, h20) -> tuple[str, str]:
    """Apply VALIDITY_PROTOCOL.md tiers at the 20d headline horizon.
    Returns (tier_label, prose)."""
    excess = h20.excess_pp
    lift = h20.direction_lift_pp * 100
    n = h20.n_fires
    if name in RISK_FRAMED:
        # Risk framing: a genuine "these underperform" edge needs a
        # negative excess. Positive/flat excess means the risk label is
        # descriptive-only (a state, not a forward-return prediction).
        if excess <= -1.0 and lift < 0 and n >= 100:
            return ("validated-risk",
                    f"Extension-High names underperformed the baseline by "
                    f"{excess:+.2f}pp at 20d with a {lift:+.1f}pp direction "
                    f"drag (n={n}). The risk framing is empirically supported: "
                    "the UI MAY note the historical forward drag.")
        return ("names-only / descriptive",
                f"20d excess {excess:+.2f}pp, direction lift {lift:+.1f}pp "
                f"(n={n}). No reliable forward underperformance — 'Extended' "
                "must stay a DESCRIPTIVE state label ('stretched vs its own "
                "history'), never a forward-return or 'will mean-revert' claim.")
    # Momentum-positive framing
    if excess >= 1.0 and lift > 0 and n >= 100:
        return ("validated",
                f"Excess {excess:+.2f}pp AND direction lift {lift:+.1f}pp at "
                f"20d (n={n}). Meets the Validated tier — the cohort MAY carry "
                "a forward-return narrative with these figures disclosed.")
    if excess >= 0.3 and lift > 0 and n >= 100:
        return ("names-only",
                f"Excess {excess:+.2f}pp, direction lift {lift:+.1f}pp at 20d "
                f"(n={n}). Marginal — publish as NAMES-ONLY (no forward-return "
                "claim), footer noting the modest baseline excess.")
    return ("not-surfaced-as-prediction",
            f"Excess {excess:+.2f}pp, direction lift {lift:+.1f}pp at 20d "
            f"(n={n}). Below the bar — surface the cohort as an OBSERVATION "
            "only (rank changed / is strong), with NO forward-return framing.")


def _write_report(name: str, report) -> Path:
    h = {s.horizon_days: s for s in report.horizons}
    h20 = h.get(20)
    tier, prose = _tier_and_verdict(name, h20) if h20 else ("insufficient", "no 20d horizon")

    lines = [
        f"# Validity study — {name} (insights_v2 C8.1)",
        "",
        f"- Cohort: `{name}`  ·  framing: "
        f"{'RISK (do these underperform?)' if name in RISK_FRAMED else 'momentum-positive'}",
        "- Harness: tasks/insight_engine/pattern_validity_study.py (matched "
        "NSE 500 unconditional baseline, same sample dates)",
        f"- Sample dates: {report.sample_dates_count} (every 21 trading days)",
        "",
        "## Forward-return statistics",
        "",
        "| Horizon | N | Mean fwd % | Median | Baseline mean % | Excess (pp) "
        "| % positive | Baseline % pos | Direction lift (pp) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for hz in HORIZONS:
        s = h.get(hz)
        if not s:
            continue
        lines.append(
            f"| {s.horizon_days}d | {s.n_fires} | {s.mean_fwd_ret:+.2f}% | "
            f"{s.median_fwd_ret:+.2f}% | {s.baseline_mean:+.2f}% | "
            f"{s.excess_pp:+.2f} | {s.pct_positive*100:.0f}% | "
            f"{s.baseline_pct_positive*100:.0f}% | {s.direction_lift_pp*100:+.1f} |"
        )
    lines += ["", "## Verdict (VALIDITY_PROTOCOL.md tiers)", "",
              f"- **Tier: {tier}**", f"- {prose}", ""]
    # sign-consistency note (Test 4)
    signs = {s.horizon_days: (s.excess_pp > 0) for s in report.horizons}
    consistent = len(set(signs.values())) == 1
    sign_str = ", ".join(f"{k}d " + ("+" if v else "-") for k, v in signs.items())
    verdict_word = "consistent" if consistent else "FLIPS (fragile — treat with caution)"
    lines.append(
        f"- Sign consistency across 5/20/60/120d: {verdict_word} ({sign_str})."
    )
    for note in report.notes:
        lines.append(f"- {note}")

    out_dir = Path(__file__).parent / "VALIDITY"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{name}.md"
    out_path.write_text("\n".join(lines) + "\n")
    return out_path


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    names = list(COHORTS) if which == "all" else [which]
    panel = _close()
    print(f"panel: {panel.shape}  {panel.index[0].date()}→{panel.index[-1].date()}")
    for name in names:
        report = run_study(name, COHORTS[name], panel)
        path = _write_report(name, report)
        print(f"wrote {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
