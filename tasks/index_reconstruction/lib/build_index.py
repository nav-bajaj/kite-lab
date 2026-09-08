"""Reconstruct an index that NSE's export does not seed.

The Nifty 500 sheet opens with all 500 names on 1998-08-01, so it can be
replayed forward from the record alone. The Nifty 50 / 100 / LargeMidcap 250
sheets do not: they start mid-stream with a balanced set of replacements and
never state who was in the index at that moment.

So the membership at the earliest event date has to be DERIVED. Starting from
today's published constituent list and un-applying every event in reverse
order recovers it; the derived seed is then replayed forward through the same
code path used for the Nifty 500, and checked two ways:

  * the constituent count must hold at the index's fixed size throughout, and
  * the reconstruction must match NSE's March 2022 factsheet, which is an
    independent document neither source feeds.

Working in company-name space throughout, because the pre-2020 export has no
symbols. Renames are shared with the Nifty 500 tables - every constituent of
these indices is also a Nifty 500 constituent.
"""
from __future__ import annotations

import csv, datetime, collections, json, sys
sys.path.insert(0, "lib")
from renames import (EXCL_NAME_TO_INCL_NAME as RENAMES, PR_ERA_RENAMES,
                     DATED_ENTITY_RENAMES)
from renames import SURVIVOR_IDENTITY, LEGACY_RENAMES
from revocations import REVOKED, INDEX_REVOKED, INDEX_SUBSTITUTED
from scanned_releases import SCANNED_CHANGES

TODAY = datetime.date(2026, 9, 8)

SPECS = {
    "nifty50": ("Nifty 50", 50),
    "nifty100": ("Nifty 100", 100),
    "nifty250": ("Nifty LargeMidcap 250", 250),
}


def load_xls_events(slug: str) -> list[dict]:
    out = []
    for r in csv.DictReader(open(f"data/raw/{slug}_incl_excl.csv")):
        out.append({"date": datetime.date.fromisoformat(r["event_date"]),
                    "name": r["scrip_name"].strip(), "kind": r["action"],
                    "symbol": None, "src": "nse_incl_excl_xls"})
    return out


# Corporate actions announced as a bare list of affected index names, which
# the section parser cannot see. Tata Motors' DVR line was cancelled out of
# every index that held it (ind_prs23082024_1 lists Nifty 100, 200 and 500).
INDEX_CORPORATE_ACTIONS = {
    "nifty100": [("2024-08-30", "Tata Motors Ltd. DVR", "TATAMTRDVR", "out",
                  "ind_prs23082024_1")],
    "nifty250": [("2024-08-30", "Tata Motors Ltd. DVR", "TATAMTRDVR", "out",
                  "ind_prs23082024_1")],
}


def load_pr_events(slug: str, after: datetime.date) -> list[dict]:
    revoked = {(datetime.date.fromisoformat(d), s, k)
               for d, s, k in list(REVOKED) + INDEX_REVOKED.get(slug, [])}
    out = []
    rels = json.load(open(f"data/pr_{slug}_changes.json"))
    rels += SCANNED_CHANGES.get(slug, [])
    for rel in rels:
        eff = datetime.date.fromisoformat(rel["eff"])
        if eff <= after:
            continue
        for name, sym in rel["excluded"]:
            if (eff, sym, "out") in revoked:
                continue
            out.append({"date": eff, "name": name, "kind": "out",
                        "symbol": sym, "src": rel["file"]})
        for name, sym in rel["included"]:
            if (eff, sym, "in") in revoked:
                continue
            out.append({"date": eff, "name": name, "kind": "in",
                        "symbol": sym, "src": rel["file"]})
    for d, name, sym, kind, src in (INDEX_CORPORATE_ACTIONS.get(slug, [])
                                    + INDEX_SUBSTITUTED.get(slug, [])):
        dd = datetime.date.fromisoformat(d)
        if dd > after:
            out.append({"date": dd, "name": name, "kind": kind,
                        "symbol": sym, "src": src})
    return out


def _survivor_name_map():
    """old company name -> the name it appears under in today's index files.

    SURVIVOR_IDENTITY maps an old name to today's SYMBOL; joining that through
    the current constituent files turns it into a name-to-name link, which is
    what the backward walk needs in order to recognise that the "Zomato Ltd."
    an old release included is the "Eternal Ltd." sitting in today's list.
    """
    sym_to_name = {}
    for f in ("ind_nifty500list", "ind_nifty50list", "ind_nifty100list",
              "ind_niftylargemidcap250list"):
        try:
            rows = csv.DictReader(open(f"data/raw/{f}_2026-09-08.csv",
                                       encoding="utf-8-sig"))
        except OSError:
            continue
        for r in rows:
            sym_to_name[r["Symbol"].strip()] = r["Company Name"].strip()
    out = {}
    for old, sym in SURVIVOR_IDENTITY.items():
        new = sym_to_name.get(sym)
        if new and new != old:
            out[old] = new
    return out


def canonicalise(name: str, depth: int = 6) -> str:
    """Fold NSE's older spellings of a company onto its later name.

    The pre-2020 sheets for these indices spell the same company several ways
    across its life ("IDFC Ltd" on the exclusion, "Infrastructure Development
    Finance Company Limited" on the inclusion). Normalising every event name
    up front is simpler and safer than trying both lookup directions at each
    step, and it makes the replay independent of which spelling NSE happened
    to use on a given day.
    """
    seen = {name}
    while name in LEGACY_RENAMES and depth:
        name = LEGACY_RENAMES[name]
        depth -= 1
        if name in seen:
            break
        seen.add(name)
    return name


def _rename_maps():
    fwd = dict(RENAMES)
    fwd.update(PR_ERA_RENAMES)                 # exclusion-name -> inclusion-name
    inv = {v: k for k, v in fwd.items()}       # inclusion-name -> exclusion-name
    for _, old, new, _ in DATED_ENTITY_RENAMES:
        fwd[new] = old
        inv[old] = new
    for old, new in LEGACY_RENAMES.items():
        fwd.setdefault(new, old)
        inv.setdefault(old, new)
    for old, new in _survivor_name_map().items():
        fwd.setdefault(new, old)
        inv.setdefault(old, new)
    return fwd, inv


def events_for(slug: str) -> list[dict]:
    xls = load_xls_events(slug)
    handoff = max(e["date"] for e in xls)
    evs = xls + load_pr_events(slug, handoff)
    # changes announced for a future effective date have not happened yet, so
    # today's published constituent list does not reflect them
    evs = [e for e in evs if e["date"] <= TODAY]
    for e in evs:
        e["name"] = canonicalise(e["name"])
    evs.sort(key=lambda e: (e["date"], 0 if e["kind"] == "out" else 1))
    return evs


def derive_seed(slug: str, today_names: set, events: list[dict]):
    """Un-apply events newest-first to recover membership before the first one."""
    fwd, inv = _rename_maps()
    by_date = collections.OrderedDict()
    for e in events:
        by_date.setdefault(e["date"], []).append(e)

    members = set(today_names)
    problems = []
    for d in sorted(by_date, reverse=True):
        # undo inclusions first, then restore exclusions: the mirror of the
        # forward order, so a slot freed by an undone inclusion can be refilled
        for e in sorted(by_date[d], key=lambda e: 0 if e["kind"] == "in" else 1):
            n = e["name"]
            if e["kind"] == "in":
                # the member may be held under an earlier or a later name than
                # the one this inclusion used, so try both directions
                if n not in members:
                    for alt in (inv.get(n), fwd.get(n)):
                        if alt in members:
                            n = alt
                            break
                if n not in members:
                    problems.append((d, "undo-inclusion-of-nonmember", e["name"]))
                    continue
                members.discard(n)
            else:
                members.add(fwd.get(n, n))
    return members, problems


def replay_forward(seed: set, events: list[dict], seed_date: datetime.date):
    fwd, _ = _rename_maps()
    by_date = collections.OrderedDict()
    for e in events:
        by_date.setdefault(e["date"], []).append(e)
    members = {n: {"symbol": None, "since": seed_date} for n in seed}
    timeline, problems = [], []
    for d, evs in by_date.items():
        for e in evs:
            n = e["name"]
            if e["kind"] == "in":
                if n in members:
                    problems.append((d, "dup-inclusion", n))
                members[n] = {"symbol": e["symbol"], "since": d}
            else:
                if n not in members and fwd.get(n) in members:
                    n = fwd[n]
                if n not in members:
                    problems.append((d, "exclusion-of-nonmember", e["name"]))
                    continue
                if e["symbol"]:
                    members[n]["symbol"] = e["symbol"]
                del members[n]
        timeline.append((d, len(members)))
    return members, timeline, problems
