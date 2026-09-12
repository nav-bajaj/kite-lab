"""Group G of TESTS_DATA.md — the offline Kite cross-check (D-36..D-38).

Kite's day candles are back-adjusted on every corporate action *and* on dividends; the view the books read is price
return. So the ratio adjusted_pr/kite is expected to step at every meaningful dividend: D-36 is a census, D-37 looks
only at steps too large to be a dividend, and D-38 is the hard, holdings-scoped version.
"""
from __future__ import annotations

import pytest

from _store import BOOK_DATA_START, book_holdings, current_members, kite_ratio_steps, warn_count

SHARE_SCALE = 0.10          # a step this large cannot be an ordinary Indian dividend


def test_d36_price_return_view_against_kite_step_census():
    df = kite_ratio_steps()
    warn_count("D-36", f"steps beyond 0.4% in adjusted_pr/kite over {df['symbol'].nunique()} symbols — expected, because Kite's series "
                       f"is dividend-adjusted and the price-return view is not", len(df), cap=25_000)


def test_d37_large_share_scale_disagreements_with_kite():
    df = kite_ratio_steps()
    big = df[((df["step"] - 1).abs() > SHARE_SCALE) & (~df["dividend_explained"])]
    in_scope = big[(big["symbol"].isin(current_members())) & (big["date"] >= BOOK_DATA_START)].sort_values("date")
    detail = [(r.symbol, str(r.date.date()), round(r.step, 5), "ca-row-present" if r.near_ca else "no-ca-row")
              for r in in_scope.itertuples()]
    warn_count("D-37", f"steps beyond {SHARE_SCALE:.0%} in adjusted_pr/kite that no dividend explains, i.e. a corporate action one side "
                       f"did not apply or applied with a different factor; current Nifty 250 members inside the book data "
                       f"era: {detail}", len(big), cap=400)


@pytest.mark.skip(reason="D-38: needs the runner's holdings — no data/<book>_portfolios/latest.json exists locally for mm_v1 or om25_v4. "
                         "Un-skips once scripts/run_rebuilt_book.py has been run here. The live-Kite equivalent is fortnightly check 1.")
def test_d38_held_names_reconcile_against_kite():
    holdings = book_holdings()
    held = set().union(*holdings.values()) if holdings else set()
    df = kite_ratio_steps()
    big = df[((df["step"] - 1).abs() > SHARE_SCALE) & (~df["dividend_explained"])]
    in_scope = big[(big["symbol"].isin(held)) & (big["date"] >= BOOK_DATA_START)]
    detail = [(r.symbol, str(r.date.date()), round(r.step, 5)) for r in in_scope.itertuples()]
    assert in_scope.empty, f"D-38: {len(in_scope)} share-scale adjustment disagreements on names a book currently holds: {detail}"
