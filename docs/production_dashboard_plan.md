# Kite-Lab Production Dashboard

## Comprehensive Implementation Plan

**Version**: 1.1
**Created**: February 2026
**Updated**: February 9, 2026
**Status**: Planning Phase

### Recent Updates (v1.1)
- Added multi-universe support from day one (NSE 500, Nifty 250, Nifty 100)
- Replaced Job Runner with sleek Admin Control Panel
- Added visual parameter controls (dropdowns, toggles) instead of CLI arguments
- Added Quick Actions cards for common operations
- Added per-universe scheduled jobs and status tracking

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Frontend Design System](#4-frontend-design-system)
5. [Backend API Design](#5-backend-api-design)
6. [Database Schema](#6-database-schema)
7. [Implementation Phases](#7-implementation-phases)
8. [Deployment Strategy](#8-deployment-strategy)
9. [Cost Analysis](#9-cost-analysis)
10. [Security Considerations](#10-security-considerations)
11. [Future Roadmap](#11-future-roadmap)

---

## 1. Executive Summary

### Project Goal
Build a production-grade web dashboard to manage, monitor, and operate the Kite-Lab momentum portfolio engine. The dashboard will provide real-time portfolio visibility, performance analytics, trade management, and automated pipeline execution.

### Key Deliverables
- **Multi-Universe Support**: NSE 500, Nifty 250, Nifty 100 portfolios with unified switching
- **Portfolio Dashboard**: Real-time view of 24 holdings with P&L tracking per universe
- **Performance Analytics**: Equity curves, metrics, benchmark comparison across universes
- **Rebalance Workflow**: Thursday preview, Friday order generation for each universe
- **Trade History**: Searchable, filterable trade records with export
- **Admin Control Panel**: Sleek UI for running pipelines with visual controls (no CLI needed)
- **Scheduled Automation**: Daily data fetch, weekly rebalance per universe

### Supported Universes

| Universe | Stocks | Description | Risk Profile |
|----------|--------|-------------|--------------|
| **NSE 500** | 499 | Full mid+large cap universe | Growth-focused, higher alpha |
| **Nifty 250** | 250 | Large + mid-cap blend | Balanced risk/return |
| **Nifty 100** | 100 | Large-cap only | Conservative, lower drawdown |

### Design Philosophy
- **Modular Development**: Each phase delivers standalone value
- **Simple Deployment**: Vercel + Railway, no complex infrastructure
- **Low Cost**: ~$5/month total operational cost
- **Beautiful UI**: Modern shadcn/ui design with system-adaptive theming

---

## 2. System Architecture

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│                         USER (Web Browser)                                   │
│                              │                                               │
│                              │ HTTPS                                         │
│                              ▼                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     FRONTEND (Vercel - Free Tier)                       │ │
│  │                                                                          │ │
│  │   Next.js 14 (App Router) + shadcn/ui + Tailwind CSS + Recharts        │ │
│  │                                                                          │ │
│  │   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │ │
│  │   │  Portfolio  │ │ Performance │ │  Rebalance  │ │   Admin     │      │ │
│  │   │   - List    │ │  - Metrics  │ │  - Preview  │ │  - Actions  │      │ │
│  │   │   - P&L     │ │  - Charts   │ │  - Orders   │ │  - Jobs     │      │ │
│  │   │   - Alloc   │ │  - Compare  │ │  - History  │ │  - Schedule │      │ │
│  │   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘      │ │
│  │                                                                          │ │
│  │   Global: [Universe Selector: NSE 500 | Nifty 250 | Nifty 100]          │ │
│  │                                                                          │ │
│  │   Auth: NextAuth.js + Google OAuth (Whitelist)                          │ │
│  │   State: SWR (data fetching + caching)                                  │ │
│  │                                                                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│                              │ REST API (JSON)                               │
│                              ▼                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    BACKEND (Railway - $5/month)                         │ │
│  │                                                                          │ │
│  │   Python 3.11 + FastAPI + SQLAlchemy + APScheduler                      │ │
│  │                                                                          │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │ │
│  │   │                        API Layer                                 │   │ │
│  │   │  /api/portfolio  /api/metrics  /api/trades  /api/rebalance      │   │ │
│  │   │  /api/signals    /api/jobs     /api/health  /api/system         │   │ │
│  │   └─────────────────────────────────────────────────────────────────┘   │ │
│  │                              │                                           │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │ │
│  │   │                     Service Layer                                │   │ │
│  │   │  PortfolioService  MetricsService  TradeService  JobService     │   │ │
│  │   │  SignalService     RebalanceService  KiteService                │   │ │
│  │   └─────────────────────────────────────────────────────────────────┘   │ │
│  │                              │                                           │ │
│  │   ┌─────────────────────────────────────────────────────────────────┐   │ │
│  │   │                   Engine (Migrated Scripts)                      │   │ │
│  │   │  run_daily_pipeline.py    build_momentum_signals_flexible.py    │   │ │
│  │   │  run_final_momentum_portfolio.py    backtest_momentum.py        │   │ │
│  │   │  fetch_nse500_history.py  compute_benchmark.py                  │   │ │
│  │   └─────────────────────────────────────────────────────────────────┘   │ │
│  │                              │                                           │ │
│  │   ┌──────────────────────┐   │   ┌──────────────────────┐              │ │
│  │   │  Scheduler           │   │   │  Job Queue           │              │ │
│  │   │  APScheduler         │   │   │  Background Tasks    │              │ │
│  │   │  - Daily: 6:30 AM    │   │   │  - Async execution   │              │ │
│  │   │  - Weekly: Thu/Fri   │   │   │  - Log streaming     │              │ │
│  │   └──────────────────────┘   │   └──────────────────────┘              │ │
│  │                              │                                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                              │                                               │
│           ┌──────────────────┼──────────────────┐                           │
│           ▼                  ▼                  ▼                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │   PostgreSQL    │ │  File Storage   │ │   Zerodha Kite  │               │
│  │   (Railway)     │ │  (Railway Vol)  │ │   (External)    │               │
│  │                 │ │                 │ │                 │               │
│  │  - trades       │ │  - nse500_data/ │ │  - Price data   │               │
│  │  - equity_curve │ │  - indices/     │ │  - Instruments  │               │
│  │  - holdings     │ │  - signals/     │ │  - Orders       │               │
│  │  - metrics      │ │  - reports/     │ │                 │               │
│  │  - jobs         │ │                 │ │                 │               │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘               │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. DAILY PIPELINE (6:30 AM IST)
   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
   │  Kite   │────▶│  Fetch  │────▶│  Build  │────▶│  Store  │
   │  API    │     │  Prices │     │ Signals │     │  CSV/DB │
   └─────────┘     └─────────┘     └─────────┘     └─────────┘

2. WEEKLY REBALANCE (Thursday/Friday)
   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
   │ Signals │────▶│ Compare │────▶│ Generate│────▶│  Store  │
   │  CSV    │     │Holdings │     │ Changes │     │ Preview │
   └─────────┘     └─────────┘     └─────────┘     └─────────┘
                                         │
                        Friday ──────────┼─────────┐
                                         ▼         ▼
                                   ┌─────────┐ ┌─────────┐
                                   │ Orders  │ │ Execute │
                                   │  File   │ │ (Manual)│
                                   └─────────┘ └─────────┘

3. DASHBOARD DATA FLOW
   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
   │  User   │────▶│ Next.js │────▶│ FastAPI │────▶│  Data   │
   │ Browser │◀────│ (SWR)   │◀────│  JSON   │◀────│ Sources │
   └─────────┘     └─────────┘     └─────────┘     └─────────┘
```

---

## 3. Technology Stack

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 14.x | React framework with App Router, SSR |
| **React** | 18.x | UI component library |
| **TypeScript** | 5.x | Type safety |
| **Tailwind CSS** | 3.x | Utility-first styling |
| **shadcn/ui** | latest | Component library (Radix-based) |
| **Recharts** | 2.x | Charting library |
| **SWR** | 2.x | Data fetching and caching |
| **NextAuth.js** | 4.x | Authentication |
| **Lucide React** | latest | Icon library |
| **date-fns** | 2.x | Date formatting |

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.11 | Runtime |
| **FastAPI** | 0.109+ | Web framework |
| **SQLAlchemy** | 2.0 | ORM |
| **Alembic** | 1.13+ | Database migrations |
| **Pydantic** | 2.x | Data validation |
| **APScheduler** | 3.x | Job scheduling |
| **uvicorn** | 0.27+ | ASGI server |
| **httpx** | 0.26+ | HTTP client |
| **pandas** | 2.x | Data processing |
| **kiteconnect** | 5.x | Zerodha API |

### Infrastructure

| Service | Tier | Purpose |
|---------|------|---------|
| **Vercel** | Hobby (Free) | Frontend hosting |
| **Railway** | Starter ($5/mo) | Backend + PostgreSQL |
| **GitHub** | Free | Source control |
| **Google Cloud** | Free | OAuth provider |

---

## 4. Frontend Design System

### Design Reference

**Primary Reference**: [Next shadcn Admin Dashboard](https://next-shadcn-admin-dashboard.vercel.app/dashboard/default)

### Visual Design Principles

#### Layout Structure
- **Sidebar-based layout** with collapsible navigation
- **Responsive grid system** using CSS container queries
- **Centered content** with max-width constraints (1400px)
- **Sticky navbar** with breadcrumb navigation

#### Color Scheme (System Adaptive)

```css
/* Light Mode */
--background: 0 0% 100%;
--foreground: 222.2 84% 4.9%;
--card: 0 0% 100%;
--card-foreground: 222.2 84% 4.9%;
--primary: 222.2 47.4% 11.2%;
--primary-foreground: 210 40% 98%;
--secondary: 210 40% 96.1%;
--muted: 210 40% 96.1%;
--accent: 210 40% 96.1%;
--destructive: 0 84.2% 60.2%;
--border: 214.3 31.8% 91.4%;

/* Dark Mode */
--background: 222.2 84% 4.9%;
--foreground: 210 40% 98%;
--card: 222.2 84% 4.9%;
--card-foreground: 210 40% 98%;
--primary: 210 40% 98%;
--primary-foreground: 222.2 47.4% 11.2%;
--secondary: 217.2 32.6% 17.5%;
--muted: 217.2 32.6% 17.5%;
--accent: 217.2 32.6% 17.5%;
--destructive: 0 62.8% 30.6%;
--border: 217.2 32.6% 17.5%;
```

#### Typography
- **Font Family**: Inter (primary), system fallbacks
- **Headings**: Semi-bold, tracking-tight
- **Body**: Regular weight, 16px base
- **Data/Numbers**: Tabular numerals for alignment

#### Card Styling
```css
/* Gradient background treatment */
.card {
  @apply rounded-xl border bg-card text-card-foreground shadow-sm;
  background: linear-gradient(to top, hsl(var(--primary) / 0.05), hsl(var(--card)));
}
```

#### Component Patterns

**Metric Cards**
```
┌─────────────────────────────────┐
│  Portfolio Value          ↑12% │
│  ₹12,345,678                   │
│  +₹1,234,567 today             │
└─────────────────────────────────┘
```

**Data Tables**
- Sortable columns with visual indicators
- Row selection with checkboxes
- Pagination with rows-per-page selector
- Search/filter inputs

**Charts**
- Area charts for equity curves (gradient fill)
- Bar charts for monthly returns
- Pie/donut for allocation
- Consistent color palette across charts

### Page Layouts

#### 1. Portfolio Overview (Default Dashboard)
```
┌──────────────────────────────────────────────────────────────────┐
│ [Logo]  Dashboard > Portfolio                    [Search] [User] │
├──────────┬───────────────────────────────────────────────────────┤
│          │                                                       │
│ Dashboard│  ┌─────────────────────────────────────────────────┐  │
│ Portfolio│  │ Universe: [NSE 500 ▼] [Nifty 250] [Nifty 100]   │  │
│ Perform. │  └─────────────────────────────────────────────────┘  │
│ Rebalance│                                                       │
│ Trades   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ Admin    │  │Portfolio │ │  Daily   │ │  Total   │ │  Cash    │ │
│          │  │  Value   │ │   P&L    │ │  Return  │ │ Balance  │ │
│ ──────── │  │₹12.3M ↑ │ │+₹45K ↑  │ │ +1,234%  │ │  ₹0.00   │ │
│ Settings │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│          │                                                       │
│          │  ┌────────────────────────────────────────────────┐  │
│ ──────── │  │           Holdings Table (24 rows)             │  │
│ Settings │  │  Symbol | Shares | Avg Cost | Price | P&L | %  │  │
│          │  │  HDFC   | 100    | ₹1,500   |₹1,600 |+6.7%|4.2%│  │
│          │  │  ...    | ...    | ...      | ...   | ... | ...│  │
│          │  └────────────────────────────────────────────────┘  │
│          │                                                       │
│          │  ┌─────────────────────┐ ┌─────────────────────────┐ │
│          │  │ Allocation by Stock │ │ Allocation by Sector    │ │
│          │  │     [Pie Chart]     │ │     [Pie Chart]         │ │
│          │  └─────────────────────┘ └─────────────────────────┘ │
│          │                                                       │
└──────────┴───────────────────────────────────────────────────────┘
```

#### 2. Performance Page
```
┌──────────────────────────────────────────────────────────────────┐
│                     Performance Analytics                         │
├──────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │   CAGR   │ │  Sharpe  │ │  Max DD  │ │ Turnover │            │
│  │  56.3%   │ │   1.87   │ │ -29.6%   │ │  97% ann │            │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Equity Curve                             │  │
│  │  [Area Chart: Portfolio vs Benchmark, 2020-2026]           │  │
│  │                                                             │  │
│  │  14M ─┤                                            ╭───     │  │
│  │  12M ─┤                                        ╭───╯        │  │
│  │  10M ─┤                                    ╭───╯            │  │
│  │   8M ─┤                               ╭────╯                │  │
│  │   6M ─┤                          ╭────╯                     │  │
│  │   4M ─┤                    ╭─────╯                          │  │
│  │   2M ─┤           ╭────────╯                                │  │
│  │   1M ─┼───────────╯                                         │  │
│  │       └──────┬──────┬──────┬──────┬──────┬──────┬───────   │  │
│  │           2020   2021   2022   2023   2024   2025   2026    │  │
│  │                                                             │  │
│  │  [Toggle: Portfolio ● | Benchmark ○ | Drawdown ○]          │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────┐ ┌───────────────────────────────┐ │
│  │ Monthly Returns Heatmap   │ │ Drawdown Analysis             │ │
│  │ [Calendar heatmap]        │ │ [Drawdown chart]              │ │
│  └───────────────────────────┘ └───────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 3. Rebalance Page
```
┌──────────────────────────────────────────────────────────────────┐
│                     Weekly Rebalance                              │
├──────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Status: Preview Ready (Thursday)                          │  │
│  │  Signal Date: 2026-02-06  │  Order Date: 2026-02-07       │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─────────────────────┐ ┌─────────────────────┐                 │
│  │      ADDITIONS      │ │      REMOVALS       │                 │
│  │  ┌───────────────┐  │ │  ┌───────────────┐  │                 │
│  │  │ MRPL      #15 │  │ │  │ ABCAPITAL #25 │  │                 │
│  │  │ UNIONBANK #18 │  │ │  │ AUBANK    #27 │  │                 │
│  │  │ CHENNPETRO#20 │  │ │  │ CUB       #28 │  │                 │
│  │  └───────────────┘  │ │  └───────────────┘  │                 │
│  └─────────────────────┘ └─────────────────────┘                 │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     Order File (Friday)                    │  │
│  │  Action | Symbol    | Current | Target | Shares | Est Cost │  │
│  │  SELL   | ABCAPITAL | 4.2%    | 0%     | 1,482  | ₹510K   │  │
│  │  BUY    | MRPL      | 0%      | 4.2%   | 3,646  | ₹672K   │  │
│  │  ...                                                       │  │
│  │                                        [Download CSV]      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   Rebalance History                        │  │
│  │  Date       | Adds | Drops | Turnover | Status            │  │
│  │  2026-02-07 |   5  |   6   |  54.2%   | Pending           │  │
│  │  2026-01-31 |   2  |   1   |  12.3%   | Executed          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

#### 4. Trades Page
```
┌──────────────────────────────────────────────────────────────────┐
│                      Trade History                                │
├──────────────────────────────────────────────────────────────────┤
│  [Search: Symbol]  [Filter: Side ▼]  [Date Range: ▼]  [Export]   │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Date       | Symbol | Side | Shares  | Price  | Notional   │  │
│  │ 2026-02-06 | MRPL   | BUY  | 3,646   | ₹184.4 | ₹672,337   │  │
│  │ 2026-02-06 | ABCAP  | SELL | 1,482   | ₹344.1 | ₹509,985   │  │
│  │ ...                                                         │  │
│  │                                                             │  │
│  │ Showing 1-50 of 2,094 trades          [< 1 2 3 ... 42 >]   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─────────────────────┐ ┌─────────────────────────────────────┐ │
│  │ Trade Summary       │ │ Trade Distribution                  │ │
│  │ Total: 2,094        │ │ [Bar chart by month]                │ │
│  │ Buys: 1,059         │ │                                     │ │
│  │ Sells: 1,035        │ │                                     │ │
│  │ Hit Rate: 50.1%     │ │                                     │ │
│  └─────────────────────┘ └─────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

#### 5. Admin Control Panel
```
┌──────────────────────────────────────────────────────────────────┐
│                     Admin Control Panel                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  QUICK ACTIONS                                              │  │
│  │                                                             │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                  │  │
│  │  │  🔄 Daily       │  │  📊 Generate    │                  │  │
│  │  │   Pipeline      │  │   Portfolio     │                  │  │
│  │  │                 │  │                 │                  │  │
│  │  │  Fetch data &   │  │  Build signals  │                  │  │
│  │  │  build signals  │  │  & run backtest │                  │  │
│  │  │                 │  │                 │                  │  │
│  │  │  [▶ Run Now]    │  │  [▶ Run Now]    │                  │  │
│  │  └─────────────────┘  └─────────────────┘                  │  │
│  │                                                             │  │
│  │  ┌─────────────────┐  ┌─────────────────┐                  │  │
│  │  │  🔑 Kite        │  │  💾 Backup      │                  │  │
│  │  │   Login         │  │   Data          │                  │  │
│  │  │                 │  │                 │                  │  │
│  │  │  Refresh API    │  │  Sync to        │                  │  │
│  │  │  access token   │  │  backup folder  │                  │  │
│  │  │                 │  │                 │                  │  │
│  │  │  [▶ Login]      │  │  [▶ Backup]     │                  │  │
│  │  └─────────────────┘  └─────────────────┘                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  PORTFOLIO GENERATOR                                        │  │
│  │                                                             │  │
│  │  Universe         Lookback        Rebalance      Top-N     │  │
│  │  ┌───────────┐   ┌───────────┐   ┌───────────┐  ┌───────┐  │  │
│  │  │ NSE 500 ▼ │   │ 6 months▼ │   │ Weekly  ▼ │  │ 24  ▼ │  │  │
│  │  └───────────┘   └───────────┘   └───────────┘  └───────┘  │  │
│  │                                                             │  │
│  │  Vol Floor        Min Hold Days   With Login               │  │
│  │  ┌───────────┐   ┌───────────┐   ┌───────────────────────┐ │  │
│  │  │ 0.05    ▼ │   │ 8 days  ▼ │   │ ☑ Include Kite login  │ │  │
│  │  └───────────┘   └───────────┘   └───────────────────────┘ │  │
│  │                                                             │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │            ▶  Generate Portfolio                     │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  ADVANCED COMMANDS                                          │  │
│  │                                                             │  │
│  │  Command                        Options                     │  │
│  │  ┌────────────────────────┐    ┌────────────────────────┐  │  │
│  │  │ fetch_nse500_history ▼ │    │ --days 30            ▼ │  │  │
│  │  └────────────────────────┘    └────────────────────────┘  │  │
│  │                                                             │  │
│  │  ┌──────────────────────┐                                  │  │
│  │  │  ▶  Execute Command  │                                  │  │
│  │  └──────────────────────┘                                  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  RECENT JOBS                                    [View All]  │  │
│  │                                                             │  │
│  │  ● daily_pipeline     Running    Started 2 min ago    [⋮]  │  │
│  │  ✓ final_portfolio    Completed  1 hour ago  NSE 500  [⋮]  │  │
│  │  ✓ final_portfolio    Completed  1 hour ago  Nifty100 [⋮]  │  │
│  │  ✗ fetch_prices       Failed     Token expired        [⋮]  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  LOG OUTPUT                               [Clear] [⤢ Full] │  │
│  │  ┌────────────────────────────────────────────────────────┐│  │
│  │  │ [14:03:22] Starting daily pipeline...                  ││  │
│  │  │ [14:03:23] Logging in to Kite API...                   ││  │
│  │  │ [14:03:25] ✓ Login successful                          ││  │
│  │  │ [14:03:26] Fetching NSE 500 prices (499 stocks)...     ││  │
│  │  │ [14:05:45] ✓ Fetched 499/499 stocks                    ││  │
│  │  │ [14:05:46] Building momentum signals...                ││  │
│  │  │ [14:05:52] ✓ Signals built for 2026-02-09              ││  │
│  │  │ ▌                                                      ││  │
│  │  └────────────────────────────────────────────────────────┘│  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  SCHEDULED JOBS                                             │  │
│  │                                                             │  │
│  │  Job                    Schedule           Next Run   Status│  │
│  │  ─────────────────────────────────────────────────────────  │  │
│  │  Daily Pipeline         6:30 AM (Mon-Fri)  Tomorrow   [●]  │  │
│  │  NSE 500 Rebalance      Thu 6:00 PM        Feb 13     [●]  │  │
│  │  Nifty 250 Rebalance    Thu 6:15 PM        Feb 13     [●]  │  │
│  │  Nifty 100 Rebalance    Thu 6:30 PM        Feb 13     [●]  │  │
│  │  Data Backup            Sat 2:00 AM        Feb 15     [●]  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  SYSTEM STATUS                                              │  │
│  │                                                             │  │
│  │  Kite API Token    ● Valid until 6:00 AM tomorrow          │  │
│  │  Last Data Fetch   ● 2026-02-09 06:32 AM (499 stocks)      │  │
│  │  Last Signals      ● 2026-02-09 06:35 AM                   │  │
│  │  Database          ● Connected (Railway PostgreSQL)        │  │
│  │  Disk Usage        ● 342 MB / 1 GB                         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Component Library

Using shadcn/ui components with custom styling:

| Component | Usage |
|-----------|-------|
| `Card` | Metric cards, section containers |
| `Table` | Holdings, trades, history |
| `Button` | Actions, navigation |
| `DropdownMenu` | Command selector, filters |
| `Badge` | Status indicators (Running, Completed, Failed) |
| `Tabs` | Page sections, chart toggles |
| `ToggleGroup` | Universe selector (NSE 500 / Nifty 250 / Nifty 100) |
| `Select` | Parameter dropdowns (lookback, rebalance, top-n) |
| `Switch` | Toggle options (with-login, enabled/disabled) |
| `Dialog` | Trade details, confirmations |
| `Sheet` | Mobile sidebar |
| `Skeleton` | Loading states |
| `Toast` | Notifications |
| `Command` | Search palette (⌘K) |
| `Separator` | Section dividers |
| `ScrollArea` | Log viewer scroll container |

### Custom Components

| Component | Description |
|-----------|-------------|
| `UniverseSelector` | Toggle group for switching between NSE 500, Nifty 250, Nifty 100 |
| `ActionCard` | Stylized button card with icon, title, description, and action |
| `ParameterForm` | Form with dropdowns for portfolio generation parameters |
| `JobStatusBadge` | Color-coded badge (running=blue, completed=green, failed=red) |
| `LogViewer` | Real-time log display with auto-scroll and formatting |
| `SystemStatusCard` | Health indicator with colored dots |

---

## 5. Backend API Design

### Base URL
```
Production: https://kite-api.railway.app/api
Development: http://localhost:8000/api
```

### Authentication
All endpoints (except `/health`) require Bearer token:
```
Authorization: Bearer <jwt_token>
```

### Endpoints

#### Portfolio Endpoints

```yaml
GET /api/portfolio
  description: Current portfolio overview
  query:
    universe: string (default: "nse500")
  response:
    total_value: number
    cash: number
    invested: number
    daily_pnl: number
    daily_pnl_pct: number
    total_return: number
    total_return_pct: number
    holdings_count: number
    as_of_date: string (ISO date)

GET /api/portfolio/holdings
  description: Detailed holdings with P&L
  query:
    universe: string (default: "nse500")
  response:
    holdings: array
      - symbol: string
        shares: number
        avg_cost: number
        current_price: number
        notional: number
        pnl: number
        pnl_pct: number
        weight: number
        entry_date: string
        holding_days: number
        rank: number
    summary:
      total_pnl: number
      winners: number
      losers: number

GET /api/portfolio/allocation
  description: Allocation breakdown
  query:
    universe: string
    group_by: string ("symbol" | "sector" | "industry")
  response:
    allocations: array
      - name: string
        value: number
        percentage: number
```

#### Metrics Endpoints

```yaml
GET /api/metrics
  description: Latest performance metrics
  query:
    universe: string
  response:
    period:
      start: string
      end: string
      days: number
    returns:
      total_return: number
      cagr: number
      mtd: number
      ytd: number
    risk:
      max_drawdown: number
      max_dd_duration: number
      volatility: number
      sharpe_ratio: number
      sortino_ratio: number
      calmar_ratio: number
    activity:
      total_trades: number
      avg_turnover: number
      annualized_turnover: number
      avg_holding_days: number
      hit_rate: number

GET /api/metrics/equity-curve
  description: Full equity curve data
  query:
    universe: string
    start: string (ISO date, optional)
    end: string (ISO date, optional)
  response:
    data: array
      - date: string
        portfolio_value: number
        benchmark_value: number
        drawdown: number

GET /api/metrics/monthly-returns
  description: Monthly return matrix
  query:
    universe: string
  response:
    years: array of numbers
    data: array
      - year: number
        months: array of (number | null)
        ytd: number
```

#### Trades Endpoints

```yaml
GET /api/trades
  description: Paginated trade history
  query:
    universe: string
    symbol: string (optional)
    side: string ("BUY" | "SELL", optional)
    start: string (ISO date, optional)
    end: string (ISO date, optional)
    limit: number (default: 50, max: 500)
    offset: number (default: 0)
  response:
    trades: array
      - id: number
        date: string
        symbol: string
        side: string
        shares: number
        price: number
        notional: number
        slippage: number
    total_count: number
    limit: number
    offset: number

GET /api/trades/export
  description: Export trades as CSV
  query:
    universe: string
    start: string
    end: string
  response: CSV file download

GET /api/trades/summary
  description: Trade statistics
  query:
    universe: string
    period: string ("mtd" | "ytd" | "all")
  response:
    total_trades: number
    buys: number
    sells: number
    total_notional: number
    avg_trade_size: number
    hit_rate: number
```

#### Rebalance Endpoints

```yaml
GET /api/rebalance/status
  description: Current rebalance status
  query:
    universe: string
  response:
    status: string ("pending" | "preview" | "ready" | "executed")
    signal_date: string
    order_date: string
    preview_available: boolean
    orders_available: boolean

GET /api/rebalance/preview
  description: Thursday preview (changes)
  query:
    universe: string
  response:
    signal_date: string
    additions: array
      - symbol: string
        rank: number
        score: number
    removals: array
      - symbol: string
        prev_rank: number
        reason: string
    rank_changes: array
      - symbol: string
        old_rank: number
        new_rank: number

GET /api/rebalance/orders
  description: Friday order file
  query:
    universe: string
  response:
    order_date: string
    orders: array
      - action: string ("BUY" | "SELL")
        symbol: string
        current_weight: number
        target_weight: number
        shares: number
        est_notional: number

GET /api/rebalance/history
  description: Past rebalances
  query:
    universe: string
    limit: number (default: 10)
  response:
    rebalances: array
      - signal_date: string
        order_date: string
        status: string
        additions: number
        removals: number
        turnover: number
```

#### Signals Endpoints

```yaml
GET /api/signals/latest
  description: Latest signal rankings
  query:
    universe: string
    top_n: number (default: 24)
  response:
    signal_date: string
    signals: array
      - rank: number
        symbol: string
        score: number
        momentum_6m: number
        volatility: number

GET /api/signals/history
  description: Signal history for a symbol
  query:
    symbol: string
    days: number (default: 90)
  response:
    symbol: string
    history: array
      - date: string
        rank: number (or null if not in top-N)
        score: number
```

#### Admin/Jobs Endpoints

```yaml
GET /api/admin/commands
  description: Available commands with their parameters
  response:
    commands: array
      - name: string
        label: string
        description: string
        category: string ("quick_action" | "portfolio" | "advanced")
        parameters: array
          - name: string
            type: string ("select" | "number" | "boolean")
            options: array (for select type)
            default: any

POST /api/admin/run
  description: Start a job with visual parameters
  body:
    command: string
    parameters:
      universe: string ("nse500" | "nifty250" | "nifty100")
      lookback_months: number (6 | 9 | 12)
      rebalance_weeks: number (1 | 2)
      top_n: number (default: 24)
      vol_floor: number (default: 0.05)
      min_hold_days: number (default: 8)
      with_login: boolean (default: false)
  response:
    job_id: string
    status: string
    created_at: string

GET /api/jobs
  description: List recent jobs
  query:
    limit: number (default: 10)
    status: string (optional)
    universe: string (optional, filter by universe)
  response:
    jobs: array
      - id: string
        command: string
        universe: string
        status: string
        started_at: string
        ended_at: string
        duration_seconds: number

GET /api/jobs/{job_id}
  description: Job details
  response:
    id: string
    command: string
    parameters: object
    universe: string
    status: string
    started_at: string
    ended_at: string
    error_message: string (if failed)

GET /api/jobs/{job_id}/logs
  description: Job logs (supports SSE streaming)
  query:
    stream: boolean (default: false)
  response:
    content: string (full log)
    # or SSE stream if stream=true

DELETE /api/jobs/{job_id}
  description: Cancel running job
  response:
    success: boolean

GET /api/admin/schedules
  description: List all scheduled jobs
  response:
    schedules: array
      - id: string
        name: string
        universe: string (or "all")
        cron: string
        next_run: string
        enabled: boolean

PUT /api/admin/schedules/{id}
  description: Enable/disable a scheduled job
  body:
    enabled: boolean
  response:
    success: boolean
```

#### System Endpoints

```yaml
GET /api/health
  description: Health check (no auth required)
  response:
    status: string ("ok" | "degraded" | "down")
    database: string ("connected" | "error")
    timestamp: string

GET /api/system/status
  description: System status overview
  response:
    kite_token_valid: boolean
    kite_token_expires: string
    last_data_fetch: string
    database_status: string ("connected" | "error")
    disk_usage:
      used_mb: number
      total_mb: number
    universes:
      - name: string ("nse500" | "nifty250" | "nifty100")
        last_signal_build: string
        last_backtest: string
        holdings_count: number
    scheduled_jobs:
      - name: string
        universe: string
        next_run: string
        enabled: boolean
```

---

## 6. Database Schema

### Entity Relationship Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   trades    │     │ equity_curve│     │  holdings   │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ id (PK)     │     │ id (PK)     │     │ id (PK)     │
│ universe    │     │ universe    │     │ universe    │
│ trade_date  │     │ date        │     │ snapshot_dt │
│ symbol      │     │ port_value  │     │ symbol      │
│ side        │     │ cash        │     │ rank        │
│ shares      │     │ invested    │     │ shares      │
│ price       │     │ benchmark   │     │ avg_cost    │
│ notional    │     │ drawdown    │     │ entry_date  │
│ slippage    │     │ exposure    │     │ pnl_pct     │
│ cash_after  │     │ created_at  │     │ notional    │
│ created_at  │     └─────────────┘     │ created_at  │
└─────────────┘                         └─────────────┘
       │
       │ (aggregated from)
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   metrics   │     │ rebalances  │     │    jobs     │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ id (PK)     │     │ id (PK)     │     │ id (PK)     │
│ universe    │     │ universe    │     │ command     │
│ computed_dt │     │ signal_date │     │ args        │
│ cagr        │     │ order_date  │     │ status      │
│ max_dd      │     │ status      │     │ started_at  │
│ sharpe      │     │ additions   │     │ ended_at    │
│ turnover    │     │ removals    │     │ log_path    │
│ hit_rate    │     │ orders_json │     │ error_msg   │
│ ...         │     │ created_at  │     │ created_at  │
└─────────────┘     └─────────────┘     └─────────────┘

┌─────────────┐     ┌─────────────┐
│   signals   │     │allowed_users│
├─────────────┤     ├─────────────┤
│ id (PK)     │     │ id (PK)     │
│ universe    │     │ email       │
│ signal_date │     │ is_active   │
│ rank        │     │ created_at  │
│ symbol      │     └─────────────┘
│ score       │
│ mom_6m      │
│ vol_6m      │
│ created_at  │
└─────────────┘
```

### Table Definitions

```sql
-- PostgreSQL Schema

-- Allowed users for SSO whitelist
CREATE TABLE allowed_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Trade history
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(20) NOT NULL DEFAULT 'nse500',
    trade_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    shares DECIMAL(18,6) NOT NULL,
    price DECIMAL(18,4) NOT NULL,
    notional DECIMAL(18,2) NOT NULL,
    slippage DECIMAL(18,4),
    cash_after DECIMAL(18,2),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(universe, trade_date, symbol, side)
);

-- Daily equity curve
CREATE TABLE equity_curve (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(20) NOT NULL DEFAULT 'nse500',
    date DATE NOT NULL,
    portfolio_value DECIMAL(18,2) NOT NULL,
    cash DECIMAL(18,2),
    invested DECIMAL(18,2),
    benchmark DECIMAL(18,2),
    drawdown DECIMAL(10,6),
    exposure DECIMAL(5,4) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(universe, date)
);

-- Current holdings snapshots
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(20) NOT NULL DEFAULT 'nse500',
    snapshot_date DATE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    rank INTEGER,
    shares DECIMAL(18,6),
    avg_cost DECIMAL(18,4),
    entry_date DATE,
    entry_rank INTEGER,
    holding_days INTEGER,
    last_price DECIMAL(18,4),
    pnl_pct DECIMAL(10,6),
    notional DECIMAL(18,2),
    contribution_pct DECIMAL(10,6),
    sector VARCHAR(100),
    industry VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(universe, snapshot_date, symbol)
);

-- Performance metrics
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(20) NOT NULL DEFAULT 'nse500',
    computed_date DATE NOT NULL,
    start_date DATE,
    end_date DATE,
    total_return DECIMAL(18,6),
    cagr DECIMAL(10,6),
    max_drawdown DECIMAL(10,6),
    max_drawdown_duration INTEGER,
    volatility DECIMAL(10,6),
    sharpe_ratio DECIMAL(10,4),
    sortino_ratio DECIMAL(10,4),
    calmar_ratio DECIMAL(10,4),
    avg_turnover_pct DECIMAL(10,6),
    annualized_turnover DECIMAL(10,6),
    hit_rate DECIMAL(10,6),
    avg_holding_days DECIMAL(10,2),
    trades_total INTEGER,
    buys INTEGER,
    sells INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(universe, computed_date)
);

-- Rebalance events
CREATE TABLE rebalances (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(20) NOT NULL DEFAULT 'nse500',
    signal_date DATE NOT NULL,
    order_date DATE,
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'preview', 'ready', 'executed')),
    additions JSONB,
    removals JSONB,
    rank_changes JSONB,
    orders_json JSONB,
    turnover_pct DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(universe, signal_date)
);

-- Signal rankings
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    universe VARCHAR(20) NOT NULL DEFAULT 'nse500',
    signal_date DATE NOT NULL,
    rank INTEGER NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    score DECIMAL(18,6),
    score_6m DECIMAL(18,6),
    mom_6m DECIMAL(18,6),
    vol_6m DECIMAL(18,6),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(universe, signal_date, symbol)
);

-- Job execution history
CREATE TABLE jobs (
    id VARCHAR(32) PRIMARY KEY,
    command VARCHAR(100) NOT NULL,
    label VARCHAR(255),
    args JSONB,
    status VARCHAR(50) DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    log_path VARCHAR(500),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_trades_date ON trades(trade_date DESC);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_universe_date ON trades(universe, trade_date DESC);

CREATE INDEX idx_equity_date ON equity_curve(date DESC);
CREATE INDEX idx_equity_universe_date ON equity_curve(universe, date DESC);

CREATE INDEX idx_holdings_date ON holdings(snapshot_date DESC);
CREATE INDEX idx_holdings_universe_date ON holdings(universe, snapshot_date DESC);

CREATE INDEX idx_signals_date ON signals(signal_date DESC);
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_universe_date ON signals(universe, signal_date DESC);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);

CREATE INDEX idx_rebalances_date ON rebalances(signal_date DESC);
```

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1-2)

#### Objectives
- Set up project infrastructure
- Implement authentication
- Deploy basic shells to Vercel/Railway
- Multi-universe support from day one (NSE 500, Nifty 250, Nifty 100)

#### Backend Tasks

| Task | Description | Files |
|------|-------------|-------|
| Project setup | Initialize FastAPI project | `kite-api/app/main.py`, `requirements.txt` |
| Database setup | SQLAlchemy + Alembic | `app/models/database.py`, `alembic/` |
| Models | Create all SQLAlchemy models (with universe column) | `app/models/*.py` |
| Universe config | Define universe constants and defaults | `app/config.py` |
| Migrations | Initial migration | `alembic/versions/001_initial.py` |
| Config | Environment variables | `app/config.py`, `.env` |
| Health endpoint | `/api/health` | `app/api/health.py` |
| Auth middleware | JWT validation | `app/auth.py` |
| Docker | Container configuration | `Dockerfile`, `railway.toml` |
| Data pipeline | Migrate from kite-lab | `app/engine/data_pipeline/` |

#### Frontend Tasks

| Task | Description | Files |
|------|-------------|-------|
| Project setup | Next.js + TypeScript | `kite-dashboard/`, `package.json` |
| Tailwind | Configure with shadcn | `tailwind.config.js`, `globals.css` |
| shadcn/ui | Install components | `components/ui/` |
| NextAuth | Google OAuth | `app/api/auth/[...nextauth]/route.ts` |
| Layout | Dashboard shell | `app/(dashboard)/layout.tsx` |
| Sidebar | Navigation component | `components/shared/sidebar.tsx` |
| Universe selector | Toggle group (NSE 500/Nifty 250/Nifty 100) | `components/shared/universe-selector.tsx` |
| Universe context | React context for selected universe | `lib/universe-context.tsx` |
| API client | Fetch wrapper with universe param | `lib/api-client.ts` |
| Types | TypeScript interfaces | `lib/types.ts` |
| Protected routes | Auth middleware | `middleware.ts` |

#### Universe Configuration

```typescript
// lib/universes.ts
export const UNIVERSES = {
  nse500: {
    id: 'nse500',
    name: 'NSE 500',
    description: 'Full mid+large cap universe',
    stocks: 499,
    riskProfile: 'Growth-focused',
  },
  nifty250: {
    id: 'nifty250',
    name: 'Nifty 250',
    description: 'Large + mid-cap blend',
    stocks: 250,
    riskProfile: 'Balanced',
  },
  nifty100: {
    id: 'nifty100',
    name: 'Nifty 100',
    description: 'Large-cap only',
    stocks: 100,
    riskProfile: 'Conservative',
  },
} as const;

export type UniverseId = keyof typeof UNIVERSES;
```

#### Deliverables
- [ ] Login with Google OAuth works
- [ ] Empty dashboard shell deployed
- [ ] Universe selector visible in header/sidebar
- [ ] Health endpoint returns OK
- [ ] Database tables created with universe column

---

### Phase 2: Portfolio View (Week 3-4)

#### Objectives
- Display current holdings for selected universe
- Show portfolio value and P&L per universe
- Allocation visualization
- Seamless universe switching

#### Backend Tasks

| Task | Description | Endpoint |
|------|-------------|----------|
| Portfolio service | Read CSVs, calculate P&L per universe | `app/services/portfolio_service.py` |
| Portfolio endpoints | REST API with universe param | `GET /api/portfolio?universe=nse500` |
| Holdings endpoint | Per-universe holdings | `GET /api/portfolio/holdings?universe=nse500` |
| Allocation endpoint | Group by symbol/sector | `GET /api/portfolio/allocation` |
| CSV sync | Import data for all 3 universes | `app/services/sync_service.py` |
| Price service | Current prices lookup | `app/services/price_service.py` |

#### Frontend Tasks

| Task | Description | Component |
|------|-------------|-----------|
| Portfolio page | Main layout with universe header | `app/(dashboard)/page.tsx` |
| Universe header | Shows selected universe info | `components/portfolio/universe-header.tsx` |
| Value cards | Portfolio metrics (universe-aware) | `components/portfolio/value-cards.tsx` |
| Holdings table | Sortable, styled | `components/portfolio/holdings-table.tsx` |
| P&L display | Color-coded | `components/portfolio/pnl-cell.tsx` |
| Allocation chart | Pie/donut | `components/portfolio/allocation-chart.tsx` |
| usePortfolio hook | SWR with universe param | `hooks/use-portfolio.ts` |
| Loading states | Skeletons | `components/portfolio/loading.tsx` |

#### Deliverables
- [ ] See all 24 holdings in table for selected universe
- [ ] Portfolio value card with daily P&L
- [ ] Allocation pie chart
- [ ] Auto-refresh every 5 minutes
- [ ] Instant switching between NSE 500, Nifty 250, Nifty 100

---

### Phase 3: Performance Metrics (Week 5-6)

#### Objectives
- Historical equity curve per universe
- Performance metrics dashboard
- Benchmark comparison
- Universe-specific metrics (different expected returns/risk)

#### Backend Tasks

| Task | Description | Endpoint |
|------|-------------|----------|
| Metrics service | Calculate from equity CSV per universe | `app/services/metrics_service.py` |
| Metrics endpoints | REST API with universe param | `GET /api/metrics?universe=nse500` |
| Equity curve | Per-universe historical data | `GET /api/metrics/equity-curve?universe=nse500` |
| Monthly returns | Matrix calculation | `GET /api/metrics/monthly-returns` |
| Equity sync | Import historical data for all universes | Part of sync_service |

#### Frontend Tasks

| Task | Description | Component |
|------|-------------|-----------|
| Performance page | Layout with universe context | `app/(dashboard)/performance/page.tsx` |
| Universe info | Shows expected metrics for universe | `components/performance/universe-info.tsx` |
| Metrics grid | CAGR, Sharpe, etc. (universe-specific) | `components/performance/metrics-grid.tsx` |
| Equity curve | Interactive chart | `components/performance/equity-curve.tsx` |
| Benchmark toggle | Compare overlay | Part of equity-curve |
| Drawdown chart | Visualization | `components/performance/drawdown-chart.tsx` |
| Date range | Selector | `components/performance/date-range.tsx` |
| Monthly heatmap | Returns calendar | `components/performance/monthly-heatmap.tsx` |

#### Deliverables
- [ ] Equity curve from 2020 to present for each universe
- [ ] All key metrics displayed (universe-aware)
- [ ] Benchmark comparison
- [ ] Drawdown visualization
- [ ] Different metrics visible when switching universes

---

### Phase 4: Trades & Rebalance (Week 7-8)

#### Objectives
- Trade history with search/filter per universe
- Thursday/Friday rebalance workflow for each universe
- Export capability
- Clear indication of which universe you're viewing

#### Backend Tasks

| Task | Description | Endpoint |
|------|-------------|----------|
| Trade service | Query trades per universe | `app/services/trade_service.py` |
| Trade endpoints | Paginated API with universe | `GET /api/trades?universe=nse500` |
| Export endpoint | CSV download per universe | `GET /api/trades/export?universe=nse500` |
| Rebalance service | Parse change files per universe | `app/services/rebalance_service.py` |
| Rebalance endpoints | Preview, orders per universe | `GET /api/rebalance/*?universe=nse500` |
| Trades sync | Import historical for all universes | Part of sync_service |

#### Frontend Tasks

| Task | Description | Component |
|------|-------------|-----------|
| Trades page | Layout with universe filter | `app/(dashboard)/trades/page.tsx` |
| Trades table | Paginated, filterable | `components/trades/trades-table.tsx` |
| Trade filters | Search, date, side, universe | `components/trades/trade-filters.tsx` |
| Trade detail | Modal/sheet | `components/trades/trade-detail.tsx` |
| Export button | Download CSV for universe | `components/trades/export-button.tsx` |
| Rebalance page | Layout with universe selector | `app/(dashboard)/rebalance/page.tsx` |
| Status card | Current state per universe | `components/rebalance/status-card.tsx` |
| Changes preview | Adds/removes | `components/rebalance/changes-preview.tsx` |
| Orders table | Friday view | `components/rebalance/orders-table.tsx` |
| History list | Past rebalances (filterable by universe) | `components/rebalance/history-list.tsx` |

#### Deliverables
- [ ] Searchable trade history per universe
- [ ] CSV export works for selected universe
- [ ] Thursday preview displays changes for each universe
- [ ] Friday orders ready for download per universe
- [ ] Rebalance history shows all universes with filter

---

### Phase 5: Admin Control Panel (Week 9-10)

#### Objectives
- Sleek admin UI with visual controls (no CLI commands needed)
- One-click quick actions for common operations
- Portfolio generator with parameter dropdowns
- Real-time log streaming
- Scheduled automation for all three universes

#### Backend Tasks

| Task | Description | Endpoint |
|------|-------------|----------|
| Job service | Execute commands | `app/services/job_service.py` |
| Job endpoints | CRUD operations | `POST /api/jobs`, `GET /api/jobs/{id}` |
| Log streaming | SSE endpoint | `GET /api/jobs/{id}/logs?stream=true` |
| Scheduler setup | APScheduler | `app/scheduler/scheduler.py` |
| Scheduled tasks | Daily + per-universe weekly | `app/scheduler/tasks.py` |
| Script migration | Move from kite-lab | `app/engine/scripts/` |
| System status | Health + token status | `GET /api/system/status` |

#### Frontend Tasks

| Task | Description | Component |
|------|-------------|-----------|
| Admin page | Full control panel layout | `app/(dashboard)/admin/page.tsx` |
| Quick actions | Stylized action cards | `components/admin/quick-actions.tsx` |
| Action card | Icon + title + description + button | `components/admin/action-card.tsx` |
| Portfolio form | Parameter dropdowns | `components/admin/portfolio-generator.tsx` |
| Universe select | Dropdown for universe | `components/admin/universe-select.tsx` |
| Lookback select | 6/9/12 month options | `components/admin/lookback-select.tsx` |
| Advanced commands | Dropdown + args input | `components/admin/advanced-commands.tsx` |
| Job list | Recent jobs with status | `components/admin/job-list.tsx` |
| Job status badge | Color-coded badges | `components/admin/job-status.tsx` |
| Log viewer | Real-time with auto-scroll | `components/admin/log-viewer.tsx` |
| Schedule table | All scheduled jobs | `components/admin/schedule-table.tsx` |
| System status | Health indicators | `components/admin/system-status.tsx` |

#### Deliverables
- [ ] One-click Daily Pipeline button
- [ ] Portfolio generator with universe/lookback/rebalance dropdowns
- [ ] Real-time log viewer with streaming
- [ ] View job history with per-universe filtering
- [ ] Scheduled jobs for all three universes
- [ ] System status dashboard (API token, last fetch, DB health)

---

### Phase 6: Polish & Production (Week 11-12)

#### Objectives
- Production hardening
- Error handling
- Documentation

#### Tasks

| Category | Task |
|----------|------|
| **Error Handling** | Add error boundaries, fallback UI |
| **Loading States** | Skeletons for all data components |
| **Caching** | Configure SWR cache, API-level caching |
| **Performance** | Optimize queries, add indexes |
| **Monitoring** | Sentry integration, Railway metrics |
| **Security** | CORS, rate limiting, input validation |
| **Notifications** | Toast messages, optional email/Telegram |
| **Mobile** | Responsive tweaks, touch interactions |
| **Documentation** | API docs (Swagger), README |
| **Testing** | Critical path E2E tests |

#### Deliverables
- [ ] All error states handled gracefully
- [ ] Loading states everywhere
- [ ] Monitoring configured
- [ ] Documentation complete

---

## 8. Deployment Strategy

### Vercel (Frontend)

#### Configuration
```json
// vercel.json
{
  "framework": "nextjs",
  "regions": ["sin1"],
  "env": {
    "NEXT_PUBLIC_API_URL": "@api_url",
    "NEXTAUTH_URL": "@nextauth_url",
    "NEXTAUTH_SECRET": "@nextauth_secret",
    "GOOGLE_CLIENT_ID": "@google_client_id",
    "GOOGLE_CLIENT_SECRET": "@google_client_secret"
  }
}
```

#### Deployment Flow
1. Push to `main` branch
2. Vercel auto-builds
3. Preview deployment on PRs
4. Production on merge

### Railway (Backend)

#### Configuration
```toml
# railway.toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "sh -c 'alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT'"
healthcheckPath = "/api/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"

[service]
internalPort = 8000
```

#### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directories
RUN mkdir -p data/nse500_data data/indices_data data/final_portfolio

# Run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
```

### Environment Variables

#### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=https://kite-api.railway.app
NEXTAUTH_URL=https://kite-dashboard.vercel.app
NEXTAUTH_SECRET=<random-32-char-string>
GOOGLE_CLIENT_ID=<from-google-console>
GOOGLE_CLIENT_SECRET=<from-google-console>
```

#### Backend (.env)
```bash
DATABASE_URL=postgresql://user:pass@host:5432/railway
ALLOWED_ORIGINS=https://kite-dashboard.vercel.app
ALLOWED_EMAILS=your-email@gmail.com
KITE_API_KEY=<from-zerodha>
KITE_API_SECRET=<from-zerodha>
JWT_SECRET=<random-32-char-string>
```

---

## 9. Cost Analysis

### Monthly Costs

| Service | Tier | Cost | Notes |
|---------|------|------|-------|
| Vercel | Hobby | $0 | 100GB bandwidth, 6000 build mins |
| Railway | Starter | $5 | 512MB RAM, 1GB storage, always-on |
| PostgreSQL | Included | $0 | 1GB storage with Railway |
| Google OAuth | Free | $0 | No charge |
| Domain (optional) | N/A | ~$1/mo | If using custom domain |

**Total: ~$5/month**

### Scaling Costs

If growth requires more resources:

| Service | Upgrade | Cost |
|---------|---------|------|
| Railway Pro | More RAM, autoscaling | $20/mo |
| Vercel Pro | More bandwidth | $20/mo |
| PostgreSQL | 5GB storage | +$7/mo |

---

## 10. Security Considerations

### Authentication
- Google OAuth with email whitelist
- JWT tokens with short expiry (1 hour)
- Secure cookie settings

### API Security
- CORS restricted to dashboard domain
- Rate limiting (100 req/min per IP)
- Input validation with Pydantic
- SQL injection prevention via ORM

### Data Security
- Environment variables for secrets
- No credentials in code
- PostgreSQL with SSL
- Encrypted connections (HTTPS)

### Access Control
- Single-user (your email only)
- Read-only for most endpoints
- Write operations for jobs only

---

## 11. Future Roadmap

### Potential Enhancements

#### Near-term
- [ ] Email alerts for rebalance days
- [ ] Telegram bot integration
- [ ] Side-by-side universe comparison view
- [ ] Custom date range backtests

#### Medium-term
- [ ] Paper trading mode
- [ ] Order execution via Kite API
- [ ] Multiple portfolios/strategies
- [ ] Mobile app (React Native)

#### Long-term
- [ ] Multi-user support
- [ ] Strategy builder UI
- [ ] ML signal enhancements
- [ ] Options overlay strategies

---

## Appendix A: Files to Migrate from kite-lab

```
kite-lab/
├── data_pipeline/
│   ├── symbol_resolver.py    → kite-api/app/engine/data_pipeline/
│   ├── price_client.py       → kite-api/app/engine/data_pipeline/
│   ├── storage.py            → kite-api/app/engine/data_pipeline/
│   └── qa.py                 → kite-api/app/engine/data_pipeline/
│
├── scripts/
│   ├── run_daily_pipeline.py           → kite-api/app/engine/scripts/
│   ├── run_final_momentum_portfolio.py → kite-api/app/engine/scripts/
│   ├── backtest_momentum.py            → kite-api/app/engine/scripts/
│   ├── build_momentum_signals_flexible.py → kite-api/app/engine/scripts/
│   ├── fetch_nse500_history.py         → kite-api/app/engine/scripts/
│   ├── fetch_indices_history.py        → kite-api/app/engine/scripts/
│   └── compute_benchmark.py            → kite-api/app/engine/scripts/
│
├── data/
│   ├── static/nse500_universe.csv      → kite-api/data/static/
│   ├── static/nifty100_universe.csv    → kite-api/data/static/
│   ├── benchmarks/nifty100.csv         → kite-api/data/benchmarks/
│   └── instruments_full.csv            → kite-api/data/
│
└── ui/
    └── server.py              → Reference for job queue pattern
```

---

## Appendix B: Design Reference Links

- **Primary**: [Next shadcn Admin Dashboard](https://next-shadcn-admin-dashboard.vercel.app/dashboard/default)
- **shadcn/ui**: [ui.shadcn.com](https://ui.shadcn.com)
- **Recharts**: [recharts.org](https://recharts.org)
- **Tailwind CSS**: [tailwindcss.com](https://tailwindcss.com)
- **NextAuth.js**: [next-auth.js.org](https://next-auth.js.org)

---

*Document maintained as part of kite-lab production dashboard project.*
