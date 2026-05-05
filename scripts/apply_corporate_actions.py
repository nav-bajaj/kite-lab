"""Apply corporate action adjustments to historical price data.

Reads data/corporate_actions.json and adjusts OHLC prices in nse500_data/
for events like demergers, splits, and bonuses. Designed to run after every
price fetch so that re-fetched raw prices are always corrected.

Strategy:
- Threshold separates raw (unadjusted) from non-raw prices.
- On first run: if data is uniformly raw or uniformly adjusted, handles simply.
  If mixed (corrupted old + raw recent from re-fetch), uses boundary detection
  to fix each region independently.
- On subsequent runs (sidecar exists): just fixes raw rows from re-fetch.
- Sidecar stored in price dir (persistent volume on Railway).
"""

import json
import math
import os
import sys

import pandas as pd
import numpy as np

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

    threshold = raw_pre_ex_close * math.sqrt(factor)
    expected_adjusted = raw_pre_ex_close * factor
    pre_idx = df.index[pre_mask]
    last_pre_ex_close = df.loc[pre_idx[-1], "close"]

    previously_applied = key in applied

    if previously_applied:
        # Normal operation: fix any raw rows from re-fetch using threshold
        raw_rows = pre_mask & (df["close"] > threshold)
        if not raw_rows.any():
            print(f"  {symbol}: All prices adjusted, skipping")
            return False
        for col in PRICE_COLS:
            df.loc[raw_rows, col] = (df.loc[raw_rows, col] * factor).round(2)
        df.to_csv(csv_path, index=False)
        print(f"  {symbol}: Re-fetch fix - adjusted {raw_rows.sum()} rows")
        return True

    # First time processing on this volume.
    last_is_adjusted = abs(last_pre_ex_close - expected_adjusted) / expected_adjusted < 0.02

    if last_is_adjusted:
        # Data looks adjusted already - mark and move on
        applied[key] = True
        print(f"  {symbol}: Already adjusted (close={last_pre_ex_close:.2f}), marking as applied")
        return False

    # Data needs fixing. Determine the state and fix.
    raw_mask = pre_mask & (df["close"] > threshold)
    has_raw = raw_mask.any()
    has_non_raw = (pre_mask & ~raw_mask).any()

    if has_raw and not has_non_raw:
        # All data is raw (true first run) - just apply factor
        for col in PRICE_COLS:
            df.loc[pre_mask, col] = (df.loc[pre_mask, col] * factor).round(2)
        df.to_csv(csv_path, index=False)
        applied[key] = True
        print(f"  {symbol}: First run - adjusted {pre_mask.sum()} rows (factor={factor})")
        return True

    if has_raw and has_non_raw:
        # Mixed state: corrupted old data + raw recent data from re-fetch.
        # Strategy:
        # 1. Adjust raw rows by factor
        # 2. Find the boundary between corrupted and raw regions
        # 3. Compute correction for old region using the boundary

        # Step 1: adjust raw rows
        for col in PRICE_COLS:
            df.loc[raw_mask, col] = (df.loc[raw_mask, col] * factor).round(2)

        # Step 2: find boundary (first raw row's position in pre-ex data)
        raw_positions = df.index[raw_mask]
        first_raw_pos = raw_positions[0]
        # The row just before the first raw row is the last corrupted row
        pre_positions = df.index[pre_mask]
        boundary_idx = pre_positions[pre_positions < first_raw_pos][-1]

        # Step 3: compute correction
        # After step 1, the first raw row is now correctly adjusted.
        # The day before should be close to it (normal daily return).
        first_adjusted_close = df.loc[first_raw_pos, "close"]
        last_corrupted_close = df.loc[boundary_idx, "close"]

        if last_corrupted_close > 0:
            old_correction = first_adjusted_close / last_corrupted_close
            old_mask = pre_mask & (df.index <= boundary_idx)
            for col in PRICE_COLS:
                df.loc[old_mask, col] = (df.loc[old_mask, col] * old_correction).round(2)
            print(f"  {symbol}: Mixed state - adjusted {raw_mask.sum()} raw rows, "
                  f"corrected {old_mask.sum()} old rows (correction={old_correction:.4f})")

        df.to_csv(csv_path, index=False)
        applied[key] = True
        return True

    # No raw rows at all - data is uniformly corrupted (some factor^N).
    # Use the last close as anchor to compute uniform correction.
    correction = expected_adjusted / last_pre_ex_close
    for col in PRICE_COLS:
        df.loc[pre_mask, col] = (df.loc[pre_mask, col] * correction).round(2)
    df.to_csv(csv_path, index=False)
    applied[key] = True
    print(f"  {symbol}: Uniform correction applied (factor={correction:.4f}, "
          f"last close: {last_pre_ex_close:.2f} -> {expected_adjusted:.2f})")
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
