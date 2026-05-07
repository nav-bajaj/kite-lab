# Kite-Lab Task Tracking

This directory contains task tracking files for all Kite-Lab features and enhancements.

## Current Features

### Production Dashboard (Phases 1-6) - COMPLETED

Full-featured web dashboard for managing the Kite-Lab momentum portfolio engine.

- **Documentation**: [dashboard_phases.md](./dashboard_phases.md)
- **Task Files**: `phase1/` through `phase6.1/`
- **Status**: All phases completed

**Key Deliverables**:
- Portfolio view with holdings, P&L, allocation
- Performance metrics with equity curves and benchmarks
- Trade history with search/filter and CSV export
- Weekly rebalance workflow (Thursday preview, Friday orders)
- Admin control panel with job execution and scheduling
- Multi-universe support (NSE 500, Nifty 250, Nifty 100)

---

### Live Portfolio / Open Positions - COMPLETED

Real-time portfolio tracking with live prices from Zerodha API.

- **Documentation**: [live_portfolio/README.md](./live_portfolio/README.md)
- **Design Doc**: [live_portfolio/DESIGN.md](./live_portfolio/DESIGN.md)
- **Status**: All 10 tasks completed

**Key Deliverables**:
- Open Positions page showing current holdings with live prices
- Real-time P&L calculations (total and day)
- Server-Sent Events (SSE) for live price streaming during market hours
- Market status indicator (Open/Closed/Pre-market)
- Fallback to closing prices when market is closed
- Support for all universes

**API Endpoints**:
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/positions` | Positions with live prices and P&L |
| GET | `/api/positions/holdings` | Raw holdings without prices |
| GET | `/api/positions/quotes` | Live quotes only |
| GET | `/api/positions/stream` | SSE for real-time updates |
| GET | `/api/positions/market-status` | Market open/closed status |
| POST | `/api/positions/sync-from-csv` | Sync from portfolio CSV |

---

### Trend Leaders 20 — IN PROGRESS

A standalone trend-following portfolio strategy, designed as a separate subscriber product alongside momentum.

- **Documentation**: [trend_leaders/README.md](./trend_leaders/README.md)
- **Design Doc**: [trend_leaders/DESIGN.md](./trend_leaders/DESIGN.md)
- **Branch**: `trend-leaders-20`
- **Status**: V1 complete — all 5 phases done, strategy improvement in progress

**Phases**:
| Phase | Description | Task File | Status |
|-------|-------------|-----------|--------|
| 1 | Signal generation (eligibility + TQS ranking) | [phase1_signals.md](./trend_leaders/phase1_signals.md) | Done |
| 2 | Backtest engine (dual-frequency rebalance) | [phase2_backtest.md](./trend_leaders/phase2_backtest.md) | Done |
| 3 | Run all 4 backtest variants | [phase3_variants.md](./trend_leaders/phase3_variants.md) | Done |
| 4 | Report generation + momentum comparison | [phase4_reports.md](./trend_leaders/phase4_reports.md) | Done |
| 5 | Orchestrator script | [phase5_orchestrator.md](./trend_leaders/phase5_orchestrator.md) | Done |

**Key Deliverables**:
- Trend Quality Score signal generator (4-component composite)
- Dual-frequency backtest engine (monthly entry + weekly exit)
- 4 strategy variants (base, market filter, monthly-only, persistence-only)
- Performance comparison vs momentum strategy
- HTML reports with equity curves, drawdowns, and correlation analysis

---

## Directory Structure

```
tasks/
├── README.md                    # This file
├── dashboard_phases.md          # Dashboard implementation overview
├── phase1/                      # Foundation (Backend, Auth, Deploy)
├── phase2/                      # Portfolio View
├── phase3/                      # Performance Metrics
├── phase4/                      # Trades & Rebalance
├── phase5/                      # Admin Control Panel
├── phase6/                      # Polish & Production
├── phase6.1/                    # Repository Reconciliation
├── live_portfolio/              # Live Portfolio Feature
│   ├── README.md                # Task breakdown
│   └── DESIGN.md                # Technical design
└── trend_leaders/               # Trend Leaders 20 Strategy
    ├── README.md                # Overview and task index
    ├── DESIGN.md                # Architecture and design decisions
    ├── phase1_signals.md        # Signal generation tasks
    ├── phase2_backtest.md       # Backtest engine tasks
    ├── phase3_variants.md       # Variant execution tasks
    ├── phase4_reports.md        # Report generation tasks
    └── phase5_orchestrator.md   # Orchestrator tasks
```

---

## Production URLs

| Service | URL |
|---------|-----|
| Frontend (Vercel) | https://kite-lab.vercel.app |
| Backend (Railway) | https://kite-lab-production.up.railway.app |
| API Docs | https://kite-lab-production.up.railway.app/docs |

---

*Last updated: May 2026*
