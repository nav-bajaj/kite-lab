"""Parse every candidate press release for each index we reconstruct."""
from __future__ import annotations

import glob, json, os, sys
sys.path.insert(0, "lib")
from parse_press_release import parse_changes

INDICES = {
    "nse500": "Nifty 500",
    "nifty50": "Nifty 50",
    "nifty100": "Nifty 100",
    "nifty250": "Nifty LargeMidcap 250",
}


def main() -> None:
    cands = {i["url"].rsplit("/", 1)[-1].replace(".pdf", ""): i
             for i in json.load(open("data/pr_candidates.json"))}
    texts = {os.path.basename(f)[:-4]:
             open(f, encoding="utf-8", errors="replace").read()
             for f in sorted(glob.glob("data/pr_text/*.txt"))}

    for slug, index_name in INDICES.items():
        rows = []
        for base, txt in texts.items():
            r = parse_changes(txt, index_name)
            if not r["excluded"] and not r["included"]:
                continue
            m = cands.get(base, {})
            rows.append({"file": base, "pub": m.get("date"),
                         "title": m.get("title", ""), "eff": str(r["effective"]),
                         "nx": len(r["excluded"]), "ni": len(r["included"]),
                         "excluded": r["excluded"], "included": r["included"]})
        rows.sort(key=lambda r: (r["eff"], r["pub"] or ""))
        json.dump(rows, open(f"data/pr_{slug}_changes.json", "w"), indent=1)
        bad = [r for r in rows if r["nx"] != r["ni"]]
        print(f"{index_name:24s} releases={len(rows):3d}  "
              f"out={sum(r['nx'] for r in rows):4d} in={sum(r['ni'] for r in rows):4d}  "
              f"imbalanced={len(bad)}")
        for r in bad:
            print(f"      IMBALANCE {r['eff']} {r['file']} out={r['nx']} in={r['ni']}")


if __name__ == "__main__":
    main()
