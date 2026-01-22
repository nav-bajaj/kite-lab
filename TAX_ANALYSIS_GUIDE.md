# Tax Impact Analysis Guide

## Overview

The tax analysis script (`analyze_tax_impact.py`) simulates the impact of taxation on portfolio returns using the **Indian Financial Year** (April 1 - March 31) taxation model.

## Tax Model

### Indian Financial Year Structure
- **FY 2020-21**: April 1, 2020 to March 31, 2021
- **FY 2021-22**: April 1, 2021 to March 31, 2022
- And so on...

### Tax Application Method
1. **At end of each FY** (March 31), calculate gains: `Gain = End Value - Start Capital`
2. **Apply tax rate** (default 25%) on positive gains only
3. **Deduct tax** from portfolio: `Post-Tax Value = End Value - Tax Amount`
4. **Continue investing** with post-tax amount in next FY
5. **No tax on losses**: If FY ends in loss, carry forward capital with no tax

### Key Assumptions
- **Flat tax rate**: 25% (configurable)
- **Annual taxation**: Tax paid once per year at FY end
- **No tax loss harvesting**: Losses don't offset future gains
- **No advance tax**: All tax paid at year-end
- **Full reinvestment**: All post-tax capital stays invested

## Usage

### Basic Usage

```bash
# Analyze tax impact on a backtest
python scripts/analyze_tax_impact.py \
    --equity data/backtests/momentum_equity.csv
```

This will:
- Load portfolio equity curve
- Apply 25% tax at end of each FY
- Print detailed report to console

### Generate Full Report with Outputs

```bash
python scripts/analyze_tax_impact.py \
    --equity experiments/final_portfolio/*/backtests/baseline/momentum_equity.csv \
    --initial-capital 1000000 \
    --tax-rate 0.25 \
    --output reports/tax_impact_report.txt \
    --chart reports/tax_impact_chart.png \
    --csv reports/tax_impact_data.csv
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--equity` | Path to portfolio equity CSV (required) | - |
| `--tax-rate` | Tax rate on gains (0.0 to 1.0) | 0.25 (25%) |
| `--initial-capital` | Starting capital in rupees | 1,000,000 |
| `--output` | Save report to text file | Print to console |
| `--chart` | Generate comparison chart (PNG) | No chart |
| `--csv` | Export comparison data to CSV | No export |

## Report Contents

### 1. Overall Performance Summary
Compares pre-tax vs post-tax metrics:
- **CAGR**: Compound annual growth rate
- **Total Return**: Cumulative return over period
- **Final Portfolio Value**: Ending value
- **Volatility**: Annualized volatility
- **Total Tax Paid**: Sum of all tax payments

### 2. Year-by-Year Tax Breakdown
For each financial year:
- **FY**: Financial year label (e.g., FY2020-2021)
- **End Date**: Last date in the FY from dataset
- **Start Capital**: Capital at beginning of FY (post-tax from previous year)
- **End Value (Pre-Tax)**: Portfolio value before tax
- **Gain**: Profit for the FY
- **Tax**: Amount paid (25% of gain)
- **End Value (Post-Tax)**: Portfolio value after tax deduction

### 3. Key Insights
- CAGR reduction due to taxes
- Final value impact
- Total and average annual tax
- Compounding multipliers (pre-tax vs post-tax)
- Tax drag percentage on compounding

## Example Output

```
================================================================================
TAX IMPACT ANALYSIS REPORT
Indian Financial Year: April 1 - March 31
================================================================================

Initial Capital: ₹1,000,000
Tax Rate: 25.0%
Analysis Period: 2020-07-10 to 2026-01-19

--------------------------------------------------------------------------------
OVERALL PERFORMANCE
--------------------------------------------------------------------------------

Metric                         Pre-Tax              Post-Tax             Impact
--------------------------------------------------------------------------------
CAGR                                       60.12%              46.69%        -13.43%
Total Return                             1251.75%             732.69%       -519.06%
Final Portfolio Value          ₹      13,517,504  ₹       8,326,940  ₹ -5,190,564
Volatility                                 26.61%              28.18%          1.57%

Total Tax Paid: ₹2,437,311
Tax as % of Final Pre-Tax Value: 18.03%

--------------------------------------------------------------------------------
KEY INSIGHTS
--------------------------------------------------------------------------------

1. Tax reduces CAGR by 13.43% (from 60.12% to 46.69%)
2. Final portfolio value is ₹5,190,564 lower due to taxes
3. Total taxes paid: ₹2,437,311 over 6 financial years
4. Average annual tax: ₹406,219
5. Pre-tax: ₹1 becomes ₹13.52
6. Post-tax: ₹1 becomes ₹8.33
7. Tax drag on compounding: 38.4%
```

## Interpreting Results

### CAGR Reduction
For a 60% CAGR strategy:
- **Pre-Tax CAGR**: 60.12%
- **Post-Tax CAGR**: 46.69%
- **Reduction**: 13.43 percentage points

This is the **annual cost** of taxation on your compounding returns.

### Tax Drag on Compounding
The **38.4% tax drag** means:
- Without taxes: ₹1 → ₹13.52 (1,252% total return)
- With taxes: ₹1 → ₹8.33 (733% total return)
- **38.4% of the potential gain** is lost to taxes

This compounds over time - the longer the investment horizon, the larger the impact.

### Final Value Impact
- **Pre-Tax**: ₹13.5M final value
- **Post-Tax**: ₹8.3M final value
- **Loss**: ₹5.2M (38.4% lower)

On ₹1M initial capital over 5.5 years, you pay ₹2.4M in taxes, but lose ₹5.2M in final value due to **compounding impact**.

## Visualization

### Generated Chart (PNG)
The chart shows two plots:

1. **Portfolio Value Comparison**
   - Blue line: Pre-tax portfolio value
   - Red line: Post-tax portfolio value
   - Gray dashed lines: FY boundaries (March 31 each year)
   - Growing gap shows compounding impact of taxes

2. **Cumulative Tax Drag**
   - Orange shaded area: Total impact of taxes over time
   - Shows how taxes compound to reduce portfolio value
   - Step-like increases at each FY end (tax payment dates)

## CSV Export

The exported CSV contains:
- `date`: Daily dates
- `fy`: Financial year label
- `portfolio_value`: Pre-tax value
- `post_tax_value`: Post-tax value
- `tax_drag`: Difference (cumulative tax impact)

Use this data for:
- Custom analysis in Excel/Python
- Time-series analysis
- Integration with other tools

## Tax Rate Scenarios

### Compare Different Tax Rates

```bash
# Low tax (15%)
python scripts/analyze_tax_impact.py --equity ... --tax-rate 0.15 --output reports/tax_15pct.txt

# Medium tax (25% - default)
python scripts/analyze_tax_impact.py --equity ... --tax-rate 0.25 --output reports/tax_25pct.txt

# High tax (30%)
python scripts/analyze_tax_impact.py --equity ... --tax-rate 0.30 --output reports/tax_30pct.txt
```

### Expected Impact by Tax Rate

For a 60% CAGR strategy over 5 years:

| Tax Rate | Post-Tax CAGR | Final Value (₹1M) | Tax Drag |
|----------|---------------|-------------------|----------|
| 0% | 60.0% | ₹13.5M | 0% |
| 15% | 52.4% | ₹10.8M | 20% |
| 25% | 46.7% | ₹8.3M | 38% |
| 30% | 43.8% | ₹7.3M | 46% |

**Key insight**: Tax drag is **non-linear** due to compounding. A 25% tax rate doesn't just reduce returns by 25% - it reduces them by 38% due to lost compounding.

## Real-World Considerations

### What This Model Captures
✅ Annual taxation on gains
✅ Compounding impact of taxes
✅ Multi-year portfolio evolution
✅ Different starting capitals

### What This Model Doesn't Capture
❌ **Short-term vs Long-term capital gains** (uses flat rate)
❌ **Indexation benefits** (for long-term gains in India)
❌ **Tax loss harvesting** (selling losers to offset winners)
❌ **Advance tax** (quarterly payments during the year)
❌ **Surcharges and cess** (additional taxes above base rate)
❌ **Exemption limits** (e.g., ₹1 lakh LTCG exemption)

### For More Accurate Analysis
Consider:
1. **Short-term (<1 year)**: 15% tax on gains
2. **Long-term (>1 year)**: 10% tax on gains >₹1L (with indexation)
3. **Intra-year tax harvesting**: Realize losses to offset gains
4. **Advance tax**: Pay quarterly to avoid penalties

## Use Cases

### 1. Strategy Evaluation
**Question**: Is my 60% CAGR strategy still attractive after taxes?

**Answer**: Yes! 46.7% post-tax CAGR is still excellent compared to:
- Fixed deposits: ~7% (pre-tax), ~5% (post-tax)
- Index funds: ~12% CAGR (pre-tax), ~10% (post-tax)
- Real estate: ~8-10% (pre-tax)

### 2. Capital Allocation
**Question**: Should I invest ₹1M or ₹5M?

Run analysis with both amounts:
```bash
python scripts/analyze_tax_impact.py --equity ... --initial-capital 1000000
python scripts/analyze_tax_impact.py --equity ... --initial-capital 5000000
```

Tax impact scales proportionally, but psychological impact differs.

### 3. Withdrawal Planning
**Question**: When should I withdraw profits?

**Insight**: Each year, ₹400K average tax is paid. Plan liquidity accordingly:
- Keep ₹500K cash buffer for annual tax
- Or structure withdrawals to minimize tax events

### 4. Strategy Comparison
Compare multiple strategies:
```bash
# High return, high turnover strategy
python scripts/analyze_tax_impact.py --equity strategy_a.csv --output tax_a.txt

# Lower return, low turnover strategy
python scripts/analyze_tax_impact.py --equity strategy_b.csv --output tax_b.txt
```

Lower-turnover strategies may perform better post-tax!

## Advanced Analysis

### Tax-Adjusted Sharpe Ratio

From the output, you can compute:

```python
post_tax_sharpe = (post_tax_cagr - risk_free_rate) / post_tax_volatility
```

Note: Volatility increases slightly post-tax due to step-like tax deductions.

### Breakeven Analysis

To maintain same post-tax CAGR:
```
Required Pre-Tax CAGR = Target / (1 - effective_tax_drag_rate)
```

For 40% post-tax target with 38% tax drag:
```
Required Pre-Tax CAGR = 40% / (1 - 0.38) = 64.5%
```

## Integration with Other Tools

### Use with Backtest Reports

```bash
# Run backtest
python scripts/backtest_momentum.py ... --output-dir data/backtests/run1

# Analyze tax impact
python scripts/analyze_tax_impact.py \
    --equity data/backtests/run1/momentum_equity.csv \
    --output reports/run1_tax_impact.txt
```

### Batch Analysis

```bash
# Analyze all backtest runs
for run in data/backtests/*/momentum_equity.csv; do
    basename=$(basename $(dirname $run))
    python scripts/analyze_tax_impact.py \
        --equity "$run" \
        --output "reports/tax_${basename}.txt"
done
```

## Tips & Best Practices

1. **Use realistic initial capital**: Match your actual investment amount
2. **Run sensitivity analysis**: Test 15%, 20%, 25%, 30% tax rates
3. **Compare timeframes**: Longer periods show larger tax drag
4. **Consider turnover**: High-churn strategies suffer more from annual taxation
5. **Plan for liquidity**: Keep cash for tax payments (don't let it reduce portfolio)

## Limitations

### Model Assumptions
- **Simplified tax structure**: Real Indian tax code is more complex
- **Perfect foresight**: Assumes you know exact tax liability at year-end
- **No timing optimization**: Doesn't model strategic realization of gains/losses
- **No transaction costs**: Focuses purely on tax impact

### When to Use Alternative Tools
- **Detailed tax planning**: Consult a tax advisor
- **Multi-asset portfolios**: Use comprehensive tax software
- **Specific deductions**: Model your actual tax situation

## Further Reading

- **Indian Income Tax Act, 1961**: Capital gains taxation (Section 112A, 111A)
- **SEBI Investor Education**: Tax implications of equity trading
- **Tax calculators**: For detailed Indian tax computation

---

**Script**: `scripts/analyze_tax_impact.py`
**Author**: Kite-Lab System
**Last Updated**: 2026-01-22
