# EODHD pricing — tier selection for US daily EOD

Research artifact for the `us-data` branch. Verified against eodhd.com on 2026-05-14.

## Need

- ~600 unique US tickers (S&P 500 ∪ Nasdaq 100), daily OHLCV.
- Split- and dividend-adjusted closes (required for momentum/backtest).
- 20+ years of history.
- Headroom for a future daily refresh (~600 calls/day at the minimum; ideally 1 call/day via the bulk endpoint).

## Tiers

| Tier | $/mo | Calls/day | Calls/min | US EOD | History | Notes |
|---|---|---|---|---|---|---|
| Free (registered) | $0 | 20 | 1000 | **No** | 1 yr | Excludes US — not viable |
| **EOD Historical Data — All World** | **$19.99** | 100,000 | 1000 | ✓ | 30+ yr | **Recommended** |
| EOD + Intraday — All World Extended | $29.99 | 100,000 | 1000 | ✓ | 30+ yr | Adds intraday; not needed |
| Fundamentals Data Feed | $59.99 | 100,000 | 1000 | ✓ | 30+ yr | Overkill |
| ALL-IN-ONE | $99.99 | 100,000 | 1000 | ✓ | 30+ yr | Overkill |

Demo token `demo` is free and works for: `AAPL.US`, `TSLA.US`, `AMZN.US`, `VTI.US`, `BTC-USD.CC`, `EURUSD.FOREX`. Used for Phase-0 infra validation.

## Recommendation

**EOD Historical Data — All World — $19.99/mo.**

Why:
- Cheapest tier that includes US EOD with adjusted close.
- 100,000 calls/day and 1,000 calls/min — initial 600-symbol backfill completes in <1 min; daily refresh sits in single-digit-percent of daily quota.
- 30+ year history covers everything the existing momentum engine needs (and far more than the 2009-start NSE panel).
- Bulk-EOD endpoint (`/api/eod-bulk-last-day/US`) — confirm inclusion at sign-up; if included, daily refresh becomes **1 call** for the entire exchange.

## Comparison vs Alpha Vantage (rejected)

| | EODHD | Alpha Vantage |
|---|---|---|
| Cheapest tier with US adjusted EOD | **$19.99** | $49.99 |
| Calls/min | **1000** | 75 |
| Bulk endpoint | **Yes** | No |
| History (US) | **30+ yr** | 20+ yr |

EODHD is ~60% cheaper, 13× the per-minute throughput, longer history, and has a structural advantage (bulk endpoint) that AV does not offer.
