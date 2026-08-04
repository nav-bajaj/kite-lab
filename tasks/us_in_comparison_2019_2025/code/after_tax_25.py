"""Flat 25% tax applied to each calendar year's gain (loss carryforward),
on top of the 2019-2025 window results. Pre-tax yearly returns come from
yearly_2019_2025.csv (computed off the daily equity curves)."""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
TAX = 0.25
YEARS = list(range(2019, 2026))

yearly = pd.read_csv(HERE / "yearly_2019_2025.csv", index_col=0) / 100.0

rows = []
detail = {}
for col in yearly.columns:
    cap = 1.0
    carry = 0.0          # loss carryforward (positive number = losses banked)
    tax_paid = 0.0
    net_returns = []
    for y in YEARS:
        r = yearly.loc[y, col]
        start = cap
        gain = cap * r
        cap += gain
        if gain > 0:
            taxable = max(0.0, gain - carry)
            carry = max(0.0, carry - gain)
            tax = TAX * taxable
            cap -= tax
            tax_paid += tax
        else:
            carry += -gain
        net_returns.append(cap / start - 1)
    pre_final = (1 + yearly[col]).prod()
    pre_cagr = pre_final ** (1 / len(YEARS)) - 1
    post_cagr = cap ** (1 / len(YEARS)) - 1
    rows.append({
        "series": col,
        "pre_tax_cagr": round(pre_cagr * 100, 1),
        "post_tax_cagr": round(post_cagr * 100, 1),
        "drag_pp": round((pre_cagr - post_cagr) * 100, 1),
        "pre_tax_final_x": round(pre_final, 2),
        "post_tax_final_x": round(cap, 2),
        "tax_paid_x": round(tax_paid, 2),
    })
    detail[col] = [round(v * 100, 1) for v in net_returns]

df = pd.DataFrame(rows)
pd.set_option("display.width", 220)
print("=== Flat 25% tax on each year's gain, losses carried forward ===")
print(df.to_string(index=False))
print("\n=== After-tax calendar-year returns (%) ===")
ddf = pd.DataFrame(detail, index=YEARS)
print(ddf.to_string())
df.to_csv(HERE / "after_tax_25_summary.csv", index=False)
