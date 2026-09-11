"""Download NSE corporate-action filings, equities, by quarter.

  GET https://www.nseindia.com/api/corporates-corporateActions
      ?index=equities&from_date=DD-MM-YYYY&to_date=DD-MM-YYYY

The API wants a cookie minted by the corporate-filings landing page; the
session re-primes when a response stops being JSON. A full year returned
2,208 rows for 2020 without complaint, but quarters are used anyway so any
silent cap cannot truncate a year unnoticed. Raw JSON is stored per quarter;
build_symbol_master.py and build_corporate_actions.py parse it.
"""
from __future__ import annotations

import argparse, json, os, time
from datetime import date

import requests

from data_pipeline.master_store import MASTER  # noqa: E402
OUT = f"{MASTER}/raw/nse_ca"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
LANDING = "https://www.nseindia.com/companies-listing/corporate-filings-actions"
API = "https://www.nseindia.com/api/corporates-corporateActions"


def prime(s: requests.Session) -> None:
    s.get(LANDING, timeout=30)
    time.sleep(1.0)


def quarters(y0: int, y1: int):
    today = date.today()
    for y in range(y0, y1 + 1):
        for q, (m0, m1, dlast) in enumerate([(1, 3, 31), (4, 6, 30), (7, 9, 30), (10, 12, 31)], 1):
            a = date(y, m0, 1)
            if a > today:
                return
            b = min(date(y, m1, dlast), today)
            yield y, q, a, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-year", type=int, default=2000)
    ap.add_argument("--end-year", type=int, default=date.today().year)
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*",
                      "Accept-Language": "en-US,en;q=0.9", "Referer": LANDING})
    prime(s)
    total = 0
    for y, q, d0, d1 in quarters(a.start_year, a.end_year):
        path = os.path.join(a.out, f"{y}Q{q}.json")
        if os.path.exists(path) and d1 != date.today():
            continue
        rows = None
        for attempt in range(5):
            try:
                r = s.get(API, params={"index": "equities", "from_date": d0.strftime("%d-%m-%Y"),
                                       "to_date": d1.strftime("%d-%m-%Y")}, timeout=60)
                rows = r.json()
                if isinstance(rows, list):
                    break
            except Exception:
                rows = None
            time.sleep(3 * (attempt + 1)); prime(s)
        if not isinstance(rows, list):
            print(f"{y}Q{q}: FAILED", flush=True); continue
        json.dump(rows, open(path, "w"))
        total += len(rows)
        print(f"{y}Q{q}: {len(rows)} rows", flush=True)
        time.sleep(1.5)
    print(f"done: {total} rows", flush=True)


if __name__ == "__main__":
    main()
