# Module 1 assets and source ledger

## Required learner-facing visuals

### A1 — Five-object card set

Format: five cards.

```text
COMPANY     the business
SECURITY    a financial claim
EXCHANGE    a regulated trading venue
INDEX       a rules-based measurement
UNIVERSE    the set an analysis is applied to
```

Accessibility: do not rely on color alone; each card needs an icon and
one-sentence definition.

### A2 — NSE/BSE overlap diagram

Format: two overlapping circles.

Purpose: show why exchange counts cannot be added.

Do not:

- size circles to imply current market share;
- place a precise company count inside either circle unless dated; or
- imply every dual-listed security has identical liquidity.

### A3 — Indian equity-universe funnel

Format: vertical funnel based on `LESSON.md`.

Required layers:

1. exchange-listed landscape;
2. NSE-listed companies and segments;
3. eligible traded common equity;
4. official Nifty 500; and
5. Marketworks dated/covered universe.

Each layer needs a “what was removed or changed?” annotation.

### A4 — Size ladder

Format: stacked 100 + 150 + 250 blocks with an additional 250 microcap block.

Labels:

```text
Nifty 100         large cap
Nifty Midcap 150  mid cap
Nifty Smallcap 250 small cap
Nifty Microcap 250 beyond Nifty 500
```

The visual should make clear that the Nifty 500 contains the first three
blocks, not the microcap block.

### A5 — Eligibility funnel

Format: five icon filters.

- security and domicile eligibility;
- trading frequency;
- free float;
- impact cost;
- turnover and market-cap rank.

Footer:

> Simplified for learning. Current official methodology controls.

### A6 — Weighted index versus breadth

Format: paired chart.

Left:

- ten bars sized by index weight;
- two largest bars green;
- eight smaller bars red;
- weighted index return `+0.30%`.

Right:

- ten equal dots;
- two green, eight red;
- advance participation `20%`.

Accessibility: label green as “advanced” and red as “declined.”

### A7 — Universe contract

Format: reusable card.

```text
Official reference
Constituent snapshot date
Price-data date
Intended members
Metric-eligible members
Missing/excluded
Weighting/counting method
Methodology version
```

This asset should reappear in Modules 2-6.

## Product screenshots

Capture at desktop and mobile:

1. Marketworks Pulse header and as-of date;
2. breadth panel;
3. `% above 200-DMA` Learn page;
4. screener with row count and filters;
5. official Nifty 500 page; and
6. official methodology eligibility section.

Screenshot footer:

```text
Captured:
Data as of:
Source:
Course note:
```

No screenshot should contain an account name, email, holding, portfolio value,
or other personal information.

## Data fixtures

### F1 — Ten-stock weighting fixture

Stored initially in `WORKSHEET.md`; create CSV during production:

```text
symbol,index_weight,daily_return
A,0.30,0.02
B,0.20,0.01
C,0.15,-0.01
D,0.10,-0.01
E,0.08,-0.01
F,0.05,-0.01
G,0.04,-0.01
H,0.03,-0.01
I,0.03,-0.01
J,0.02,-0.01
```

Expected:

- weighted index return: `+0.003` or `+0.30%`;
- advance count: `2`;
- decline count: `8`; and
- advance participation: `20%`.

### F2 — Broker-search mock

Use fictional names. Include:

- main-board equity;
- SME equity;
- ETF;
- REIT;
- debt security; and
- preferred/other security.

Do not use real securities because the exercise is about classification, not
selection.

### F3 — Course universe manifest

Required fields:

```text
symbol
isin
company_name
official_index
membership_effective_date
snapshot_created_at
security_series
sector
price_history_available
metric_eligible_as_of
exclusion_reason
source
methodology_version
```

The learner does not need every field on screen. The facilitator and dashboard
must retain them.

## Source ledger

### Dynamic facts — refresh before recording and each cohort

| Fact | Current study value | As-of | Primary source |
|---|---:|---|---|
| NSE-listed companies | 2,898 | 31 Dec 2025 | [NSE Annual Highlights 2025](https://nsearchives.nseindia.com/web/pressrelease/2026-01/PR_cc_01012026_20260101194417.pdf) |
| NSE main-board companies | 2,358 | 31 Dec 2025 | [NSE Annual Highlights 2025](https://nsearchives.nseindia.com/web/pressrelease/2026-01/PR_cc_01012026_20260101194417.pdf) |
| Nifty 500 free-float market-cap coverage | about 92.04% | 30 Mar 2026 | [Official Nifty 500 page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500) |
| Nifty 500 six-month traded-value coverage | about 84.07% | Mar 2026 period end | [Official Nifty 500 page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500) |
| Official reconstitution schedule | semi-annual, last working day of Mar/Sep | current page | [Reconstitution calendar](https://niftyindices.com/resources/index-rebalancing-schedule) |

### Methodology sources

- [Nifty 500 official page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500)
- [Nifty equity-index methodology, March 2026](https://www.niftyindices.com/Methodology/Method_NIFTY_Equity_Indices.pdf)
- [Nifty 500 white paper, October 2025](https://www.niftyindices.com/docs/default-source/indices/nifty-500/nifty-500-whitepaper_2025.pdf?sfvrsn=7b2c6635_4)
- [Nifty Total Market](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-total-market)
- [Nifty Microcap 250](https://niftyindices.com/indices/equity/broad-based-indices/nifty-microcap-250)
- [SEBI recognized stock exchanges](https://www.sebi.gov.in/stock-exchanges.html)
- [SEBI — understanding shares](https://investor.sebi.gov.in/understandings_shares.html)

### Internal product sources

- `data/static/nse500_universe.csv`
- `kite-api/app/insights/breadth.py`
- `kite-dashboard/src/content/insights/learn/pct-above-200dma.ts`
- `kite-dashboard/src/components/insights/tabs.tsx`

Internal implementation is evidence of current Marketworks behavior, not an
authoritative definition of the official Nifty 500.

## Source-use rules

1. Prefer NSE Indices for index definition and methodology.
2. Prefer NSE for NSE listing statistics.
3. Prefer SEBI for recognized-exchange and investor-education context.
4. Date every market-size, constituent, coverage, and turnover statistic.
5. Never copy historical return claims into Module 1; they are irrelevant to
   the universe lesson and could be mistaken for a return promise.
6. If official sources disagree because of dates, show the date difference
   rather than selecting the larger number.
7. Do not describe a current constituent snapshot as historical point-in-time
   membership.
8. If a dated official factsheet's published security count differs from the
   index's design target, preserve the official count and date. Check index
   maintenance notices; do not silently force the count to 500 or invent a
   reason.

## Production status

- Copy/manuscript: drafted.
- Diagrams: specified, not produced.
- Screenshots: specified, not captured.
- Fixture CSVs: specified, not packaged.
- Accessibility descriptions: specified at asset level, final review pending.
