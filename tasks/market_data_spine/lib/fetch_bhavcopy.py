"""Download every NSE cash-market bhavcopy from NSE's own archive.

Two formats over the span:
  legacy  https://nsearchives.nseindia.com/content/historical/EQUITIES/<YYYY>/<MON>/cm<DD><MON><YYYY>bhav.csv.zip
  UDiFF   https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_<YYYYMMDD>_F_0000.csv.zip

UDiFF began in 2024 and the legacy file was withdrawn later that year, so
2024 dates try both. A 404 on every candidate is a holiday and is recorded so
the run is resumable without re-asking. Files are stored as fetched (zip);
parsing happens in build_symbol_master.py.

Polite by design: one request at a time, a fixed pause between them, and
exponential backoff on 403/429/5xx. NSE has not throttled at this rate.
"""
from __future__ import annotations

import argparse, os, sys, time
from datetime import date, timedelta

import requests

OUT = "/Users/navdeep/kite-lab/data/master/raw/bhavcopy"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
PAUSE = 0.35
UDIFF_FROM = date(2024, 1, 1)
LEGACY_UNTIL = date(2024, 12, 31)


def candidates(d: date) -> list[tuple[str, str]]:
    urls = []
    if d >= UDIFF_FROM:
        urls.append(("udiff", "https://nsearchives.nseindia.com/content/cm/"
                     f"BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"))
    if d <= LEGACY_UNTIL:
        mon = d.strftime("%b").upper()
        urls.append(("legacy", "https://nsearchives.nseindia.com/content/historical/EQUITIES/"
                     f"{d.year}/{mon}/cm{d:%d}{mon}{d.year}bhav.csv.zip"))
    return urls


def get(session: requests.Session, url: str) -> tuple[int, bytes]:
    wait = 2.0
    for attempt in range(6):
        try:
            r = session.get(url, timeout=30)
        except requests.RequestException as e:
            status, body = -1, str(e).encode()
        else:
            status, body = r.status_code, r.content
        if status == 200 or status == 404:
            return status, body
        time.sleep(wait)
        wait = min(wait * 2, 60)
    return status, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2005-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    holidays_path = os.path.join(a.out, "holidays.txt")
    errors_path = os.path.join(a.out, "errors.txt")
    holidays = set(open(holidays_path).read().split()) if os.path.exists(holidays_path) else set()

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"})

    d, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    n_days = n_got = n_hol = n_err = n_skip = 0
    t0 = time.time()
    while d <= end:
        if d.weekday() >= 5:
            d += timedelta(days=1); continue
        n_days += 1
        ymd = d.isoformat()
        ydir = os.path.join(a.out, str(d.year)); os.makedirs(ydir, exist_ok=True)
        have = [f for f in os.listdir(ydir) if f.startswith(ymd)]
        if have or ymd in holidays:
            n_skip += 1; d += timedelta(days=1); continue

        got = False
        last_status = None
        for fmt, url in candidates(d):
            status, body = get(s, url)
            time.sleep(PAUSE)
            last_status = status
            if status == 200 and body[:2] == b"PK":
                with open(os.path.join(ydir, f"{ymd}_{fmt}.zip"), "wb") as f:
                    f.write(body)
                got = True; n_got += 1
                break
        if not got:
            if last_status == 404:
                holidays.add(ymd); n_hol += 1
                with open(holidays_path, "a") as f: f.write(ymd + "\n")
            else:
                n_err += 1
                with open(errors_path, "a") as f: f.write(f"{ymd} {last_status}\n")
        if n_days % 100 == 0:
            el = time.time() - t0
            print(f"[{ymd}] fetched {n_got} holidays {n_hol} errors {n_err} skipped {n_skip} "
                  f"({el/60:.1f} min)", flush=True)
        d += timedelta(days=1)
    print(f"done: fetched {n_got} holidays {n_hol} errors {n_err} skipped {n_skip}", flush=True)


if __name__ == "__main__":
    main()
