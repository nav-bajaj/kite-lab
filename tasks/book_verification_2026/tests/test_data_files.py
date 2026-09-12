"""Group A of TESTS_DATA.md — file and schema integrity of the price-return view the books read (D-01..D-08)."""
from __future__ import annotations

import os

import pandas as pd

from _store import PR_COLS, master, scan, warn_count


def _offenders(summary: pd.DataFrame, col: str, limit: int = 8):
    bad = summary[summary[col] > 0]
    return len(bad), bad[col].head(limit).to_dict()


def test_d01_every_adjusted_pr_file_parses_with_the_expected_schema():
    sc = scan()
    assert not sc.schema_errors, f"D-01: {len(sc.schema_errors)} files with a schema problem: {sc.schema_errors[:8]}"
    assert len(sc.summary) >= 2000, f"D-01: only {len(sc.summary)} adjusted_pr files scanned"
    assert len(PR_COLS) == 8


def test_d02_dates_are_midnight_unique_and_strictly_increasing():
    for col in ("nonmidnight", "dup_dates", "nonincreasing"):
        n, sample = _offenders(scan().summary, col)
        assert n == 0, f"D-02: {n} symbols with {col} rows: {sample}"


def test_d03_closes_are_finite_and_positive():
    for col in ("close_nan", "close_nonpositive"):
        n, sample = _offenders(scan().summary, col)
        assert n == 0, f"D-03: {n} symbols with {col}: {sample}"


def test_d04_ohlc_bars_are_internally_consistent():
    for col in ("ohl_nan", "high_below_low", "low_negative", "open_outside", "close_outside"):
        n, sample = _offenders(scan().summary, col)
        assert n == 0, f"D-04: {n} symbols with {col}: {sample}"


def test_d05_volumes_are_finite_and_non_negative():
    for col in ("volume_nan", "volume_negative"):
        n, sample = _offenders(scan().summary, col)
        assert n == 0, f"D-05: {n} symbols with {col}: {sample}"


def test_d06_factor_column_is_usable_and_ends_at_one():
    summary = scan().summary
    for col in ("factor_nan", "factor_nonpositive"):
        n, sample = _offenders(summary, col)
        assert n == 0, f"D-06: {n} symbols with {col}: {sample}"
    drift = summary[(summary["factor_last"] - 1.0).abs() > 1e-9]["factor_last"]
    assert drift.empty, f"D-06: {len(drift)} symbols whose last row is adjusted: {drift.head(8).to_dict()}"


def test_d07_panel_views_mirror_their_source_and_are_portable():
    m = master()
    non_portable = []
    for view in ("pr", "tr"):
        src, dst = m / f"prices/adjusted_{view}", m / f"panels/{view}"
        assert dst.is_dir(), f"D-07: panels/{view} missing"
        links = sorted(dst.glob("*_day.csv"))
        want = {p.stem for p in src.glob("*.csv") if not p.name.startswith(".")}
        got = {p.name[: -len("_day.csv")] for p in links}
        assert got == want, (f"D-07: panels/{view} out of step with prices/adjusted_{view}: only-source {sorted(want-got)[:6]}, "
                             f"only-view {sorted(got-want)[:6]}")
        broken = [p.name for p in links if not p.resolve().exists()]
        assert not broken, f"D-07: broken links in panels/{view}: {broken[:6]}"
        absolute = [p.name for p in links if p.is_symlink() and os.path.isabs(os.readlink(p))]
        assert not absolute, (f"D-07: non-relative links in panels/{view} (would break when the store is read from /data/master): "
                             f"{absolute[:6]}")
    for other in sorted(p for p in (m / "panels").iterdir() if p.is_dir() and p.name not in ("pr", "tr")):
        links = sorted(other.glob("*_day.csv"))
        if links and any(p.is_symlink() and os.path.isabs(os.readlink(p)) for p in links):
            non_portable.append(other.name)
    warn_count("D-07", f"panel views with absolute link targets (research views, not shipped): {non_portable}",
               len(non_portable), cap=1)


def test_d08_no_macos_sidecars_or_metadata_files_in_the_store():
    m = master()
    sidecars, junk = [], []
    for root, _dirs, files in os.walk(m):
        for name in files:
            if name.startswith("._"):
                sidecars.append(os.path.join(root, name))
            elif name == ".DS_Store":
                junk.append(os.path.join(root, name))
    rel = [os.path.relpath(p, m) for p in sidecars]
    assert not sidecars, (f"D-08: AppleDouble sidecars break every glob-based reader: {rel[:8]} "
                          f"(fix: data_pipeline.master_store.views.remove_junk_files)")
    warn_count("D-08", f"macOS metadata files under the store: {[os.path.relpath(p, m) for p in junk]}", len(junk), cap=6)
