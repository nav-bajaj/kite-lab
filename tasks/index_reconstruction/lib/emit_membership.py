"""Write the reconstructed Nifty 500 history out in two forms.

  nse500_events_reconstructed.csv     - one row per membership event
  nse500_membership_reconstructed.csv - one row per membership WINDOW, in the
                                        repo's data/static/*_membership.csv
                                        schema (symbol, effective_from,
                                        effective_to, note)

A company that leaves and later rejoins gets one window per spell, which is
what the effective-dated membership loader expects.
"""
from __future__ import annotations

import csv, datetime, collections, sys
sys.path.insert(0, "lib")
import build_chain
import resolve_symbols as rs

OUT_EVENTS = "data/nse500_events_reconstructed.csv"
OUT_MEMBERSHIP = "data/nse500_membership_reconstructed.csv"
OUT_UNRESOLVED = "data/unresolved_symbols.csv"


def windows():
    """Replay and record (name, from, to, symbol) spells."""
    events = build_chain.load_csv_events() + build_chain.load_pr_events()
    events.sort(key=lambda e: (e["date"], 0 if e["kind"] == "out" else 1))
    by_date = collections.OrderedDict()
    for e in events:
        by_date.setdefault(e["date"], []).append(e)

    ren = dict(build_chain.RENAMES)
    ren.update(build_chain.PR_ERA_RENAMES)
    dated = sorted((datetime.date.fromisoformat(d), o, n, s)
                   for d, o, n, s in build_chain.DATED_ENTITY_RENAMES)
    applied = set()

    open_spell: dict = {}
    spells: list = []
    for d, evs in by_date.items():
        for rd, old, new, sym in dated:
            if rd <= d and old in open_spell and (rd, old) not in applied:
                applied.add((rd, old))
                rec = open_spell.pop(old)
                rec["symbol"] = sym
                rec["name"] = new
                open_spell[new] = rec
        for e in evs:
            n = e["name"]
            if e["kind"] == "in":
                open_spell[n] = {"name": n, "from": d, "symbol": e["symbol"],
                                 "src_in": e["src"]}
            else:
                if n not in open_spell and ren.get(n) in open_spell:
                    n = ren[n]
                rec = open_spell.pop(n, None)
                if rec is None:
                    continue
                if e["symbol"] and not rec["symbol"]:
                    rec["symbol"] = e["symbol"]
                rec["to"] = d
                rec["src_out"] = e["src"]
                spells.append(rec)
    for rec in open_spell.values():
        rec["to"] = None
        rec["src_out"] = ""
        spells.append(rec)
    spells.sort(key=lambda r: (r["name"], r["from"]))
    return events, spells


def main() -> None:
    events, spells = windows()
    by_name, by_norm = rs.current_maps()
    by_instr = rs.instrument_map()

    with open(OUT_EVENTS, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "action", "company_name", "symbol", "source"])
        for e in sorted(events, key=lambda x: (x["date"], x["kind"], x["name"])):
            w.writerow([e["date"], "include" if e["kind"] == "in" else "exclude",
                        e["name"], e["symbol"] or "", e["src"]])

    resolved = unresolved = 0
    rows, missing = [], []
    srcs = collections.Counter()
    for rec in spells:
        sym, src = rs.resolve_with_source(rec["name"], rec["symbol"],
                                          by_name, by_norm, by_instr)
        if sym is None:
            unresolved += 1
            missing.append([rec["name"], rec["from"], rec["to"] or ""])
            continue
        if sym.startswith("DUMMY"):
            continue          # zero-price demerger placeholder, not tradeable
        resolved += 1
        srcs[src] += 1
        rows.append([sym, rec["from"], rec["to"] or "",
                     f'{rec["name"]} [{src}]'])

    rows.sort(key=lambda r: (r[0], r[1]))
    with open(OUT_MEMBERSHIP, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "effective_from", "effective_to", "note"])
        w.writerows(rows)

    missing.sort()
    with open(OUT_UNRESOLVED, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["company_name", "effective_from", "effective_to"])
        w.writerows(missing)

    print(f"events            : {len(events)}")
    print(f"membership spells : {len(spells)}")
    print(f"  symbol resolved : {resolved}")
    print(f"  unresolved      : {unresolved}")
    for k, v in srcs.most_common():
        print(f"      {k:16s} {v}")


if __name__ == "__main__":
    main()
