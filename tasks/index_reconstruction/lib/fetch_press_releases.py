"""Download the candidate press-release PDFs from niftyindices.com.

Polite: sequential with a short delay, skips anything already on disk, and
retries twice. The PDFs are large and reproducible from this script, so they
are gitignored; the extracted text is what gets committed.
"""
import json, time, sys, urllib.request
from pathlib import Path
from urllib.parse import urlparse

OUT = Path("data/press_releases")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
HOST = "www.niftyindices.com"


def _checked(url: str) -> str:
    """Reject anything that is not an https URL on the NSE indices host.

    The URLs come out of a scraped page, so they are untrusted input; without
    this a "file:" or off-host entry would be fetched blindly.
    """
    p = urlparse(url)
    if p.scheme != "https" or p.netloc != HOST:
        raise ValueError(f"refusing to fetch {url!r}")
    return url


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    items = json.load(open("data/pr_candidates.json"))
    ok = skip = fail = 0
    for i, it in enumerate(items, 1):
        name = it["url"].rsplit("/", 1)[-1]
        dest = OUT / name
        if dest.exists() and dest.stat().st_size > 5000:
            skip += 1
            continue
        for attempt in range(3):
            try:
                url = _checked(it["url"])
                req = urllib.request.Request(url, headers={"User-Agent": UA})  # noqa: S310 - _checked pins scheme+host
                data = urllib.request.urlopen(req, timeout=45).read()  # noqa: S310 - scheme and host checked above
                if len(data) < 5000:
                    raise ValueError(f"short body {len(data)}")
                dest.write_bytes(data)
                ok += 1
                break
            except Exception as e:
                if attempt == 2:
                    fail += 1
                    print(f"FAIL {name}: {e}", file=sys.stderr)
                else:
                    time.sleep(2)
        time.sleep(0.4)
        if i % 25 == 0:
            print(f"  ...{i}/{len(items)}", flush=True)
    print(f"downloaded={ok} skipped={skip} failed={fail}")


if __name__ == "__main__":
    main()
