"""Apply corporate action adjustments to historical price data.

Reads data/corporate_actions.json and adjusts OHLC prices in nse500_data/
for events like demergers, splits, and bonuses. Designed to run after every
price fetch so that re-fetched raw prices are always corrected.

Strategy:
- Uses a price threshold to identify unadjusted (raw) rows. Any pre-ex-date
  row with close > threshold is raw and gets the factor applied.
- On first run (no sidecar), verifies data consistency before bulk adjusting.
  If data is in an unrecoverable mixed state, deletes the CSV so the next
  fetch downloads fresh raw data.
- The sidecar (.corporate_actions_applied.json) lives in the price directory
  (persistent volume on Railway) to survive container redeploys.
"""

import json
import math
import os
import sys

import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
ACTIONS_FILE = os.path.join(ROOT_DIR, "data", "corporate_actions.json")
PRICE_DIR = os.path.join(ROOT_DIR, "nse500_data")
APPLIED_FILE = os.path.join(PRICE_DIR, ".corporate_actions_applied.json")
PRICE_COLS = ["open", "high", "low", "close"]


def load_actions():
    if not os.path.exists(ACTIONS_FILE):
        return []
    with open(ACTIONS_FILE) as f:
        return json.load(f)


def load_applied():
    if not os.path.exists(APPLIED_FILE):
        return {}
    with open(APPLIED_FILE) as f:
        return json.load(f)


def save_applied(applied):
    with open(APPLIED_FILE, "w") as f:
        json.dump(applied, f, indent=2)


def action_key(action):
    return f"{action['symbol']}_{action['action']}_{action['ex_date']}"


def apply_adjustment(action, applied):
    symbol = action["symbol"]
    ex_date = action["ex_date"]
    factor = action["factor"]
    raw_pre_ex_close = action["raw_pre_ex_close"]
    key = action_key(action)

    csv_path = os.path.join(PRICE_DIR, f"{symbol}_day.csv")
    if not os.path.exists(csv_path):
        print(f"  {symbol}: CSV not found, skipping")
        return False

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])

    pre_mask = df["date"] < ex_date
    if not pre_mask.any():
        print(f"  {symbol}: No pre-ex-date data, skipping")
        return False

    # Threshold separates raw prices (above) from adjusted prices (below)
    threshold = raw_pre_ex_close * math.sqrt(factor)
    expected_adjusted = raw_pre_ex_close * factor

    # Check last pre-ex close
    last_pre_ex_close = df.loc[pre_mask, "close"].iloc[-1]
    last_is_adjusted = abs(last_pre_ex_close - expected_adjusted) / expected_adjusted < 0.05
    last_is_raw = abs(last_pre_ex_close - raw_pre_ex_close) / raw_pre_ex_close < 0.05

    previously_applied = key in applied

    if previously_applied:
        # Normal operation: just fix any raw rows from re-fetch
        raw_rows = pre_mask & (df["close"] > threshold)
        if not raw_rows.any():
            print(f"  {symbol}: All prices adjusted, skipping")
            return False
        for col in PRICE_COLS:
            df.loc[raw_rows, col] = (df.loc[raw_rows, col] * factor).round(2)
        df.to_csv(csv_path, index=False)
        print(f"  {symbol}: Re-fetch fix - adjusted {raw_rows.sum()} rows (threshold={threshold:.2f})")
        return True

    # First time processing this action on this volume.
    # Verify data is in a known-good state before proceeding.

    if last_is_adjusted:
        # Check a sample of older data too to confirm consistency
        first_pre_ex_close = df.loc[pre_mask, "close"].iloc[0]
        # If both first and last are in adjusted range (below threshold), mark as done
        if first_pre_ex_close < threshold:
            applied[key] = True
            print(f"  {symbol}: Already adjusted (last={last_pre_ex_close:.2f}), marking as applied")
            return False

    if last_is_raw:
        # Last close is raw. Check if ALL data is raw (true first run)
        # or if it's a mixed state (corrupted volume + re-fetch).
        # A "true first run" means oldest data should also be raw.
        first_pre_ex_close = df.loc[pre_mask, "close"].iloc[0]
        # VEDL's earliest raw price was ~50+ (post-COVID). If first close
        # is unreasonably low (< expected_adjusted * 0.5), data is corrupted.
        if first_pre_ex_close < expected_adjusted * 0.3:
            # Corrupted state: old data has been multiply-adjusted.
            # Delete CSV so next fetch downloads fresh raw data.
            os.remove(csv_path)
            # Also remove sidecar so next run treats it as fresh
            if key in applied:
                del applied[key]
            print(f"  {symbol}: CORRUPTED data detected (first close={first_pre_ex_close:.2f}). "
                  f"Deleted CSV - will be re-fetched on next pipeline run.")
            return True

        # Data looks consistently raw - adjust everything
        for col in PRICE_COLS:
            df.loc[pre_mask, col] = (df.loc[pre_mask, col] * factor).round(2)
        df.to_csv(csv_path, index=False)
        applied[key] = True
        print(f"  {symbol}: First run - adjusted {pre_mask.sum()} rows (factor={factor})")
        return True

    # Last close doesn't match raw or adjusted - possibly double/triple adjusted
    # or partially corrupted. Delete and let it re-fetch.
    os.remove(csv_path)
    if key in applied:
        del applied[key]
    print(f"  {symbol}: UNRECOVERABLE state (last pre-ex close={last_pre_ex_close:.2f}, "
          f"expected raw={raw_pre_ex_close:.2f} or adjusted={expected_adjusted:.2f}). "
          f"Deleted CSV - will be re-fetched on next pipeline run.")
    return True


def main():
    actions = load_actions()
    if not actions:
        print("No corporate actions configured.")
        return

    applied = load_applied()

    print(f"Processing {len(actions)} corporate action(s)...")
    count = 0
    for action in actions:
        if apply_adjustment(action, applied):
            count += 1

    save_applied(applied)
    print(f"Done. {count} adjustment(s) applied.")


if __name__ == "__main__":
    main()
