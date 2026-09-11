"""Did a fetch rewrite history, or only append to it?

Compares each panel file against manifest_pre_flip.csv. New rows after the
manifest's last_date are expected and ignored. Any change to a row at or
before that date means the provider rewrote history and our fetch accepted it.
"""

import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).resolve().parent / "manifest_pre_flip.csv"
COLS = ("date", "open", "high", "low", "close")


def hash_through(path, cutoff):
    """Hash only rows dated <= cutoff, so appended rows don't affect it."""
    h = hashlib.sha256()
    n = 0
    with path.open() as f:
        r = csv.reader(f)
        hdr = next(r, None)
        if not hdr or "date" not in hdr:
            return None, 0
        idx = {c: i for i, c in enumerate(hdr)}
        cols = [idx[c] for c in COLS if c in idx]
        for row in r:
            if not row:
                continue
            if row[idx["date"]][:10] <= cutoff:
                h.update("|".join(row[i] for i in cols).encode())
                n += 1
    return h.hexdigest(), n


def main():
    rows = list(csv.DictReader(MANIFEST.open()))
    moved, appended, missing, clean = [], 0, [], 0

    for m in rows:
        path = ROOT / m["panel"] / m["file"]
        if not path.exists():
            missing.append(f"{m['panel']}/{m['file']}")
            continue
        cutoff = m["last_date"][:10]
        got, n = hash_through(path, cutoff)
        if got is None:
            continue
        if got == m["sha256"]:
            clean += 1
            if n < int(m["rows"]):
                appended += 1
        else:
            moved.append({
                "file": f"{m['panel']}/{m['file']}",
                "cutoff": cutoff,
                "rows_then": int(m["rows"]),
                "rows_now_through_cutoff": n,
            })

    print(f"checked {len(rows)} files")
    print(f"  history intact : {clean}")
    print(f"  history MOVED  : {len(moved)}")
    print(f"  missing        : {len(missing)}")

    if moved:
        print("\nFiles whose pre-existing history changed:")
        for x in moved[:40]:
            delta = x["rows_now_through_cutoff"] - x["rows_then"]
            note = f" (row count {delta:+d})" if delta else " (same row count — VALUES changed)"
            print(f"  {x['file']:<45} through {x['cutoff']}{note}")
        if len(moved) > 40:
            print(f"  ... and {len(moved)-40} more")
    if missing:
        print("\nMissing:", ", ".join(missing[:10]))

    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main())
