# Tracked Indices Documentation

## Overview

The kite-lab system now tracks **38 indices** across multiple categories to provide comprehensive benchmarking and market analysis for the momentum portfolio strategy.

## Indices Categories

### 1. Broad Market Indices (7 indices)
**Purpose**: Compare portfolio performance against broad market segments

- **NIFTY 50** - India's flagship benchmark (50 large-cap stocks)
- **NIFTY 100** - Top 100 companies (current primary benchmark)
- **NIFTY 500** - Broad market index (our trading universe)
- **NIFTY NEXT 50** - Next tier of large caps after Nifty 50
- **NIFTY MIDCAP 150** - Mid-cap segment
- **NIFTY SMLCAP 250** - Small-cap segment
- **NIFTY LARGEMID250** - Large + Mid cap blend

### 2. Factor/Strategy Indices (4 indices)
**Purpose**: Compare against other systematic strategies

- **NIFTY200 MOMENTM30** - Direct momentum strategy comparison from Nifty 200
- **NIFTY500 MOMENTUM 50** - Momentum strategy from Nifty 500 universe
- **NIFTY ALPHA 50** - Alpha factor-based strategy
- **NIFTY100 LOWVOL30** - Low volatility strategy (contrast with our vol-adjusted approach)

### 3. Sectoral Indices (23 indices)
**Purpose**: Understand sector exposure and relative performance

**Financial Sector**:
- NIFTY BANK - Banking sector
- NIFTY PVT BANK - Private sector banks
- NIFTY PSU BANK - Public sector banks
- NIFTY FIN SERVICE - Financial services

**Technology & Digital**:
- NIFTY IT - Information technology

**Industrial & Manufacturing**:
- NIFTY AUTO - Automobile sector
- NIFTY METAL - Metals sector
- NIFTY INFRA - Infrastructure

**Energy & Resources**:
- NIFTY ENERGY - Energy sector
- NIFTY OIL AND GAS - Oil and gas sector

**Consumer**:
- NIFTY FMCG - Fast-moving consumer goods
- NIFTY CONSUMPTION - Consumer sector
- NIFTY CONSR DURBL - Consumer durables

**Healthcare**:
- NIFTY PHARMA - Pharmaceutical sector
- NIFTY HEALTHCARE - Healthcare sector

**Real Estate & Services**:
- NIFTY REALTY - Real estate sector
- NIFTY SERV SECTOR - Services sector
- NIFTY MEDIA - Media and entertainment

**Others**:
- NIFTY COMMODITIES - Commodities sector
- NIFTY MNC - Multinational corporations
- NIFTY PSE - Public sector enterprises
- NIFTY CPSE - Central public sector enterprises

### 4. Global Indices (3 indices)
**Purpose**: Compare against international markets

- **US500** (S&P 500) - US large-cap benchmark
- **US100** (NASDAQ 100) - US technology benchmark
- **US30** (Dow Jones) - US blue-chip benchmark

### 5. Commodity Indices (2 indices)
**Purpose**: Track commodity market performance

- **MCXGOLDEX** - MCX Gold index
- **MCXSILVDEX** - MCX Silver index

## Data Files

### Configuration
- **tracked_indices.csv** - Master list of tracked indices with metadata
  - Columns: instrument_token, exchange_token, tradingsymbol, name, exchange, category, description

### Historical Data
- **indices_data/** - Directory containing daily OHLC data for all indices
  - One CSV file per index (e.g., `NIFTY_50.csv`, `US500.csv`)
  - Format: date, open, high, low, close, volume
  - History: 2020-01-01 to present

## Usage

### 1. Fetch Historical Data

**First time** (fetch all historical data):
```bash
python scripts/fetch_indices_history.py
```

**Daily updates** (included in daily pipeline):
```bash
python scripts/run_daily_pipeline.py --with-login
```

The daily pipeline now includes:
1. Refresh NSE 500 data
2. **Fetch indices data** (new step)
3. Update Nifty 100 benchmark
4. Build momentum rankings

### 2. Generate Indices Report

Compare your portfolio against all tracked indices:

```bash
# Using latest final portfolio equity
python scripts/report_indices.py \
    --portfolio experiments/final_portfolio/final_portfolio_20260120182943/backtests/baseline/momentum_equity.csv \
    --output reports/indices_comparison.html

# Using a specific backtest run
python scripts/report_indices.py \
    --portfolio data/backtests/momentum_equity.csv \
    --output reports/indices_report.html

# Custom indices directory
python scripts/report_indices.py \
    --portfolio data/backtests/momentum_equity.csv \
    --indices-dir custom_indices_data \
    --output reports/custom_report.html
```

### 3. Report Contents

The generated HTML report includes:

**Summary Section**:
- Portfolio performance summary (CAGR, volatility, Sharpe, max drawdown)
- Report metadata (date range, number of indices tracked)

**Comprehensive Metrics Table**:
- All indices with CAGR, volatility, Sharpe ratio, max drawdown
- Correlation and beta vs portfolio
- Total return over period
- Sortable by any metric

**Equity Curves**:
- Normalized performance comparison (base 100)
- Portfolio vs all indices
- Category-wise equity curves

**Correlation Analysis**:
- Heatmap showing correlation with portfolio
- Identify indices with similar/opposite behavior

**Category-Wise Analysis**:
- Separate sections for each category
- Detailed metrics tables
- Category-specific equity curves

## Metrics Explained

### Performance Metrics
- **CAGR** (Compound Annual Growth Rate): Annualized return
- **Volatility**: Annualized standard deviation of returns
- **Sharpe Ratio**: Risk-adjusted return (assumes 5% risk-free rate)
- **Max Drawdown**: Largest peak-to-trough decline
- **Total Return**: Cumulative return over period

### Relative Metrics
- **Correlation**: How closely returns move together (-1 to +1)
  - +1: Perfect positive correlation
  - 0: No correlation
  - -1: Perfect negative correlation (hedge)
- **Beta**: Sensitivity to index movements
  - Beta > 1: More volatile than index
  - Beta = 1: Moves with index
  - Beta < 1: Less volatile than index

## Analysis Use Cases

### 1. Performance Benchmarking
Compare portfolio CAGR against:
- NIFTY 50 (flagship benchmark)
- NIFTY 500 (trading universe)
- NIFTY200 MOMENTM30 (direct momentum comparison)

**Question**: Does our strategy outperform standard momentum indices?

### 2. Factor Exposure Analysis
Compare correlation with:
- NIFTY ALPHA 50 (alpha factor)
- NIFTY100 LOWVOL30 (low volatility)
- NIFTY500 MOMENTUM 50 (momentum factor)

**Question**: What factors drive our returns?

### 3. Sector Concentration Risk
Check correlation with sectoral indices:
- High correlation with NIFTY BANK → Banking concentration
- High correlation with NIFTY IT → Tech concentration

**Question**: Are we too concentrated in specific sectors?

### 4. Market Regime Analysis
During market downturns, compare:
- Max drawdown vs NIFTY 50
- Recovery speed vs NIFTY 100
- Defensive performance vs NIFTY FMCG/NIFTY PHARMA

**Question**: Does our strategy protect capital in bear markets?

### 5. Global Market Correlation
Check correlation with:
- US500 (S&P 500)
- US100 (NASDAQ)

**Question**: How exposed are we to global market movements?

### 6. Commodity Hedge
Check correlation with:
- MCXGOLDEX (gold)
- MCXSILVDEX (silver)

**Question**: Do commodities provide diversification?

## Maintenance

### Adding New Indices

1. Find instrument token in `data/instruments_full.csv`
2. Add row to `data/static/tracked_indices.csv`:
   ```csv
   instrument_token,exchange_token,tradingsymbol,name,exchange,category,description
   256265,1001,NIFTY 50,NIFTY 50,NSE,broad_market,India's flagship benchmark
   ```
3. Run `python scripts/fetch_indices_history.py`

### Removing Indices

1. Remove row from `data/static/tracked_indices.csv`
2. Optionally delete CSV file from `indices_data/`

### Updating Historical Data

Incremental updates happen automatically:
- Script detects last date in each CSV
- Only fetches new data from that date forward
- No need to re-download entire history

## API Rate Limiting

The fetch script respects Zerodha API limits:
- 0.2 second delay between requests (5 req/sec max)
- Automatic retry with exponential backoff on rate limiting
- Daily data: 1900-day chunks per API call

**Estimated time**: ~40 seconds for 38 indices (daily updates ~10 seconds)

## Troubleshooting

### Error: "Missing access_token.txt"
**Solution**: Run `python scripts/login_and_save_token.py` first

### Error: "No indices found"
**Solution**: Run `python scripts/fetch_indices_history.py` to fetch data

### Error: "No overlapping dates for index"
**Cause**: Index has no data in portfolio date range
**Solution**: Check if index is newly listed or data is missing

### Warning: "Skipping index - empty or missing 'close' column"
**Cause**: Corrupted or incomplete CSV file
**Solution**: Delete the file and re-fetch: `python scripts/fetch_indices_history.py`

## Data Directory Structure

```
kite-lab/
├── data/
│   ├── static/
│   │   ├── tracked_indices.csv          # Index configuration
│   │   └── README_INDICES.md            # This file
│   └── ...
├── indices_data/                         # Gitignored
│   ├── NIFTY_50.csv
│   ├── NIFTY_100.csv
│   ├── NIFTY_500.csv
│   ├── NIFTY_BANK.csv
│   ├── US500.csv
│   └── ... (38 files total)
├── scripts/
│   ├── fetch_indices_history.py         # Fetch indices data
│   └── report_indices.py                # Generate comparison report
└── reports/                              # Generated reports
    └── indices_comparison.html
```

## Future Enhancements

Potential additions:
1. **More global indices**: Europe (DAX, FTSE), Asia (Nikkei, Hang Seng)
2. **Factor indices**: Value, growth, quality indices
3. **Thematic indices**: ESG, digital economy, manufacturing
4. **Custom indices**: Equal-weight, momentum variants
5. **Real-time data**: Intraday index tracking
6. **Alerts**: Notify when portfolio diverges from indices

## References

- **NSE Indices**: https://www.niftyindices.com/
- **BSE Indices**: https://www.bseindia.com/indices/
- **Zerodha Instruments**: `data/instruments_full.csv`
- **Kite Connect API**: https://kite.trade/docs/connect/v3/

---

**Last Updated**: 2026-01-21
**Maintained By**: Kite-Lab System
