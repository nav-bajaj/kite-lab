"""build_adjusted collects an ISIN-less `observed:` corporate action by ticker, and applies an
event once when it arrives both as an NSE filing and as an observed row.

The bug this pins (book_verification_2026 D-14): events were collected by the ISIN each identity
window carried, with the ticker used only for windows whose ISIN was unknown. Every row
derive_observed_events writes carries no ISIN, so for any company with a filing history — which is
to say any index member — the inferred split was silently dropped and the adjusted series kept an
unadjusted 50-90% one-day fall.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_pipeline.master_store import build_adjusted, identity  # noqa: E402

CA_COLS = ["isin", "symbol", "ex_date", "type", "factor_or_amount", "detail", "face_val", "series", "subject", "source"]
ISIN = "INE000A01010"
SESSIONS = pd.bdate_range("2020-01-01", periods=8)          # split ex-date is the 5th session
SPLIT_AT = SESSIONS[4]


def _filing(ex, typ, factor, detail="", face_val=10):
    return dict(isin=ISIN, symbol="ACME", ex_date=str(pd.Timestamp(ex).date()), type=typ, factor_or_amount=factor,
                detail=detail, face_val=face_val, series="EQ", subject=typ, source="nse-filing")


def _observed(ex, typ, factor):
    return dict(isin=None, symbol="ACME", ex_date=str(pd.Timestamp(ex).date()), type=typ, factor_or_amount=factor,
                detail="observed:kite-observed", face_val=None, series=None, subject="", source="kite-observed")


def _store(tmp_path: Path, ca_rows: list) -> Path:
    (tmp_path / "prices/bhavcopy").mkdir(parents=True)
    (tmp_path / "qa").mkdir()
    close = [100.0] * 4 + [50.0] * 4                        # the raw fall a 2:1 split leaves behind
    pd.DataFrame({"date": SESSIONS.date, "open": close, "high": close, "low": close, "close": close,
                  "volume": [1000] * 8, "traded_as": ["ACME"] * 8}).to_csv(tmp_path / "prices/bhavcopy/ACME.csv", index=False)
    pd.DataFrame(ca_rows, columns=CA_COLS).to_csv(tmp_path / "corporate_actions.csv", index=False)
    pd.DataFrame([{"isin": ISIN, "symbol": "ACME", "first_seen": str(SESSIONS[0].date()),
                   "last_seen": str(SESSIONS[-1].date()), "n_days": 8}]).to_csv(tmp_path / "symbol_master.csv", index=False)
    pd.DataFrame(columns=["company", "old", "new", "date"]).to_csv(tmp_path / "symbol_changes.csv", index=False)
    pd.DataFrame(columns=["old", "new", "t0", "t1", "c", "pc"]).to_csv(tmp_path / "symbol_renames_detected.csv", index=False)
    return tmp_path


def _run(tmp_path: Path, ca_rows: list, monkeypatch) -> pd.DataFrame:
    master = _store(tmp_path, ca_rows)
    monkeypatch.setattr(build_adjusted, "MASTER", str(master))
    monkeypatch.setattr(build_adjusted, "RAW", str(master / "prices/bhavcopy"))
    monkeypatch.setattr(build_adjusted, "OUT_PR", str(master / "prices/adjusted_pr"))
    monkeypatch.setattr(build_adjusted, "OUT_TR", str(master / "prices/adjusted_tr"))
    monkeypatch.setattr(identity, "MASTER", str(master))
    build_adjusted.main()
    return pd.read_csv(master / "prices/adjusted_pr/ACME.csv", parse_dates=["date"])


def test_observed_row_is_applied_even_when_the_window_has_a_known_isin(tmp_path, monkeypatch):
    """The dividend filing puts the window's ISIN in the by-ISIN index; the split has no ISIN."""
    adj = _run(tmp_path, [_filing(SESSIONS[1], "dividend", 2.0, "final"),
                          _observed(SPLIT_AT, "split", 0.5)], monkeypatch)
    assert adj.loc[adj["date"] < SPLIT_AT, "factor"].eq(0.5).all()
    assert adj["close"].eq(50.0).all(), "the split leaves a fall in the adjusted series"
    assert adj["factor"].iloc[-1] == 1.0


def test_a_filing_and_a_duplicate_observed_row_are_applied_once(tmp_path, monkeypatch):
    """Same event, two sources, one session apart: the filing wins and 0.5 is applied once."""
    adj = _run(tmp_path, [_filing(SPLIT_AT, "split", 0.5, "10->5"),
                          _observed(SESSIONS[5], "split", 0.5)], monkeypatch)
    assert adj.loc[adj["date"] < SPLIT_AT, "factor"].eq(0.5).all(), "0.25 means the event was applied twice"
    assert adj["close"].eq(50.0).all()


def test_drop_observed_covered_by_filing_keeps_an_unrelated_observed_row():
    ev = pd.DataFrame([_filing("2020-01-07", "split", 0.5, "10->5"),
                       _observed("2020-01-08", "split", 0.5),
                       _observed("2020-06-01", "split", 0.2)], columns=CA_COLS)
    kept = build_adjusted.drop_observed_covered_by_filing(ev)
    assert list(kept["ex_date"]) == ["2020-01-07", "2020-06-01"]


@pytest.mark.parametrize("splits_after, expected_fv", [([], 2.0), ([("2024-05-15", 0.2)], 10.0)])
def test_face_value_at_ex_date_undoes_later_splits(splits_after, expected_fv):
    """NSE reports faceVal as of the fetch: Canara Bank's 2017 rights row carries the post-2024
    Rs 2 face value, and the rights factor needs the Rs 10 that was in force."""
    rows = [_filing("2017-02-17", "rights", None, "1:10@prem=197.0", face_val=2)]
    rows += [_filing(d, "split", f, "10->2", face_val=2) for d, f in splits_after]
    ca = pd.DataFrame(rows, columns=CA_COLS)
    ca["ex_date"] = pd.to_datetime(ca["ex_date"]).dt.date
    assert build_adjusted.face_value_at_ex(ca).iloc[0] == pytest.approx(expected_fv)
