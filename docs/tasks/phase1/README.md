# Phase 1: Foundation

**Duration**: Week 1-2
**Status**: In Progress
**Started**: February 2026

## Objectives

- Set up project infrastructure (FastAPI backend, Next.js frontend)
- Implement authentication (Google OAuth with email whitelist)
- Deploy basic shells to Vercel/Railway
- Multi-universe support from day one (NSE 500, Nifty 250, Nifty 100)

## Task Progress

### Backend Track

| # | Task | Status | File |
|---|------|--------|------|
| 1 | Set up FastAPI backend project structure | `completed` | [01-backend-setup.md](./01-backend-setup.md) |
| 2 | Set up PostgreSQL database with SQLAlchemy models | `completed` | [02-database-models.md](./02-database-models.md) |
| 3 | Implement health endpoint and auth middleware | `completed` | [03-health-auth.md](./03-health-auth.md) |
| 4 | Create Docker and Railway deployment config | `completed` | [04-docker-railway.md](./04-docker-railway.md) |
| 5 | Migrate data pipeline modules from kite-lab | `completed` | [05-migrate-pipeline.md](./05-migrate-pipeline.md) |

### Frontend Track

| # | Task | Status | File |
|---|------|--------|------|
| 6 | Set up Next.js frontend project with TypeScript | `completed` | [06-nextjs-setup.md](./06-nextjs-setup.md) |
| 7 | Install and configure shadcn/ui components | `completed` | [07-shadcn-components.md](./07-shadcn-components.md) |
| 8 | Implement NextAuth.js with Google OAuth | `pending` | [08-nextauth.md](./08-nextauth.md) |
| 9 | Create dashboard layout with sidebar navigation | `pending` | [09-dashboard-layout.md](./09-dashboard-layout.md) |
| 10 | Implement universe selector and context | `pending` | [10-universe-selector.md](./10-universe-selector.md) |
| 11 | Create API client with SWR integration | `pending` | [11-api-client.md](./11-api-client.md) |

### Deployment

| # | Task | Status | File |
|---|------|--------|------|
| 12 | Deploy initial shells to Vercel and Railway | `pending` | [12-deploy.md](./12-deploy.md) |

## Dependency Graph

```
Backend:                          Frontend:
┌───┐                            ┌───┐
│ 1 │ FastAPI Setup              │ 6 │ Next.js Setup
└─┬─┘                            └─┬─┘
  │                                ├──────────┬──────────┐
  ├────────┬────────┐              │          │          │
  ▼        ▼        ▼              ▼          ▼          ▼
┌───┐    ┌───┐    ┌───┐         ┌───┐      ┌───┐      ┌───┐
│ 2 │    │ 4 │    │ 5 │         │ 7 │      │ 8 │      │11 │←─┐
└─┬─┘    └───┘    └───┘         └─┬─┘      └───┘      └───┘  │
  │       Docker   Pipeline       │         Auth        API   │
  ▼                               ├────────┐                  │
┌───┐                             ▼        ▼                  │
│ 3 │                           ┌───┐    ┌────┐               │
└───┘                           │ 9 │    │ 10 │               │
Health/Auth                     └───┘    └────┘               │
                               Layout   Universe              │
                                                              │
                    ┌─────────────────────────────────────────┘
                    │ (also blocked by #8)
                    │
                    ▼
              ┌──────────┐
              │    12    │ Deploy (blocked by #3, #4, #9, #10, #11)
              └──────────┘
```

## Deliverables Checklist

- [ ] Login with Google OAuth works
- [ ] Empty dashboard shell deployed
- [ ] Universe selector visible in header/sidebar
- [ ] Health endpoint returns OK
- [ ] Database tables created with universe column

## Notes

- Tasks #1 and #6 can be worked on in parallel (no dependencies)
- Backend and Frontend tracks can progress independently until deployment

---

*Status Key: `pending` | `in_progress` | `completed`*
