"""Scrape Zerodha's sector taxonomy for every listed NSE/BSE stock.

Source: https://zerodha.com/markets/sector/  (35 sector detail pages, each a
fully server-rendered HTML table — no JS/pagination). Each row gives the
exchange, symbol, company name, market cap and PE.

Output: tasks/sector_mapping/data/zerodha_sectors_raw.csv
    columns: zerodha_sector, sector_slug, exchange, symbol, company, market_cap_cr, pe

This is a research probe (lives under tasks/, not scripts/). It only writes
inside this task folder — it does not touch data/static/ or any production
path. The join onto our tracked universes happens in build_sector_map.py.

Usage:
    python tasks/sector_mapping/scrape_zerodha_sectors.py
    python tasks/sector_mapping/scrape_zerodha_sectors.py --sectors it nbfc  # subset
"""
from __future__ import annotations

import argparse
import csv
import html as htmllib
import re
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://zerodha.com/markets/sector"
OUT_DIR = Path(__file__).resolve().parent / "data"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# The 35 sector slugs from the /markets/sector/ index (as of 2026-07).
SECTOR_SLUGS = [
    "agriculture", "auto-ancillary", "automobile", "aviation",
    "building-materials", "chemicals", "consumer-durables", "dairy-products",
    "defence", "diversified", "education-training", "energy",
    "engineering-capital-goods", "fmcg", "fertilizers", "financial-services",
    "healthcare", "it", "logistics", "media-entertainment", "metals",
    "miscellaneous", "nbfc", "packaging", "plastic-pipes", "real-estate",
    "retail", "services", "silver", "software-services", "solar-panel",
    "telecom", "textiles", "tourism-hospitality", "trading",
]

# Each stock is an <a href="/markets/stocks/<EXCH>/<SYMBOL>/"> wrapping a
# .table_row whose first inner <div> text is the company name, followed by
# .market_cap and .pe cells.
ROW_RE = re.compile(
    r'<a href="/markets/stocks/(?P<exch>NSE|BSE)/(?P<symbol>[A-Z0-9&._-]+)/">'
    r'.*?<div class="left">\s*<div>\s*(?P<company>.*?)\s*</div>'
    r'.*?<div class="market_cap">\s*(?P<mcap>.*?)\s*</div>'
    r'.*?<div class="pe">\s*(?P<pe>.*?)\s*</div>',
    re.S,
)


_ACRONYMS = {"it": "IT", "fmcg": "FMCG", "nbfc": "NBFC"}


def slug_to_name(slug: str) -> str:
    if slug in _ACRONYMS:
        return _ACRONYMS[slug]
    return slug.replace("-", " ").title()


def fetch(url: str, retries: int = 3) -> str:
    last = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": UA})  # noqa: S310 (fixed https zerodha URL)
            with urlopen(req, timeout=30) as resp:  # noqa: S310
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 - best-effort scraper
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to fetch {url}: {last}")


def clean(text: str) -> str:
    # Strip any stray tags and collapse whitespace inside a captured cell.
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_sector(html: str, slug: str) -> list[dict]:
    name = slug_to_name(slug)
    # Hrefs and names carry HTML entities (e.g. NSE/M&amp;M/, "Mahindra &amp;
    # Mahindra"). Decode before the row regex so &-tickers are not dropped.
    html = htmllib.unescape(html)
    rows = []
    for m in ROW_RE.finditer(html):
        rows.append(
            {
                "zerodha_sector": name,
                "sector_slug": slug,
                "exchange": m.group("exch"),
                "symbol": m.group("symbol"),
                "company": clean(m.group("company")),
                "market_cap_cr": clean(m.group("mcap")),
                "pe": clean(m.group("pe")),
            }
        )
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sectors", nargs="*", help="subset of slugs (default: all)")
    ap.add_argument("--sleep", type=float, default=0.8, help="polite delay between pages")
    args = ap.parse_args()

    slugs = args.sectors or SECTOR_SLUGS
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "zerodha_sectors_raw.csv"

    all_rows: list[dict] = []
    for i, slug in enumerate(slugs, 1):
        url = f"{BASE}/{slug}/"
        try:
            html = fetch(url)
        except RuntimeError as exc:
            print(f"[{i}/{len(slugs)}] {slug}: FAILED — {exc}", file=sys.stderr)
            continue
        rows = parse_sector(html, slug)
        all_rows.extend(rows)
        print(f"[{i}/{len(slugs)}] {slug}: {len(rows)} stocks")
        time.sleep(args.sleep)

    fields = ["zerodha_sector", "sector_slug", "exchange", "symbol",
              "company", "market_cap_cr", "pe"]
    with out_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(all_rows)

    n_nse = sum(1 for r in all_rows if r["exchange"] == "NSE")
    print(f"\nWrote {len(all_rows)} rows ({n_nse} NSE) across {len(slugs)} "
          f"sectors -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
