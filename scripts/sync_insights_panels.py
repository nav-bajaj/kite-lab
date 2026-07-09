"""Append fresh live data to the long-history panels used by the
insight engine.

The insight modules read from:
  - nse500_data_merged/<SYM>_day.csv   (split-adjusted, ~16y of history)
  - /Users/navdeep/Documents/stock_data/indices_data_full/<IDX>.csv
                                         (16y of indices + VIX)

The daily fetch lands in:
  - nse500_data/<SYM>_day.csv     (live Kite, no historical depth)
  - indices_data/<IDX>.csv         (live, current-cycle)

These two sets normally drift apart between refreshes. This script
brings the long-history panels up to date by appending any new dates
from the live folders that the long-history files don't already have.

Safe-by-construction:
  - Only APPENDS; never modifies existing rows
  - Skips any symbol where the live file is missing or has no new dates
  - Verifies the live header matches the long-history header before appending
  - For split-adjusted merged stocks: assumes no new splits since the last
    merge ran (true for our typical daily cadence — apply_corporate_actions.py
    handles splits separately in the live file)

Run as the last step of the daily refresh, before clearing the insights
cache + restarting the API.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

# Reuse the engine's indices-dir resolver so the append target matches the
# path the API actually reads (env override → local Documents → data_dir
# fallback). Without this the script could append to a folder no reader sees.
_KITE_API = REPO_ROOT / "kite-api"
if str(_KITE_API) not in sys.path:
    sys.path.insert(0, str(_KITE_API))
from app.insights._paths import indices_dir  # noqa: E402

LIVE_STOCKS = REPO_ROOT / "nse500_data"
MERGED_STOCKS = REPO_ROOT / "nse500_data_merged"
LIVE_INDICES = REPO_ROOT / "indices_data"
HIST_INDICES = indices_dir()


def _append_new_rows(live_path: Path, target_path: Path) -> tuple[int, str | None]:
    """Append rows from `live_path` to `target_path` for dates newer than
    target's current max. Returns (n_appended, new_max_date_or_none).
    """
    if not live_path.exists() or not target_path.exists():
        return 0, None
    live = pd.read_csv(live_path, parse_dates=["date"]).sort_values("date")
    target = pd.read_csv(target_path, parse_dates=["date"]).sort_values("date")
    if live.empty or target.empty:
        return 0, None

    # Header check — schemas must match for a safe append
    if list(live.columns) != list(target.columns):
        return 0, None

    max_target = target["date"].max()
    new_rows = live[live["date"] > max_target]
    if new_rows.empty:
        return 0, max_target.strftime("%Y-%m-%d")

    combined = pd.concat([target, new_rows], ignore_index=True)
    combined.to_csv(target_path, index=False)
    return len(new_rows), new_rows["date"].max().strftime("%Y-%m-%d")


def sync_stocks() -> None:
    print(f"[stocks] live={LIVE_STOCKS}  →  merged={MERGED_STOCKS}")
    if not LIVE_STOCKS.exists() or not MERGED_STOCKS.exists():
        print("  one of the dirs missing — skipping")
        return
    appended_total = 0
    n_files_touched = 0
    n_files_skipped = 0
    by_new_max: dict[str, int] = {}
    for live_file in sorted(LIVE_STOCKS.glob("*_day.csv")):
        target = MERGED_STOCKS / live_file.name
        n, new_max = _append_new_rows(live_file, target)
        if n > 0:
            appended_total += n
            n_files_touched += 1
            by_new_max[new_max] = by_new_max.get(new_max, 0) + 1
        elif not target.exists():
            n_files_skipped += 1
    print(f"  {n_files_touched} files updated, {appended_total} new rows total")
    if n_files_skipped:
        print(f"  {n_files_skipped} live files had no merged counterpart (skipped)")
    print(f"  new max-date distribution: {dict(sorted(by_new_max.items()))}")


def sync_indices() -> None:
    print(f"[indices] live={LIVE_INDICES}  →  hist={HIST_INDICES}")
    if not LIVE_INDICES.exists() or not HIST_INDICES.exists():
        print("  one of the dirs missing — skipping")
        return
    appended_total = 0
    n_files_touched = 0
    n_files_skipped = 0
    by_new_max: dict[str, int] = {}
    for live_file in sorted(LIVE_INDICES.glob("*.csv")):
        target = HIST_INDICES / live_file.name
        if not target.exists():
            n_files_skipped += 1
            continue
        n, new_max = _append_new_rows(live_file, target)
        if n > 0:
            appended_total += n
            n_files_touched += 1
            by_new_max[new_max] = by_new_max.get(new_max, 0) + 1
    print(f"  {n_files_touched} indices updated, {appended_total} new rows total")
    if n_files_skipped:
        print(f"  {n_files_skipped} live indices had no historical counterpart (skipped)")
    print(f"  new max-date distribution: {dict(sorted(by_new_max.items()))}")


def main() -> None:
    sync_stocks()
    print()
    sync_indices()


if __name__ == "__main__":
    main()
