"""Resolve each tracked stock's canonical Zerodha sector.

Companion to `fetch_sector_constituents.py`. That script snapshots the 12 NSE
thematic sector *indices* (NIFTY_BANK, NIFTY_IT, ...) for sector RS / breadth.
This one produces a *per-stock* sector label for every tracked symbol using
Zerodha's finer 35-sector taxonomy (https://zerodha.com/markets/sector/), which
NSE's macro `Industry` column does not distinguish (e.g. Software Services vs
IT vs Services all collapse to "Information Technology" in NSE's scheme).

Source of truth: each stock's own Zerodha page
    https://zerodha.com/markets/stocks/{NSE|BSE}/<SYMBOL>/
whose breadcrumb links to exactly one /markets/sector/<slug>/. This is more
complete and less ambiguous than the sector-list pages (it files ASTRAL under
Engineering Capital Goods rather than the niche Plastic Pipes).

Renamed tickers: our universe keeps the canonical (old) symbol while NSE moved
the listing (LTIM->LTM, AKZOINDIA->JSWDULUX). We reuse the same alias map the
fetch layer uses (scripts/history_utils.SYMBOL_ALIASES) so the Zerodha lookup
follows the successor ticker but the output keys stay on our canonical symbol.

Output (a NEW file — the universe CSVs are left untouched):
    data/static/zerodha_sectors.csv
        symbol, company, zerodha_sector, zerodha_sector_slug, source_exchange

Behaviour:
  - Best-effort per symbol; DUMMY* placeholder scrips are skipped.
  - Idempotent: overwrites the output CSV.
  - Exits non-zero if resolved coverage falls below --min-coverage (default 0.97).

Usage:
    python scripts/fetch_zerodha_sectors.py
    python scripts/fetch_zerodha_sectors.py --symbols LTIM ASTRAL --dry-run
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from history_utils import SYMBOL_ALIASES  # noqa: E402  (sibling script module)

REPO_ROOT = SCRIPT_DIR.parent
STATIC_DIR = REPO_ROOT / "data" / "static"
OUT_PATH = STATIC_DIR / "zerodha_sectors.csv"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
STOCK_URL = "https://zerodha.com/markets/stocks/{exch}/{sym}/"
SECTOR_RE = re.compile(r"/markets/sector/([a-z-]+)/")

UNIVERSE_FILES = [
    "nse500_universe.csv",
    "nifty250_universe.csv",
    "nifty100_universe.csv",
    "nifty_smallcap_universe.csv",
]

_ACRONYMS = {"it": "IT", "fmcg": "FMCG", "nbfc": "NBFC"}


def slug_to_name(slug: str) -> str:
    return _ACRONYMS.get(slug, slug.replace("-", " ").title())


def load_tracked() -> dict[str, str]:
    """Return {canonical_symbol: company_name} across the tracked universes,
    excluding DUMMY* placeholder scrips (no real listing / sector)."""
    meta: dict[str, str] = {}
    for fname in UNIVERSE_FILES:
        with (STATIC_DIR / fname).open() as fh:
            for r in csv.DictReader(fh):
                sym = r["Symbol"].strip()
                if sym.upper().startswith("DUMMY"):
                    continue
                meta.setdefault(sym, r["Company Name"].strip())
    return meta


def fetch_sector(symbol: str, retries: int = 3) -> tuple[str, str]:
    """Return (sector_slug, source_exchange) for our canonical `symbol`, or
    ("", "") if Zerodha has no sector for it. Follows SYMBOL_ALIASES to the
    successor ticker for renamed listings."""
    lookup = SYMBOL_ALIASES.get(symbol, symbol)
    for exch in ("NSE", "BSE"):
        url = STOCK_URL.format(exch=exch, sym=lookup)
        for _ in range(retries):
            try:
                # S310: URL is a hardcoded https://zerodha.com/... path built
                # from trusted universe symbols; no user input, no file: scheme.
                req = Request(url, headers={"User-Agent": UA})  # noqa: S310
                with urlopen(req, timeout=30) as resp:  # noqa: S310
                    html = resp.read().decode("utf-8", errors="replace")
                m = SECTOR_RE.search(html)  # breadcrumb precedes footer nav
                if m:
                    return m.group(1), exch
                break  # page exists but carries no sector; try other exchange
            except HTTPError as exc:
                if exc.code == 404:
                    break
            except URLError:
                pass
    return "", ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--symbols", nargs="*", help="subset (default: all tracked)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--min-coverage", type=float, default=0.97)
    ap.add_argument("--dry-run", action="store_true",
                    help="resolve and report, but do not write the CSV")
    args = ap.parse_args()

    meta = load_tracked()
    symbols = args.symbols or sorted(meta)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        resolved = dict(zip(symbols, pool.map(fetch_sector, symbols)))

    rows, unmatched = [], []
    for sym in symbols:
        slug, exch = resolved[sym]
        rows.append({
            "symbol": sym,
            "company": meta.get(sym, ""),
            "zerodha_sector": slug_to_name(slug) if slug else "",
            "zerodha_sector_slug": slug,
            "source_exchange": exch,
        })
        if not slug:
            unmatched.append(sym)

    n = len(rows)
    matched = n - len(unmatched)
    coverage = matched / n if n else 0.0
    print(f"tracked symbols: {n}")
    print(f"resolved: {matched} ({coverage:.1%})")
    if unmatched:
        print(f"unresolved ({len(unmatched)}): {', '.join(unmatched)}")

    if args.dry_run:
        print("[dry-run] not writing output")
    else:
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
        fields = ["symbol", "company", "zerodha_sector",
                  "zerodha_sector_slug", "source_exchange"]
        with OUT_PATH.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {n} rows -> {OUT_PATH.relative_to(REPO_ROOT)}")

    if coverage < args.min_coverage:
        print(f"ERROR: coverage {coverage:.1%} < --min-coverage "
              f"{args.min_coverage:.0%}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
