import pandas as pd, os, sys
from kiteconnect import KiteConnect
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("Missing API_KEY in environment. Populate .env before running this script.")
    sys.exit(1)

access_token_path = "access_token.txt"
if not os.path.exists(access_token_path):
    print("Missing access_token.txt. Run scripts/login_and_save_token.py first.")
    sys.exit(1)

with open(access_token_path) as f:
    ACCESS_TOKEN = f.read().strip()
    if not ACCESS_TOKEN:
        print("access_token.txt is empty. Re-run scripts/login_and_save_token.py to refresh the token.")
        sys.exit(1)

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Big CSV; recommended once/day (morning) per docs
inst = kite.instruments()  # or kite.instruments("NSE")
df = pd.DataFrame(inst)
os.makedirs("data", exist_ok=True)
df.to_csv("data/instruments_full.csv", index=False)
print("Saved data/instruments_full.csv with", len(df), "rows")
