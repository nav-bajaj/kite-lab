import pandas as pd, os, sys
from kiteconnect import KiteConnect
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("API_KEY")
with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Big CSV; recommended once/day (morning) per docs
inst = kite.instruments()  # or kite.instruments("NSE")
df = pd.DataFrame(inst)
os.makedirs("data", exist_ok=True)
df.to_csv("data/instruments_full.csv", index=False)
print("Saved data/instruments_full.csv with", len(df), "rows")
