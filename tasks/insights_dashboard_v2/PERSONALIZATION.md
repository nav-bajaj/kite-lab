# Personalization architecture — custom watchlists & alerts

Founder question (2026-08-14): "say we assign custom watchlists and
alerts to certain users — how would we factor that in? We have no user
customization today, but it will become necessary sooner rather than
later."

Answer: the auth migration already bought us everything hard. Supabase
Auth gives us verified user identity on every request; Postgres on
Railway holds relational per-user state; SES production access (just
granted on auth_stack_v2) gives us an email channel. What is missing
is purely additive: three tables, one authenticated API namespace, and
an evaluator job. Nothing about the public dashboard design has to
change — which is the key architectural rule below.

## 1. The one binding rule: two API planes

- **Public plane (exists)** — `/api/insights/*`: anonymous, read-only,
  `Cache-Control: public, max-age=900`, identical payload for every
  viewer. This is what makes the dashboard fast and cacheable. It must
  NEVER carry per-user data.
- **Personal plane (new)** — `/api/me/*`: requires the Supabase JWT
  (same `require_user` dependency pattern as the portfolio routes),
  `Cache-Control: private`, always user-scoped. Watchlists, alerts,
  notifications live here.

The frontend composes them: server components render the shared
dashboard from the public plane; a thin client layer (SWR + bearer,
the exact pattern the portfolio side already uses) hydrates the
personal bits — star states, "My watchlist" module, alert badges.
This keeps personalization from destroying the caching story.

## 2. Data model (Postgres, alembic migration)

```
user_watchlists        id PK · user_id · name · created_at
watchlist_symbols      watchlist_id FK · symbol · added_at
                       (normalized, not JSONB — alerts + entitlement
                        counts want per-symbol rows)
user_alerts            id PK · user_id · kind · params JSONB ·
                       channel (in_app|email) · is_active ·
                       cooldown_hours · last_fired_at · created_at
user_notifications     id PK · user_id · alert_id FK · fired_at ·
                       title · body · read_at
```

Alert `kind` starts from what the engines already compute — no new
math, just thresholds over existing snapshots:

| kind | params | evaluated against |
|---|---|---|
| `price_level` | symbol, above/below, level | EOD close / intraday snapshot |
| `list_event` | list key, symbol or "any", enter/exit | curated-list membership (Phase 1.2 daily cross-section) |
| `rs_rank` | symbol, rank threshold, crosses | rs_rank table |
| `rrg_quadrant` | sector, universe, quadrant change | RRG panel |
| `breadth_level` | metric, threshold | breadth panel |

Symbols validate against the universe file; alert params validate
against a per-kind schema (pydantic), so the evaluator never parses
free-form user input.

## 3. Evaluation & delivery

- **Evaluator job** in the existing APScheduler: runs once after the
  16:30 pipeline (EOD alerts, ships first), and optionally per
  intraday snapshot for `price_level`/`list_event` once the live layer
  exists (posture C). It reads the same engine snapshots the dashboard
  reads — evaluation is a cheap loop over active alerts, not a
  recompute.
- **Delivery ladder**: (1) in-app notification center — `user_notifications`
  rows + a navbar bell, zero external dependencies; (2) email via SES
  (production access already granted); (3) WhatsApp later (Meta
  approval was already the blocker in insight_engine Phase 3 — not
  this task's problem).
- Cooldowns are mandatory (`last_fired_at` + `cooldown_hours`) or
  intraday alerts will spam re-fires around a threshold.

## 4. Frontend surfaces

- Star toggle on every symbol row (lists, screener, stock page) —
  optimistic SWR mutation.
- "My watchlist" module on Pulse: the user's symbols run through the
  SAME engine columns (RS rank, scores, tags) — personal selection,
  shared analytics. This is the cheapest high-value personalization.
- Alert composer on the stock page ("notify me if...") and a manager
  under settings; notification bell in the navbar.

## 5. Entitlements tie-in (the real reason to do it this way)

`entitlements_v1` is already the planned follow-on to auth_stack_v2.
Watchlist/alert capacity is the natural first paid boundary — e.g.
free: 1 watchlist × 10 symbols, 3 EOD alerts; paid: more of each +
intraday alerts + email channel. Enforce limits server-side in the
`/api/me/*` handlers by reading the user's entitlement (single
function now, entitlements service later). Designing the tables
per-row (not JSONB blobs) is what makes these limits enforceable and
countable.

## 6. Compliance & security notes

- Alert copy is user-configured *conditions on published indicators*.
  Notification text stays in the closed lexicon: "condition met:
  RELIANCE crossed above 2,900", never "buy signal triggered".
  Lexicon tests extend to notification templates.
- Every `/api/me/*` query is scoped by `user_id` from the verified
  JWT — no client-supplied user ids anywhere. Add an authz test file
  mirroring `test_clerk_authz.py` coverage (IDOR: user A cannot read
  or fire user B's watchlists/alerts).
- New API surface ⇒ security-reviewer subagent pass before merge;
  register row if the posture differs from the documented ones.
- Data deletion: watchlists/alerts/notifications cascade on user
  delete (the auth stack's account-deletion path must include them).

## 7. Sequencing (post-launch, but schema-ready now)

1. Migration + watchlists CRUD + star UI + "My watchlist" on Pulse.
2. Notification center + EOD evaluator + `list_event`/`rs_rank` kinds.
3. Email channel (SES) + entitlement limits.
4. Intraday kinds once the live layer ships.

Nothing in phases 1-3 depends on the intraday layer; phase 1 alone is
a meaningful retention feature for launch+1.
