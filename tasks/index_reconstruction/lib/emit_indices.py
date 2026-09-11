"""Emit membership files for the indices reconstructed backwards.

Same schema and the same production loader as the Nifty 500 file. Symbols
resolve through the shared resolver; companies that were merged away and have
no tradeable successor (HDFC into HDFC Bank, MindTree into LTIMindtree,
ICICI Securities delisted) are written to an unresolved list instead of being
guessed at.
"""
from __future__ import annotations

import csv, datetime, collections, sys
sys.path.insert(0, "lib")
import build_index as bi
import resolve_symbols as rs

FILES = {"nifty50": "ind_nifty50list",
         "nifty100": "ind_nifty100list",
         "nifty250": "ind_niftylargemidcap250list"}


def spells(slug: str):
    """(name, from, to, symbol) windows, from the derived seed forward."""
    cur = {bi.canonicalise(r["Company Name"].strip())
           for r in csv.DictReader(
               open(f"data/raw/{FILES[slug]}_2026-09-08.csv", encoding="utf-8-sig"))}
    events = bi.events_for(slug)
    seed, back = bi.derive_seed(slug, cur, events)
    seed_date = min(e["date"] for e in events) - datetime.timedelta(days=1)

    fwd, _ = bi._rename_maps()
    by_date = collections.OrderedDict()
    for e in events:
        by_date.setdefault(e["date"], []).append(e)

    open_spell = {n: {"name": n, "from": seed_date, "symbol": None} for n in seed}
    out = []
    for d, evs in by_date.items():
        for e in evs:
            n = e["name"]
            if e["kind"] == "in":
                open_spell[n] = {"name": n, "from": d, "symbol": e["symbol"]}
            else:
                if n not in open_spell and fwd.get(n) in open_spell:
                    n = fwd[n]
                rec = open_spell.pop(n, None)
                if rec is None:
                    continue
                if e["symbol"]:
                    rec["symbol"] = e["symbol"]
                rec["to"] = d
                out.append(rec)
    for rec in open_spell.values():
        rec["to"] = None
        out.append(rec)
    return out, seed, back, seed_date


def main() -> None:
    by_name, by_norm = rs.current_maps()
    by_instr = rs.instrument_map()
    for slug, (name, size) in bi.SPECS.items():
        sp, seed, back, seed_date = spells(slug)
        rows, missing = [], []
        for rec in sp:
            sym, src = rs.resolve_with_source(rec["name"], rec["symbol"],
                                              by_name, by_norm, by_instr)
            if sym is None:
                missing.append([rec["name"], rec["from"], rec["to"] or ""])
                continue
            if sym.startswith("DUMMY"):
                continue
            rows.append([sym, rec["from"], rec["to"] or "",
                         f'{rec["name"]} [{src}]'])
        rows.sort(key=lambda r: (r[0], str(r[1])))
        with open(f"data/{slug}_membership_reconstructed.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["symbol", "effective_from", "effective_to", "note"])
            w.writerows(rows)
        with open(f"data/{slug}_unresolved.csv", "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["company_name", "effective_from", "effective_to"])
            w.writerows(sorted(missing))
        print(f"{name:22s} seed {seed_date} ({len(seed)}/{size}, back-probs {len(back)})"
              f"  spells={len(sp)} resolved={len(rows)} unresolved={len(missing)}")


if __name__ == "__main__":
    main()
