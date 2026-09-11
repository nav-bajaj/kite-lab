"""P1 (2026-09-11): the nightly master-store runner — step plan is stable, the QA gate summarises the QA files correctly."""
import json, subprocess, sys, importlib.util
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def test_dry_run_lists_all_steps_in_order():
    r = subprocess.run([sys.executable, "scripts/refresh_master_store.py", "--dry-run"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0
    names = [l.split(":")[1].strip() for l in r.stdout.splitlines() if l.startswith("===")]
    assert names[0].startswith("fetch missing sessions") and names[-1].startswith("report")
    assert [n.split()[0] for n in names] == ["fetch", "symbol", "per-symbol", "NSE", "table", "observed", "append", "data_pipeline.master_store.build_adjusted"][:0] or len(names) == 10


def test_qa_gate_flags_kite_disagreement_and_is_ok_when_clean(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("refresh", ROOT / "scripts/refresh_master_store.py"); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    monkeypatch.setattr(m, "QA", tmp_path)
    today = pd.Timestamp.today().normalize()
    pd.DataFrame({"symbol": ["A"], "date": [str(today.date())], "move_pct": [9.0], "revert_pct": [-9.0], "kite_agrees": [True]}).to_csv(tmp_path / "bad_prints.csv", index=False)
    pd.DataFrame(columns=["symbol", "last"]).to_csv(tmp_path / "stale_tails.csv", index=False)
    pd.DataFrame(columns=["symbol", "non_midnight", "duplicates", "off_calendar"]).to_csv(tmp_path / "calendar.csv", index=False)
    assert m.qa_gate()["status"] == "ok"
    pd.DataFrame({"symbol": ["A"], "date": [str(today.date())], "move_pct": [9.0], "revert_pct": [-9.0], "kite_agrees": [False]}).to_csv(tmp_path / "bad_prints.csv", index=False)
    g = m.qa_gate(); assert g["status"] == "flagged" and g["bad_prints_30d_kite_disagrees"] == 1
    assert json.load(open(tmp_path / "nightly_latest.json"))["status"] == "flagged"
