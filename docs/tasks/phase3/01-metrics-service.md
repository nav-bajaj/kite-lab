# Task 1: Metrics Service

**Status**: `completed`
**Blocked By**: None
**Blocks**: #2, #3, #4

## Objective

Create a service to calculate and retrieve performance metrics from the database.

## Tasks

- [ ] Create `metrics_service.py` in `kite-api/app/services/`
- [ ] Implement `get_metrics()` function
- [ ] Implement `get_equity_curve()` function
- [ ] Implement `get_monthly_returns()` function
- [ ] Calculate derived metrics (Sharpe, Sortino, Calmar)
- [ ] Support universe parameter

## Implementation

### File: `kite-api/app/services/metrics_service.py`

```python
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session
from app.models.database import get_session_local
from app.models.models import Metric, EquityCurve

def get_metrics(universe: str = "nse500") -> dict:
    """
    Get comprehensive performance metrics for a universe.

    Returns metrics from database plus calculated ratios.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Get latest metrics record
        metric = db.query(Metric).filter(
            Metric.universe == universe
        ).order_by(Metric.computed_date.desc()).first()

        if not metric:
            return {"error": "No metrics found"}

        # Get equity curve for additional calculations
        equity_data = db.query(EquityCurve).filter(
            EquityCurve.universe == universe
        ).order_by(EquityCurve.date).all()

        # Calculate Sharpe, Sortino, Calmar if not in DB
        volatility = calculate_volatility(equity_data)
        sharpe = calculate_sharpe(metric.cagr, volatility)
        sortino = calculate_sortino(equity_data, metric.cagr)
        calmar = metric.cagr / abs(metric.max_drawdown) if metric.max_drawdown else None

        return {
            "period": {
                "start": str(metric.start_date),
                "end": str(metric.end_date),
                "days": (metric.end_date - metric.start_date).days if metric.start_date and metric.end_date else 0
            },
            "returns": {
                "total_return": float(metric.total_return) * 100 if metric.total_return else 0,
                "cagr": float(metric.cagr) * 100 if metric.cagr else 0,
                "mtd": calculate_mtd(equity_data),
                "ytd": calculate_ytd(equity_data)
            },
            "risk": {
                "max_drawdown": float(metric.max_drawdown) * 100 if metric.max_drawdown else 0,
                "max_dd_duration": metric.max_drawdown_duration,
                "volatility": volatility,
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "calmar_ratio": calmar
            },
            "activity": {
                "total_trades": metric.trades_total,
                "avg_turnover": float(metric.avg_turnover_pct) * 100 if metric.avg_turnover_pct else 0,
                "annualized_turnover": float(metric.annualized_turnover) * 100 if metric.annualized_turnover else 0,
                "avg_holding_days": float(metric.avg_holding_days) if metric.avg_holding_days else 0,
                "hit_rate": float(metric.hit_rate) * 100 if metric.hit_rate else 0
            }
        }
    finally:
        db.close()


def get_equity_curve(
    universe: str = "nse500",
    start: Optional[date] = None,
    end: Optional[date] = None
) -> dict:
    """
    Get equity curve data for charting.

    Returns daily portfolio value, benchmark, and drawdown.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        query = db.query(EquityCurve).filter(
            EquityCurve.universe == universe
        )

        if start:
            query = query.filter(EquityCurve.date >= start)
        if end:
            query = query.filter(EquityCurve.date <= end)

        query = query.order_by(EquityCurve.date)
        records = query.all()

        data = []
        for r in records:
            data.append({
                "date": str(r.date),
                "portfolio_value": float(r.portfolio_value),
                "benchmark_value": float(r.benchmark) if r.benchmark else None,
                "drawdown": float(r.drawdown) * 100 if r.drawdown else 0
            })

        return {"data": data, "count": len(data)}
    finally:
        db.close()


def get_monthly_returns(universe: str = "nse500") -> dict:
    """
    Calculate monthly returns matrix for heatmap display.

    Returns years and monthly return percentages.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        records = db.query(EquityCurve).filter(
            EquityCurve.universe == universe
        ).order_by(EquityCurve.date).all()

        if not records:
            return {"years": [], "data": []}

        # Group by year-month and calculate returns
        monthly_data = calculate_monthly_returns(records)

        return monthly_data
    finally:
        db.close()


# Helper functions

def calculate_volatility(equity_data: list, annualize: bool = True) -> float:
    """Calculate annualized volatility from equity curve."""
    if len(equity_data) < 2:
        return 0

    import numpy as np
    values = [float(e.portfolio_value) for e in equity_data]
    returns = np.diff(values) / values[:-1]
    vol = np.std(returns)

    if annualize:
        vol *= np.sqrt(252)  # Trading days per year

    return round(vol * 100, 2)


def calculate_sharpe(cagr: float, volatility: float, risk_free: float = 0.05) -> float:
    """Calculate Sharpe ratio."""
    if volatility == 0:
        return 0
    return round((cagr - risk_free) / (volatility / 100), 2)


def calculate_sortino(equity_data: list, cagr: float, risk_free: float = 0.05) -> float:
    """Calculate Sortino ratio using downside deviation."""
    if len(equity_data) < 2:
        return 0

    import numpy as np
    values = [float(e.portfolio_value) for e in equity_data]
    returns = np.diff(values) / values[:-1]

    # Only negative returns for downside deviation
    negative_returns = returns[returns < 0]
    if len(negative_returns) == 0:
        return 0

    downside_dev = np.std(negative_returns) * np.sqrt(252)
    if downside_dev == 0:
        return 0

    return round((cagr - risk_free) / downside_dev, 2)


def calculate_mtd(equity_data: list) -> float:
    """Calculate month-to-date return."""
    # Implementation details...
    pass


def calculate_ytd(equity_data: list) -> float:
    """Calculate year-to-date return."""
    # Implementation details...
    pass


def calculate_monthly_returns(equity_data: list) -> dict:
    """Calculate monthly returns for heatmap."""
    # Implementation details...
    pass
```

## Database Queries

### Get Latest Metrics
```sql
SELECT * FROM metrics
WHERE universe = 'nse500'
ORDER BY computed_date DESC
LIMIT 1;
```

### Get Equity Curve
```sql
SELECT date, portfolio_value, benchmark, drawdown
FROM equity_curve
WHERE universe = 'nse500'
ORDER BY date;
```

## Verification

```python
from app.services.metrics_service import get_metrics

result = get_metrics("nse500")
assert "cagr" in result["returns"]
assert "sharpe_ratio" in result["risk"]
```

## Notes

- Sharpe calculation uses 5% risk-free rate
- Sortino uses only downside deviation
- All percentages returned as numbers (not decimals)

---

*Status Key: `pending` | `in_progress` | `completed`*
