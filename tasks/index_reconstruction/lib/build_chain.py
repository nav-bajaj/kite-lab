"""Replay every Nifty 500 membership event from 1998 to today.

Two sources, joined at 2020-09-14:
  * NSE's IndexInclExcl export (1998-08-01 .. 2020-09-14) - company names only.
  * NSE press releases (2020-09-14 .. today)              - names AND symbols.

Both cover 2020-09-14, but unequally: the CSV records only 1 of the 5 changes
the press release lists that day, so the CSV is cut strictly BEFORE the handoff
and the press release owns that date outright. Overlapping either way would
double-count or drop members.
"""
from __future__ import annotations

import csv, json, datetime, collections, sys
sys.path.insert(0, "lib")
from renames import (EXCL_NAME_TO_INCL_NAME as RENAMES, PR_ERA_RENAMES,
                     DATED_ENTITY_RENAMES)
from revocations import REVOKED, SUBSTITUTED, CORPORATE_ACTIONS

CSV_SRC = "data/raw/nse_incl_excl_1998_2020.csv"
PR_SRC = "data/pr_nifty500_changes.json"
HANDOFF = datetime.date(2020, 9, 14)


def _parse_date(s: str):
    s = s.strip()
    for f in ("%d-%m-%Y", "%m/%d/%y", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(s, f).date()
        except ValueError:
            pass
    raise ValueError(s)


def load_csv_events():
    rows = list(csv.DictReader(open(CSV_SRC, encoding="utf-8-sig")))
    seen, out = set(), []
    for r in rows:
        d, n = _parse_date(r["Event Date"]), r["Scrip Name"].strip()
        kind = "in" if r["Description"].startswith("Inclusion") else "out"
        k = (d, n, kind)
        if k in seen:          # NSE ships a handful of exact duplicate rows
            continue
        seen.add(k)
        if d >= HANDOFF:
            continue
        out.append({"date": d, "name": n, "kind": kind, "symbol": None,
                    "src": "nse_incl_excl"})
    return out


def load_pr_events(extra_renames=None):
    revoked = {(datetime.date.fromisoformat(d), sym, kind) for d, sym, kind in REVOKED}
    events = []
    for rel in json.load(open(PR_SRC)):
        eff = datetime.date.fromisoformat(rel["eff"])
        if eff < HANDOFF:
            continue
        for name, sym in rel["excluded"]:
            if (eff, sym, "out") in revoked:
                continue
            events.append({"date": eff, "name": name, "kind": "out",
                           "symbol": sym, "src": rel["file"]})
        for name, sym in rel["included"]:
            if (eff, sym, "in") in revoked:
                continue
            events.append({"date": eff, "name": name, "kind": "in",
                           "symbol": sym, "src": rel["file"]})
    for d, name, sym, kind, src in SUBSTITUTED + CORPORATE_ACTIONS:
        events.append({"date": datetime.date.fromisoformat(d), "name": name,
                       "kind": kind, "symbol": sym, "src": src})
    return events


def build(extra_renames=None, stop=None):
    """Replay; returns (members, timeline, problems).

    members: dict name -> {"symbol": str|None, "since": date}
    """
    ren = dict(RENAMES)
    ren.update(PR_ERA_RENAMES)
    if extra_renames:
        ren.update(extra_renames)
    events = load_csv_events() + load_pr_events()
    if stop:
        events = [e for e in events if e["date"] <= stop]
    # exclusions before inclusions on the same date: a slot is vacated before
    # it is refilled, which keeps the count at 500 through a reconstitution
    events.sort(key=lambda e: (e["date"], 0 if e["kind"] == "out" else 1))

    members: dict = {}
    problems, timeline = [], []
    by_date = collections.OrderedDict()
    for e in events:
        by_date.setdefault(e["date"], []).append(e)

    dated = sorted((datetime.date.fromisoformat(dt), old, new, sym)
                   for dt, old, new, sym in DATED_ENTITY_RENAMES)
    applied: set = set()   # fire once: the old name gets REUSED by a new
                           # company later, which must not be renamed too

    for d, evs in by_date.items():
        for rd, old, new, sym in dated:
            if rd <= d and old in members and (rd, old) not in applied:
                applied.add((rd, old))
                rec = members.pop(old)
                rec["symbol"] = sym
                members[new] = rec
        for e in evs:
            n = e["name"]
            if e["kind"] == "in":
                if n in members:
                    problems.append((d, "dup-inclusion", n))
                members[n] = {"symbol": e["symbol"], "since": d, "src": e["src"]}
            else:
                if n not in members and ren.get(n) in members:
                    n = ren[n]
                if n not in members:
                    problems.append((d, "exclusion-of-nonmember", e["name"]))
                    continue
                # carry the symbol the press release gave us onto the record
                if e["symbol"]:
                    members[n]["symbol"] = e["symbol"]   # later vintage wins
                del members[n]
        timeline.append((d, len(members)))
    return members, timeline, problems
