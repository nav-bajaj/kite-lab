"""Group E of TESTS_DATA.md — benchmark and regime index series (D-26..D-29)."""
from __future__ import annotations

import pandas as pd

from _store import master, scan, warn_count

REGIME_INDEX = "NIFTY_100"                               # scripts/rebuilt_books.py STACK["regime_index"]
PAIRS = ("NIFTY_100", "NIFTY_500", "NIFTY_50", "NIFTY_MIDCAP_150")


def _read(p):
    return pd.read_csv(p, parse_dates=["date"]).sort_values("date")


def test_d26_every_benchmark_series_has_a_usable_schema():
    files = sorted((master() / "benchmarks").glob("*.csv"))
    assert files, "D-26: no benchmark files"
    for p in files:
        df = _read(p)
        assert {"date", "close"} <= set(df.columns), f"D-26: {p.name} columns {list(df.columns)}"
        assert not df["date"].duplicated().any(), f"D-26: {p.name} has duplicate dates"
        assert (df["date"].diff().dt.days.fillna(1) > 0).all(), f"D-26: {p.name} dates are not strictly increasing"
        assert df["close"].notna().all() and (df["close"] > 0).all(), f"D-26: {p.name} has a NaN or non-positive close"


def test_d27_bench_variants_agree_with_their_base_series():
    for name in PAIRS:
        a = master() / "benchmarks" / f"{name}.csv"
        b = master() / "benchmarks" / f"{name}_bench.csv"
        if not (a.exists() and b.exists()):
            continue
        sa = _read(a).set_index("date")["close"]; sb = _read(b).set_index("date")["close"]
        assert sa.index.equals(sb.index), f"D-27: {name} and {name}_bench have different date indexes ({len(sa)} vs {len(sb)})"
        diff = (sa - sb).abs().max()
        assert diff == 0, f"D-27: {name} and {name}_bench closes differ by up to {diff}"


def test_d28_regime_index_is_complete_and_current():
    sessions = scan().sessions
    s = _read(master() / f"benchmarks/{REGIME_INDEX}.csv").set_index("date")["close"]
    span = sessions[(sessions >= s.index.min()) & (sessions <= s.index.max())]
    gaps = span.difference(s.index)
    assert gaps.empty, (f"D-28: {REGIME_INDEX}.csv is missing {len(gaps)} store sessions, so roc_regime compares rows that are not "
                        f"31 sessions apart: {[str(d.date()) for d in gaps[:8]]}")
    assert s.index.max() == sessions[-1], (f"D-28: {REGIME_INDEX}.csv ends {s.index.max().date()} but the store's latest session is "
                                          f"{sessions[-1].date()} — the regime would be frozen at its last reading")


def test_d29_other_benchmark_series_have_no_session_gaps():
    sessions = scan().sessions
    report, total = [], 0
    for p in sorted((master() / "benchmarks").glob("*.csv")):
        if p.stem == REGIME_INDEX:
            continue
        s = _read(p).set_index("date")["close"]
        span = sessions[(sessions >= s.index.min()) & (sessions <= s.index.max())]
        gaps = span.difference(s.index)
        behind = len(sessions[sessions > s.index.max()])
        if len(gaps) or behind:
            report.append(f"{p.name}: {len(gaps)} gaps {[str(d.date()) for d in gaps[:3]]}, {behind} sessions behind the store")
        total += len(gaps)
    warn_count("D-29", "session gaps in the benchmark series the books do not read — " + " | ".join(report), total, cap=10)
