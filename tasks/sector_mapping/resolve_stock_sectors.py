"""Resolve each tracked stock's canonical Zerodha sector.

Authoritative source: each stock's own Zerodha page,
    https://zerodha.com/markets/stocks/NSE/<SYMBOL>/
whose breadcrumb links to exactly one /markets/sector/<slug>/. This is more
complete and less ambiguous than the sector-list pages (scrape_zerodha_sectors.py):
it recovers stocks the list pages omit (LTIM, GSPL) and gives Zerodha's single
canonical sector where the list pages show a stock under both a broad and a
niche sector (ASTRAL -> engineering-capital-goods, not plastic-pipes).

Reads the union of tracked Indian symbols from the four universe CSVs
(read-only) and writes, inside this task folder only:
    tasks/sector_mapping/data/tracked_sectors.csv
        symbol, company, nse_industry, zerodha_sector, zerodha_sector_slug,
        in_universes, source_exchange, matched
    tasks/sector_mapping/data/unmatched.csv   (symbols with no Zerodha sector)

Nothing under data/static/ or any production path is modified.

Usage:
    python tasks/sector_mapping/resolve_stock_sectors.py
    python tasks/sector_mapping/resolve_stock_sectors.py --symbols LTIM ASTRAL
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
STOCK_URL = "https://zerodha.com/markets/stocks/{exch}/{sym}/"
SECTOR_RE = re.compile(r"/markets/sector/([a-z-]+)/")

UNIVERSES = {
    "nse500": REPO / "data/static/nse500_universe.csv",
    "nifty250": REPO / "data/static/nifty250_universe.csv",
    "nifty100": REPO / "data/static/nifty100_universe.csv",
    "nifty_smallcap": REPO / "data/static/nifty_smallcap_universe.csv",
}


_ACRONYMS = {"it": "IT", "fmcg": "FMCG", "nbfc": "NBFC"}


def slug_to_name(slug: str) -> str:
    if slug in _ACRONYMS:
        return _ACRONYMS[slug]
    return slug.replace("-", " ").title()


def load_universes():
    meta: dict[str, dict] = {}
    membership: dict[str, list[str]] = defaultdict(list)
    for name, path in UNIVERSES.items():
        for r in csv.DictReader(path.open()):
            sym = r["Symbol"]
            membership[sym].append(name)
            meta.setdefault(sym, {"company": r["Company Name"],
                                  "nse_industry": r["Industry"]})
    return meta, membership


def fetch_sector(sym: str, retries: int = 3) -> tuple[str, str]:
    """Return (sector_slug, source_exchange) or ("", "") if uncategorized."""
    for exch in ("NSE", "BSE"):
        url = STOCK_URL.format(exch=exch, sym=sym)
        for attempt in range(retries):
            try:
                req = Request(url, headers={"User-Agent": UA})  # noqa: S310 (fixed https zerodha URL)
                with urlopen(req, timeout=30) as resp:  # noqa: S310
                    html = resp.read().decode("utf-8", errors="replace")
                m = SECTOR_RE.search(html)  # breadcrumb precedes footer nav
                if m:
                    return m.group(1), exch
                break  # page exists but has no sector; try other exchange
            except HTTPError as exc:
                if exc.code == 404:
                    break  # not on this exchange; try the other
            except URLError:
                pass
    return "", ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", help="subset (default: all tracked)")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    meta, membership = load_universes()
    symbols = args.symbols or sorted(meta)
    DATA.mkdir(parents=True, exist_ok=True)

    results: dict[str, tuple[str, str]] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for sym, res in zip(symbols, pool.map(fetch_sector, symbols)):
            results[sym] = res

    out_rows, unmatched = [], []
    for sym in symbols:
        slug, exch = results[sym]
        m = meta.get(sym, {"company": "", "nse_industry": ""})
        row = {
            "symbol": sym,
            "company": m["company"],
            "nse_industry": m["nse_industry"],
            "zerodha_sector": slug_to_name(slug) if slug else "",
            "zerodha_sector_slug": slug,
            "in_universes": " ".join(membership.get(sym, [])),
            "source_exchange": exch,
            "matched": "yes" if slug else "no",
        }
        out_rows.append(row)
        if not slug:
            unmatched.append(row)

    fields = ["symbol", "company", "nse_industry", "zerodha_sector",
              "zerodha_sector_slug", "in_universes", "source_exchange", "matched"]
    for path, rows in [(DATA / "tracked_sectors.csv", out_rows),
                       (DATA / "unmatched.csv", unmatched)]:
        with path.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)

    n = len(out_rows)
    matched = n - len(unmatched)
    print(f"tracked Indian symbols: {n}")
    print(f"resolved to a Zerodha sector: {matched} ({matched / n:.1%})")
    print(f"uncategorized on Zerodha: {len(unmatched)}")
    for r in unmatched:
        print(f"  {r['symbol']:14s} {r['company'][:38]:38s} [{r['nse_industry']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
