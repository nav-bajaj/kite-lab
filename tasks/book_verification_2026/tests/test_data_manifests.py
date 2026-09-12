"""Group H of TESTS_DATA.md — manifests and the QA files the nightly gate reads (D-39..D-42)."""
from __future__ import annotations

import hashlib
import json

import pandas as pd

from _store import corporate_actions, current_members, manifests, master, warn_count

QA_SCHEMAS = {
    "qa/bad_prints.csv": {"symbol", "date", "move_pct", "revert_pct", "kite_agrees"},
    "qa/stale_tails.csv": {"symbol", "last"},
    "qa/calendar.csv": {"symbol", "non_midnight", "duplicates", "off_calendar"},
    "qa/kite_steps_unexplained.csv": {"symbol", "date", "step", "p_cum"},
    "qa/adjustment_log.csv": {"symbol", "ex_date", "type", "factor", "note"},
    "qa/observed_events.csv": {"symbol", "ex_date", "source", "factor"},
    "corporate_actions.csv": {"isin", "symbol", "ex_date", "type", "factor_or_amount", "detail"},
}
NIGHTLY_KEYS = {"date", "status", "bad_prints_30d", "stale_tails", "calendar_issues", "kite_steps_unexplained_30d"}
HASHED_LAYERS = ("bhavcopy", "kite")


def test_d39_every_price_file_on_disk_is_in_its_manifest_with_a_matching_hash():
    m, man_all = master(), manifests()
    for layer in HASHED_LAYERS:
        man = man_all[layer]
        files = sorted((m / f"prices/{layer}").glob("*.csv"))
        assert files, f"D-39: prices/{layer} is empty"
        absent = [p.stem for p in files if p.stem not in man]
        assert not absent, f"D-39: {len(absent)} files in prices/{layer} have no manifest entry: {absent[:10]}"
        bad_hash, bad_rows = [], []
        for p in files:
            entry = man[p.stem]
            blob = p.read_bytes()
            if "sha256" in entry and hashlib.sha256(blob).hexdigest() != entry["sha256"]:
                bad_hash.append(p.stem)
            if "rows" in entry and blob.count(b"\n") - 1 != int(entry["rows"]):
                bad_rows.append((p.stem, blob.count(b"\n") - 1, int(entry["rows"])))
        assert not bad_hash, (f"D-39: {len(bad_hash)} files in prices/{layer} do not match their manifest sha256 — edited outside the "
                              f"pipeline: {bad_hash[:10]}")
        assert not bad_rows, f"D-39: {len(bad_rows)} files in prices/{layer} do not match their manifest row count: {bad_rows[:6]}"


def test_d40_no_manifest_entry_points_at_a_missing_file():
    m, members = master(), current_members()
    orphans, scoped = [], []
    for layer, man in manifests().items():
        d = m / f"prices/{layer}"
        on_disk = {p.stem for p in d.glob("*.csv")} if d.is_dir() else set()
        missing = sorted(set(man) - on_disk)
        orphans += [(layer, s) for s in missing]
        scoped += [(layer, s) for s in missing if s in members]
    by_layer = pd.Series([layer for layer, _ in orphans]).value_counts().to_dict() if orphans else {}
    warn_count("D-40", f"manifest entries with no file on disk, by layer {by_layer}; first {orphans[:8]}", len(orphans), cap=60)
    assert not scoped, f"D-40: manifest entries with no file on disk for current Nifty 250 members: {scoped}"


def test_d41_qa_files_parse_with_the_schema_the_gate_expects():
    m, ca = master(), corporate_actions()
    for rel, cols in QA_SCHEMAS.items():
        p = m / rel
        assert p.exists(), f"D-41: {rel} is missing, so the nightly gate has nothing to count"
        df = pd.read_csv(p)
        missing = cols - set(df.columns)
        assert not missing, f"D-41: {rel} is missing columns {sorted(missing)} (present: {list(df.columns)})"
    share = ca[ca["type"].isin(["bonus", "split", "consolidation"])]
    bad = share[share["factor_or_amount"].notna() & (share["factor_or_amount"] <= 0)]
    assert bad.empty, (f"D-41: {len(bad)} share-event rows in corporate_actions.csv have a non-positive factor: "
                       f"{bad.head(5).to_dict('records')}")
    conflict = ca.dropna(subset=["factor_or_amount"]).groupby(["symbol", "ex_date", "type"])["factor_or_amount"].nunique()
    warn_count("D-41", f"(symbol, ex_date, type) keys in corporate_actions.csv carrying conflicting factors — build_adjusted keeps the "
                       f"smallest: {conflict[conflict > 1].head(6).to_dict()}", int((conflict > 1).sum()), cap=50)


def test_d42_nightly_gate_output_is_fresh_and_self_consistent():
    m = master()
    p = m / "qa/nightly_latest.json"
    assert p.exists(), "D-42: qa/nightly_latest.json is missing — nothing says the nightly ran"
    gate = json.load(open(p))
    missing = NIGHTLY_KEYS - set(gate)
    assert not missing, f"D-42: qa/nightly_latest.json is missing keys {sorted(missing)}: {gate}"
    assert gate["status"] in ("ok", "flagged"), f"D-42: unexpected gate status {gate['status']!r}"
    counts = {"stale_tails": len(pd.read_csv(m / "qa/stale_tails.csv")), "calendar_issues": len(pd.read_csv(m / "qa/calendar.csv"))}
    drift = [k for k, v in counts.items() if int(gate[k]) != v]
    age = (pd.Timestamp.today().normalize() - pd.Timestamp(gate["date"])).days
    counters = {k: gate[k] for k in sorted(NIGHTLY_KEYS - {"date", "status"})}
    warn_count("D-42", f"nightly gate status {gate['status']!r} dated {gate['date']} ({age} days old), counters {counters}, "
                       f"counters disagreeing with the CSVs they summarise {drift}",
               max(age - 4, 0) + len(drift), cap=3)
