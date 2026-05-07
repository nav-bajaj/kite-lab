# Phase 1: Signal Generation

**File:** `scripts/build_trend_leaders_signals.py`

**Status:** Done

**Depends on:** Nothing (first phase)

---

## Objective

Create a signal generator that takes NSE 500 price data, computes trend eligibility and a 4-component Trend Quality Score, and outputs:
1. A signals CSV with the top-20 stocks per monthly rebalance date
2. A full audit CSV with all 500 stocks' scores per rebalance date

---

## Tasks

- [ ] **1.1** Load close price panel from `nse500_data/` with optional universe filtering
- [ ] **1.2** Compute moving averages (50, 100, 200 DMA) using `ta_indicators.sma()`
- [ ] **1.3** Implement trend eligibility filter
- [ ] **1.4** Implement MA Structure Score (Component 1)
- [ ] **1.5** Implement Trend Persistence Score (Component 2)
- [ ] **1.6** Implement Distance from 200 DMA Score (Component 3)
- [ ] **1.7** Implement Drawdown Control Score (Component 4)
- [ ] **1.8** Implement composite Trend Quality Score with percentile normalization
- [ ] **1.9** Derive monthly rebalance dates (1st trading day of each month)
- [ ] **1.10** Build signal output (top-20 per date) and audit output (all stocks per date)
- [ ] **1.11** Add CLI with argparse
- [ ] **1.12** Run and validate signals

---

## Function Signatures

```python
def load_close_panel(data_dir: Path, universe: Optional[Set[str]] = None) -> pd.DataFrame:
    """Load daily close prices into Date x Symbol panel. Reuses pattern from
    build_momentum_signals_flexible.py."""

def compute_moving_averages(close: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute 50, 100, 200 DMA for all stocks.
    Returns {'sma_50': DataFrame, 'sma_100': DataFrame, 'sma_200': DataFrame}"""

def compute_eligibility(close, sma_50, sma_200) -> pd.DataFrame:
    """Boolean Date x Symbol DataFrame. True where:
    - Close > 200 DMA
    - 50 DMA > 200 DMA
    - 200 DMA today > 200 DMA 20 trading days ago (slope rising)"""

def compute_ma_structure_score(close, sma_50, sma_100, sma_200) -> pd.DataFrame:
    """0.25 * I(Close > 50 DMA) + 0.25 * I(50 > 100 DMA)
     + 0.25 * I(100 > 200 DMA) + 0.25 * I(200 DMA slope > 0)"""

def compute_persistence_score(close, sma_100, window=63) -> pd.DataFrame:
    """Rolling fraction of days Close > 100 DMA over last `window` trading days."""

def compute_distance_200_score(close, sma_200) -> pd.DataFrame:
    """Penalized distance scoring:
    <5%: ramp up (distance/0.05)
    5-35%: score = 1.0
    >35%: ramp down, max(0, 1 - (d-0.35)/0.35)"""

def compute_drawdown_control_score(close, window=126) -> pd.DataFrame:
    """clip(1 + (Close / rolling_high_126d - 1), 0, 1)"""

def compute_trend_quality_score(
    ma_score, persistence_score, distance_score, drawdown_score,
    eligibility, weights=(0.30, 0.30, 0.20, 0.20)
) -> pd.DataFrame:
    """Percentile-rank each component among eligible stocks, then weighted sum."""

def derive_monthly_rebalance_dates(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First trading day of each month."""

def build_signals(
    close, tqs, eligibility, components, rebalance_dates, top_n=20
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (signals_df, audit_df).
    signals_df: date, rank, symbol, score, + component columns (top-N only)
    audit_df: date, symbol, all scores, eligibility, rank, selected flag"""
```

---

## CLI Interface

```bash
python scripts/build_trend_leaders_signals.py \
  --prices-dir nse500_data \
  --universe data/static/nse500_universe.csv \
  --output data/trend_leaders/signals/trend_leaders_signals.csv \
  --audit-output data/trend_leaders/signals/trend_scores_by_rebalance.csv \
  --top-n 20 \
  --scoring-mode composite   # or "persistence_only" for Variant 4
```

**`--scoring-mode persistence_only`** skips the composite TQS and ranks by trend persistence alone (for Variant 4 backtest).

---

## Output Formats

### Signals CSV (`trend_leaders_signals.csv`)
```
date,rank,symbol,score,ma_structure,persistence,distance_200,drawdown_control,eligible_count
2020-08-03,1,INFY,0.87,1.00,0.92,0.85,0.71,147
2020-08-03,2,TCS,0.84,1.00,0.89,0.91,0.73,147
...
```

### Audit CSV (`trend_scores_by_rebalance.csv`)
```
date,symbol,close,sma_50,sma_100,sma_200,sma_200_20d_ago,eligible,ma_structure_score,persistence_score,distance_200_raw,distance_200_score,drawdown_6m,drawdown_control_score,trend_quality_score,rank,selected,target_weight
```

---

## Validation Criteria

- [ ] `eligible_count` per month is reasonable (100-300 bull, <50 correction)
- [ ] All TQS component scores are in [0, 1]
- [ ] Composite TQS is in [0, 1]
- [ ] Audit file has entries for all ~500 stocks per rebalance date
- [ ] No stocks selected that fail eligibility filter
- [ ] Spot-check 2-3 stocks' eligibility against their price charts
- [ ] `persistence_only` mode produces different rankings than composite

---

## Key Dependencies

| File | Usage |
|------|-------|
| `ta_indicators.py` | `sma()` function |
| `data/static/nse500_universe.csv` | Universe filtering |
| `nse500_data/*_day.csv` | Price data input |
