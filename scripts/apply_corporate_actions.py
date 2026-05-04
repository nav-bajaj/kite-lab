"""Apply corporate action adjustments to historical price data.

Reads data/corporate_actions.json and adjusts OHLC prices in nse500_data/
for events like demergers, splits, and bonuses. Designed to run after every
price fetch so that re-fetched raw prices are always corrected.

Idempotency strategy:
- First run: adjusts ALL pre-ex-date prices (tracked via sidecar file).
- Subsequent runs: scans ALL pre-ex-date rows using a price threshold
  (geometric mean of raw and adjusted reference prices) to find any
  re-fetched raw rows, and adjusts only those.
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
# Store sidecar in PRICE_DIR (persistent volume on Railway) so it survives redeploys
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

    previously_applied = key in applied

    # Check the last pre-ex close to determine if data is raw or adjusted
    last_pre_ex_close = df.loc[pre_mask, "close"].iloc[-1]
    expected_adjusted = raw_pre_ex_close * factor
    data_is_adjusted = abs(last_pre_ex_close - expected_adjusted) / expected_adjusted < 0.05
    data_is_raw = abs(last_pre_ex_close - raw_pre_ex_close) / raw_pre_ex_close < 0.05

    # Detect double-adjusted data (factor applied twice: close ≈ raw * factor^2)
    expected_double = raw_pre_ex_close * factor * factor
    data_is_double_adjusted = abs(last_pre_ex_close - expected_double) / expected_double < 0.05

    if data_is_double_adjusted:
        # Recover: divide by factor to get back to single-adjusted
        for col in PRICE_COLS:
            df.loc[pre_mask, col] = (df.loc[pre_mask, col] / factor).round(2)
        df.to_csv(csv_path, index=False)
        applied[key] = True
        print(f"  {symbol}: RECOVERED from double-adjustment - divided {pre_mask.sum()} rows by factor")
        return True

    if not previously_applied:
        if data_is_adjusted:
            # Data already adjusted (e.g., restored from backup), just mark as applied
            applied[key] = True
            print(f"  {symbol}: Already adjusted (close={last_pre_ex_close:.2f}), marking as applied")
            return False
        if not data_is_raw:
            print(f"  {symbol}: WARNING - last pre-ex close ({last_pre_ex_close:.2f}) doesn't match "
                  f"raw ({raw_pre_ex_close:.2f}), adjusted ({expected_adjusted:.2f}), "
                  f"or double-adjusted ({expected_double:.2f}). Manual review needed.")
            return False
        # First run: all pre-ex rows are raw, adjust everything
        for col in PRICE_COLS:
            df.loc[pre_mask, col] = (df.loc[pre_mask, col] * factor).round(2)
        df.to_csv(csv_path, index=False)
        applied[key] = True
        print(f"  {symbol}: First run - adjusted {pre_mask.sum()} rows (factor={factor})")
        return True

    # Subsequent run: scan for any raw rows that survived a re-fetch.
    # Raw prices are above the threshold; adjusted prices are below.
    threshold = raw_pre_ex_close * math.sqrt(factor)
    raw_rows = pre_mask & (df["close"] > threshold)

    if not raw_rows.any():
        print(f"  {symbol}: All prices adjusted, skipping")
        return False

    for col in PRICE_COLS:
        df.loc[raw_rows, col] = (df.loc[raw_rows, col] * factor).round(2)

    df.to_csv(csv_path, index=False)
    print(f"  {symbol}: Re-fetch fix - adjusted {raw_rows.sum()} rows (threshold={threshold:.2f})")
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
