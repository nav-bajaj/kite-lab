"""Dump raw GDF responses for a single GetHistory call (full untruncated)."""
from __future__ import annotations
import asyncio, json, os, sys
from pathlib import Path
import websockets
from dotenv import load_dotenv
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
URL = os.environ.get("GDF_WSS_URL", "wss://nimblewebstream.lisuns.com:4576/")
KEY = os.environ["GDF_API_KEY"]


async def main():
    sym = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    end = pd.Timestamp.today().normalize()
    start = end - pd.Timedelta(days=days)

    async with websockets.connect(URL, ping_interval=20, ping_timeout=20) as ws:
        await ws.send(json.dumps({"MessageType": "Authenticate", "Password": KEY}))
        print("AUTH:", await asyncio.wait_for(ws.recv(), timeout=15))

        req = {
            "MessageType": "GetHistory", "Exchange": "NSE",
            "InstrumentIdentifier": sym, "Periodicity": "DAY", "Period": 1,
            "Max": 0, "From": int(start.timestamp()), "To": int(end.timestamp()),
            "isShortIdentifier": "False", "UserTag": "raw",
        }
        await ws.send(json.dumps(req))

        # Read until we see a message with "Result" key, ignoring Echo/Allow*
        n = 0
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=15)
            msg = json.loads(raw)
            mtype = msg.get("MessageType", "")
            n += 1
            if mtype in ("Echo", "AllowVMRunningResult", "AllowServerOSRunningResult"):
                continue
            if mtype == "RequestError":
                print(f"#{n} ERROR:", msg)
                break
            if "Result" in msg:
                results = msg["Result"]
                print(f"#{n} GOT Result: {len(results)} bars")
                if results:
                    print("first:", json.dumps(results[0]))
                    print("last :", json.dumps(results[-1]))
                    print(f"first date: {pd.Timestamp(results[0]['LastTradeTime'], unit='s')}")
                    print(f"last date : {pd.Timestamp(results[-1]['LastTradeTime'], unit='s')}")
                break
            print(f"#{n} OTHER:", raw[:200])
            if n > 30:
                print("[bail]")
                break


asyncio.run(main())
