"""GDF raw daily history for every company Kite cannot serve — the second
opinion on the bhavcopy series (D-1 revised, D-11). Single-session key, so
symbols are fetched sequentially over one connection. Written as served to
data/master/prices/gdf/<SYMBOL>.csv with a manifest; nothing reads these as
a basis.
"""
from __future__ import annotations

import asyncio, hashlib, json, os, sys
import pandas as pd

from data_pipeline.master_store import ROOT as REPO, MASTER  # noqa: E402
sys.path.insert(0, REPO)
from data_pipeline.gdf_client import GDFClient  # noqa: E402

MASTER = MASTER
OUT = f"{MASTER}/prices/gdf"
MANIFEST = f"{MASTER}/prices/gdf_manifest.json"


async def main():
    os.makedirs(OUT, exist_ok=True)
    t = pd.read_csv(f"{MASTER}/kite_targets.csv")
    syms = sorted({s for s in t[t["exchange"] == "NONE"]["symbol"] for s in s.split("|")})
    bman = json.load(open(f"{MASTER}/prices/bhavcopy_manifest.json"))
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    ok = empty = 0
    async with GDFClient() as c:
        for i, s in enumerate(syms, 1):
            if s in manifest:
                continue
            # ask under every ticker the company traded as; GDF files history by ticker
            tickers = bman.get(s, {}).get("traded_as", [s])
            frames = []
            for tk in tickers:
                try:
                    df = await c.get_history(tk, "2009-01-01", "2026-09-10")
                except Exception as e:  # noqa: BLE001
                    manifest[f"{s}:{tk}"] = {"error": str(e)[:160]}; continue
                if len(df):
                    frames.append(df.assign(traded_as=tk))
            if not frames:
                empty += 1; manifest[s] = {"rows": 0}; continue
            df = pd.concat(frames).sort_values("date").drop_duplicates("date", keep="last")
            df["date"] = pd.to_datetime(df["date"]).dt.normalize()
            df.to_csv(f"{OUT}/{s}.csv", index=False)
            manifest[s] = {"first": str(df["date"].min().date()), "last": str(df["date"].max().date()), "rows": int(len(df)),
                           "traded_as": tickers, "basis": "gdf-raw",
                           "sha256": hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()}
            ok += 1
            if i % 25 == 0:
                json.dump(manifest, open(MANIFEST, "w"), indent=1); print(f"  {i}/{len(syms)} ok {ok} empty {empty}", flush=True)
    json.dump(manifest, open(MANIFEST, "w"), indent=1)
    print(f"done: {ok} series, {empty} empty, of {len(syms)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
