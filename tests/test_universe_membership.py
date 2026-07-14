"""Spec: effective-dated universe membership + engine grandfather rule.

Decided 2026-07-14 (tasks/universe_membership): a universe change must never
force-exit a live position. Membership gates NEW ENTRIES only; a stock that
entered while it was a member exits by portfolio logic (rank), and once out
it cannot re-enter. Non-held non-members are invisible to the ranking — they
can't occupy a top-N slot, block an entrant, or push a holding out of the
keep set.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy
from scripts.universe_membership import (
    load_membership, all_ever_members, members_asof, make_membership_fn,
)


# ------------------------------------------------------------------
# Loader semantics
# ------------------------------------------------------------------

def _write_membership(tmp_path, rows):
    p = tmp_path / "membership.csv"
    df = pd.DataFrame(rows, columns=["symbol", "effective_from",
                                     "effective_to", "note"])
    df.to_csv(p, index=False)
    return p


def test_members_asof_boundaries(tmp_path):
    p = _write_membership(tmp_path, [
        ("AAA", "1900-01-01", "", ""),
        ("BBB", "1900-01-01", "2026-07-15", "removed at cutover"),
        ("CCC", "2026-07-15", "", "added at cutover"),
    ])
    df = load_membership(p)
    assert all_ever_members(df) == {"AAA", "BBB", "CCC"}
    # day before cutover: BBB in, CCC out
    assert members_asof(df, "2026-07-14") == {"AAA", "BBB"}
    # cutover day itself: effective_from inclusive, effective_to exclusive
    assert members_asof(df, "2026-07-15") == {"AAA", "CCC"}
    assert members_asof(df, "2027-01-01") == {"AAA", "CCC"}


def test_membership_fn_matches_members_asof(tmp_path):
    p = _write_membership(tmp_path, [
        ("AAA", "1900-01-01", "", ""),
        ("BBB", "1900-01-01", "2026-07-15", ""),
        ("CCC", "2026-07-15", "2026-09-01", "in and out"),
    ])
    df = load_membership(p)
    fn = make_membership_fn(df)
    for d in ["2020-01-01", "2026-07-14", "2026-07-15",
              "2026-08-31", "2026-09-01", "2030-01-01"]:
        assert fn(d) == frozenset(members_asof(df, d)), d


def test_load_membership_rejects_bad_rows(tmp_path):
    p = _write_membership(tmp_path, [("AAA", "2026-07-15", "2026-07-15", "")])
    with pytest.raises(ValueError):
        load_membership(p)
    p2 = tmp_path / "missing_col.csv"
    pd.DataFrame({"symbol": ["AAA"]}).to_csv(p2, index=False)
    with pytest.raises(ValueError):
        load_membership(p2)


# ------------------------------------------------------------------
# Engine grandfather rule
# ------------------------------------------------------------------
#
# 4 symbols, top_n=2, flat prices (no stop/drawdown effects), 5 weekly
# signals with hand-set scores. C leaves the universe at CUTOVER (cal[10]);
# D joins at CUTOVER.
#
# signal   scores (desc)              members       expected book after exec
# cal[2]   C=3  D=2.5 A=2  B=1        A,B,C         C,A   (D not member yet)
# cal[7]   same                       A,B,C         C,A   (no churn)
# cal[12]  C=3  D=2.5 A=2  B=1        A,B,D         C,D   (C grandfathered,
#                                                          D enters, A ranked out)
# cal[17]  C=.5 D=2.5 A=2  B=1        A,B,D         D,A   (C exits BY RANK)
# cal[22]  C=5  D=2.5 A=2  B=1        A,B,D         D,A   (C top score but
#                                                          invisible: no re-entry,
#                                                          doesn't displace A)

def _grandfather_fixture():
    cal = pd.bdate_range("2026-06-01", periods=30)
    syms = ["A", "B", "C", "D"]
    close = pd.DataFrame(100.0, index=cal, columns=syms)
    trade = close.copy()
    sma = pd.DataFrame(np.nan, index=cal, columns=syms)
    atr = pd.DataFrame(np.nan, index=cal, columns=syms)
    bench = pd.Series(100.0, index=cal)

    signal_dates = [cal[2], cal[7], cal[12], cal[17], cal[22]]
    scores = {
        cal[2]: {"A": 2.0, "B": 1.0, "C": 3.0, "D": 2.5},
        cal[7]: {"A": 2.0, "B": 1.0, "C": 3.0, "D": 2.5},
        cal[12]: {"A": 2.0, "B": 1.0, "C": 3.0, "D": 2.5},
        cal[17]: {"A": 2.0, "B": 1.0, "C": 0.5, "D": 2.5},
        cal[22]: {"A": 2.0, "B": 1.0, "C": 5.0, "D": 2.5},
    }

    def signal_function(date, **_):
        return pd.Series(scores.get(date, {}), dtype=float)

    cutover = cal[10]
    membership = pd.DataFrame({
        "symbol": ["A", "B", "C", "D"],
        "effective_from": [cal[0], cal[0], cal[0], cutover],
        "effective_to": [pd.NaT, pd.NaT, cutover, pd.NaT],
    })

    kwargs = dict(
        close_panel=close, trade_panel=trade, calendar=cal,
        benchmark_aligned=bench,
        entry_signal_dates=signal_dates, weekly_signal_dates=signal_dates,
        signal_function=signal_function, signal_function_args={},
        sma_200_panel=sma, atr_20_panel=atr,
        top_n=2, exit_buffer=0, max_weight=0.5, slippage=0.0,
        use_trailing_stop=False, use_dma_exit=False, min_hold_days=0,
    )
    return kwargs, membership, cal


def _buys_sells(result):
    tr = result["trades"]
    buys = {(r["date"], r["symbol"]) for _, r in tr.iterrows() if r["side"] == "BUY"}
    sells = {(r["date"], r["symbol"]) for _, r in tr.iterrows() if r["side"] == "SELL"}
    return buys, sells, tr


def test_grandfather_rule_end_to_end():
    kwargs, membership, cal = _grandfather_fixture()
    fn = make_membership_fn(membership)
    result = run_strategy(membership_fn=fn, **kwargs)
    buys, sells, tr = _buys_sells(result)
    buy_syms_by_date = {}
    for d, s in buys:
        buy_syms_by_date.setdefault(pd.Timestamp(d), set()).add(s)

    exec_1, exec_3 = cal[3], cal[13]          # exec day = signal day + 1
    exec_4, exec_5 = cal[18], cal[23]

    # entry while member: C and A bought at first rebalance
    assert buy_syms_by_date.get(exec_1) == {"A", "C"}
    # D never bought before its membership starts
    assert all(not (pd.Timestamp(d) < cal[10] and s == "D") for d, s in buys)

    # cutover rebalance: C grandfathered (NOT sold), D enters, A ranked out
    assert (exec_3, "C") not in sells
    assert (exec_3, "D") in buys
    assert (exec_3, "A") in sells

    # C exits by portfolio logic when its score collapses
    assert (exec_4, "C") in sells
    c_exit = result["exits"].query("symbol == 'C'")
    assert len(c_exit) == 1 and c_exit.iloc[0]["reason"] == "rank"

    # no re-entry: C tops the scores at cal[22] but is not a member and not
    # held — invisible. Nothing is bought or sold at exec_5.
    assert not any(pd.Timestamp(d) == exec_5 for d, _ in buys | sells)
    # and A (member, rank #2 among visible) is still held at the end
    signed = tr.assign(net=np.where(tr["side"] == "BUY",
                                    tr["shares"], -tr["shares"]))
    held = set(signed.groupby("symbol")["net"].sum().loc[lambda s: s > 0].index)
    assert held == {"A", "D"}


def test_membership_fn_none_equals_all_members_fn():
    """Depth change (full ranking vs top_n+buffer cut) must not alter behavior
    when every symbol is always a member."""
    kwargs, membership, cal = _grandfather_fixture()
    res_none = run_strategy(membership_fn=None, **kwargs)
    all_fn = lambda d: frozenset(["A", "B", "C", "D"])
    res_all = run_strategy(membership_fn=all_fn, **kwargs)
    pd.testing.assert_frame_equal(res_none["trades"], res_all["trades"])
    pd.testing.assert_frame_equal(res_none["equity"], res_all["equity"])
