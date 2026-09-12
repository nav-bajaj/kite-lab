"""Group C of TESTS_DATA.md — corporate-action adjustment consistency (D-12..D-19)."""
from __future__ import annotations

import pandas as pd

from _store import (BOOK_DATA_START, JUMP_THRESHOLD, SHARE_TYPES, corporate_actions, current_members, master, scan,
                    warn_count)

# One-session moves beyond JUMP_THRESHOLD that a human has confirmed as genuine market events rather than an
# unadjusted corporate action. Nothing is added here without a public reason.
REVIEWED_GENUINE_MOVES = {
    ("YESBANK", "2020-03-06"),   # RBI moratorium announced 2020-03-05
    ("YESBANK", "2020-03-17"),   # reconstruction scheme, the rebound
}


def test_d12_adjusted_close_reproduces_raw_close_times_factor():
    sc = scan()
    unaligned = sc.summary[sc.summary["raw_aligned"] == 0]
    assert unaligned.empty, (f"D-12: {len(unaligned)} symbols whose adjusted and bhavcopy files have different date indexes: "
                             f"{list(unaligned.index[:8])}")
    bad = sc.summary[sc.summary["adj_mismatch"] > 0]
    detail = [(s, str(d.date()), a, p, n) for s, d, a, p, n in sc.mismatches[:8]]
    assert bad.empty, (f"D-12: {int(bad['adj_mismatch'].sum())} symbol-days over {len(bad)} symbols where adjusted close != "
                       f"round(raw close x factor, 4) beyond one 4-dp tick; worst rows "
                       f"(symbol, date, adjusted, predicted, n): {detail}")


def test_d13_factor_steps_only_on_filed_ex_dates():
    steps = scan().unexplained_steps
    detail = [(s, str(d.date()), round(r, 5)) for s, d, r in steps[:10]]
    assert not steps, f"D-13: {len(steps)} factor steps with no corporate-action row within 4 days: {detail}"


def test_d14_share_events_for_current_members_in_the_book_era_are_applied():
    members = current_members()
    in_scope = [(s, d, t, f, obs) for s, d, t, f, obs in scan().unapplied_events
                if s in members and d >= BOOK_DATA_START]
    detail = [(s, str(d.date()), t, round(f, 6), "observed" if obs else "nse-filing")
              for s, d, t, f, obs in sorted(in_scope, key=lambda r: r[1])]
    assert not in_scope, (f"D-14: {len(in_scope)} {'/'.join(SHARE_TYPES)} events on current Nifty 250 members with ex-dates in the "
                          f"book data era are not reflected as a factor step, so the adjusted series carries an unadjusted "
                          f"split: {detail}")


def test_d15_share_event_application_gap_over_the_whole_store():
    events = scan().unapplied_events
    observed = sum(1 for *_, obs in events if obs)
    names = sorted({s for s, *_ in events})[:10]
    warn_count("D-15", f"share events inside a series span with no factor step ({observed} from observed:* rows derived by "
                       f"derive_observed_events, {len(events)-observed} from NSE filings); first symbols {names}",
               len(events), cap=700)


def test_d16_unexplained_one_day_moves():
    sc, members = scan(), current_members()
    bad_prints = pd.read_csv(master() / "qa/bad_prints.csv")
    known = set(zip(bad_prints["symbol"], bad_prints["date"].astype(str)))
    rows = [(s, d, r) for s, d, r in sc.jumps if (s, str(d.date())) not in known]
    in_scope = [(s, d, r) for s, d, r in rows
                if s in members and d >= BOOK_DATA_START and (s, str(d.date())) not in REVIEWED_GENUINE_MOVES]
    detail = [(s, str(d.date()), round(r, 4)) for s, d, r in sorted(in_scope, key=lambda x: x[1])]
    warn_count("D-16", f"one-session moves beyond {JUMP_THRESHOLD:.0%} in the adjusted view that neither a corporate action nor "
                       f"qa/bad_prints.csv explains", len(rows), cap=200)
    assert not in_scope, (f"D-16: {len(in_scope)} unexplained moves beyond {JUMP_THRESHOLD:.0%} on current Nifty 250 members inside "
                          f"the book data era — each is either a missing corporate-action filing or a reviewed genuine event to add "
                          f"to REVIEWED_GENUINE_MOVES: {detail}")


def test_d17_total_return_view_never_sits_above_price_return():
    summary = scan().summary
    unaligned = summary[summary["tr_aligned"] == 0]
    assert unaligned.empty, (f"D-17: {len(unaligned)} symbols whose adjusted_tr and adjusted_pr date indexes differ: "
                             f"{list(unaligned.index[:8])}")
    missing = summary[summary["tr_aligned"] == -1]
    assert missing.empty, f"D-17: {len(missing)} symbols have adjusted_pr but no adjusted_tr file: {list(missing.index[:8])}"
    bad = summary[summary["tr_above_pr"] > 0]
    assert bad.empty, (f"D-17: {len(bad)} symbols where the total-return factor exceeds the price-return factor — dividends are "
                       f"being applied with the wrong sign: {bad['tr_above_pr'].head(8).to_dict()}")


def test_d18_every_demerger_was_considered_by_the_adjustment_pass():
    sc = scan()
    log = pd.read_csv(master() / "qa/adjustment_log.csv", parse_dates=["ex_date"])
    logged = set(zip(log["symbol"], log["ex_date"]))
    dm = corporate_actions()[corporate_actions()["type"] == "demerger"]
    missing = []
    for e in dm.itertuples():
        if e.symbol not in sc.summary.index:
            continue
        row = sc.summary.loc[e.symbol]
        if not (pd.Timestamp(row["first"]) < e.ex_date <= pd.Timestamp(row["last"])):
            continue
        if (e.symbol, e.ex_date) not in logged:
            missing.append((e.symbol, str(e.ex_date.date())))
    assert not missing, (f"D-18: {len(missing)} demergers inside a symbol's span are absent from qa/adjustment_log.csv, so the "
                         f"adjustment pass never measured them: {missing[:10]}")


def test_d19_no_rights_issue_left_unadjusted_for_a_current_member():
    log = pd.read_csv(master() / "qa/adjustment_log.csv", parse_dates=["ex_date"])
    skipped = log[log["note"].isin(["rights:no-price", "rights:unparsed", "dividend:unparsed-or-implausible"])]
    rights = skipped[skipped["note"].str.startswith("rights")]
    in_scope = rights[(rights["symbol"].isin(current_members())) & (rights["ex_date"] >= BOOK_DATA_START)]
    warn_count("D-19", f"corporate actions the adjustment pass skipped for want of a parseable price ({len(rights)} rights, "
                       f"{len(skipped)-len(rights)} dividends — dividends are harmless in the price-return view)",
               len(skipped), cap=80)
    detail = [(r.symbol, str(r.ex_date.date()), r.note) for r in in_scope.itertuples()]
    assert in_scope.empty, (f"D-19: {len(in_scope)} rights issues on current Nifty 250 members in the book data era were applied as "
                            f"factor 1.0, i.e. not at all, so the ex-date drop stays in the series as a fake loss: {detail}")
