import os, datetime as dt, math
import pandas as pd
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from utils import find_token
import matplotlib.pyplot as plt

load_dotenv()
API_KEY = os.getenv("API_KEY")
with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

def fetch_history(symbol, start, end, interval="day", exchange="NSE", oi=False):
    """
    Batches requests by date window (safe defaults) to avoid server limits.
    Adjust chunk_days for intraday intervals if you see truncation.
    """
    token = find_token(symbol, exchange=exchange)
    start = pd.Timestamp(start)
    end   = pd.Timestamp(end)

    # Conservative chunking (minute data often requires small windows).
    chunk_days = 30 if interval != "day" else 3650
    frames = []
    cur = start
    while cur < end:
        chunk_end = min(cur + pd.Timedelta(days=chunk_days), end)
        candles = kite.historical_data(
            instrument_token=token,
            from_date=cur.to_pydatetime(),
            to_date=chunk_end.to_pydatetime(),
            interval=interval,
            continuous=False,
            oi=oi
        )
        if candles:
            frames.append(pd.DataFrame(candles))
        cur = chunk_end
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    # Normalize timestamp to pandas datetime
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates(subset=["date"])
    return df

if __name__ == "__main__":
    symbol = "INFY"  # try any NSE symbol you hold
    start = "2020-01-01"
    end   = dt.date.today().isoformat()

    # Daily data for multi-year analysis
    ddf = fetch_history(symbol, start, end, "day")
    os.makedirs("data", exist_ok=True)
    ddf.to_csv(f"data/{symbol}_day.csv", index=False)
    print("Saved daily candles:", len(ddf))

    # Quick, meaningful analysis
    ddf["ret"] = ddf["close"].pct_change()
    ddf["cumret"] = (1 + ddf["ret"]).cumprod()
    ddf["ma50"] = ddf["close"].rolling(50).mean()
    ddf["ma200"] = ddf["close"].rolling(200).mean()

    # Minimal plots
    plt.figure()
    plt.title(f"{symbol} close vs MA(50/200)")
    plt.plot(ddf["date"], ddf["close"], label="Close")
    plt.plot(ddf["date"], ddf["ma50"], label="MA50")
    plt.plot(ddf["date"], ddf["ma200"], label="MA200")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"data/{symbol}_ma.png", dpi=160)

    plt.figure()
    plt.title(f"{symbol} cumulative returns (normalized)")
    plt.plot(ddf["date"], ddf["cumret"])
    plt.tight_layout()
    plt.savefig(f"data/{symbol}_cumret.png", dpi=160)

    print("Charts saved in data/")
