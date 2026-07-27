# CLAUDE.md

Project context loaded into every Claude conversation on this repo.
Keep it small; point at authoritative docs rather than inlining their
content.

## What this is

**Marketworks** — a momentum-based quantitative trading platform for
Indian equities. Two halves:

1. **Research toolkit** (`scripts/`, `data_pipeline/`, `tests/`)
   — Python; fetches NSE data via Zerodha KiteConnect, builds momentum
   signals, backtests strategies, runs the daily production pipeline.
2. **Web product** (`kite-api/`, `kite-dashboard/`) — FastAPI on
   Railway + Next.js on Vercel; Postgres-backed; Clerk auth; deployed
   at <https://marketworks.in>. Currently in Private Beta with sign-up
   allowlist.

The 4 production portfolios are documented in `docs/portfolios.md`:
**Quality Momentum** (OM25 v3, Nifty 250), **Trend Leaders** (TL25 v3,
NSE 500), **Core Momentum** (L6 v2, NSE 500), **Defensive Blend**
(COMBO, NSE 500). Clients see these 4; admins see 3 more alt-universe
legacy variants.

## Repo map

Read `MAP.md` first when landing fresh. Headline:

| Where | What |
|---|---|
| `scripts/` (37 production files) | Daily pipeline, portfolio runners, sync — see `scripts/README.md` |
| `kite-api/`, `kite-dashboard/` | Production services |
| `data_pipeline/`, `tests/`, `tools/security/` | Library, tests, scanner configs |
| `docs/` | Living ops + research docs — see `docs/portfolios.md`, `docs/security/` |
| `tasks/` | One folder per initiative — see `tasks/CONVENTIONS.md` |
| `.claude/` | Agents, skills, workflows — see `.claude/workflows/README.md` |

Closed research history → branch `repo-snapshot-2026-05-20`. Browse it
on GitHub or `git checkout` for any closed task folder, archived
script, or removed `.md`. Don't push to that branch.

## Active invariants — do not break

- **Auth:** Clerk verifies session JWTs via JWKS (RS256, issuer-pinned). Role in `publicMetadata.role` (`client`/`admin`). 16 backend mutation/engine endpoints behind `require_admin`. 20 client-read endpoints behind `check_universe_access` (clients can't query admin-only universes). Tests at `kite-api/tests/test_clerk_authz.py` (288 assertions) — don't weaken.
- **Universe IDs are stable.** `nse500`, `nifty250`, `nifty100`, `om25_v3`, `tl25_v3`, `l6_v2`, `combo_defensive`. Never rename — they're in DB rows, CSV columns, and URLs. Display names live in `kite-dashboard/src/lib/universes.ts`.
- **CSP, security headers, rate limiting** on the backend are R-006/R-007 risk-register closures. Loosening any requires a register row first — see `docs/security/risk-register.md`.
- **Token files** (`access_token.txt`, `session.json`) written with mode 0o600. Pattern in `kite-api/app/services/system_service.py`.
- **Daily pipeline order** (see `scripts/run_daily_pipeline.py`): login → instruments → NSE 500 + indices → corporate-actions adjust → benchmark → shared-state cache → all 7 portfolios via `update_all_portfolios.py` → DB sync → cloud upload. Each step has a downstream consumer — don't reorder casually.
- **`/api/system/*`** is intentionally unauthenticated (AD-1, R-003). Only OAuth-bootstrap routes go there; any new route here must pass through the `security-reviewer` subagent first.

## Conventions

- **Task folders** (`tasks/<name>/`): PLAN.md + TASKS.md + RESULTS.md + `_meta.yml`. See `tasks/CONVENTIONS.md`.
- **Commit messages**: prefix with task folder name when relevant — `client_portal: Phase 1 backend Clerk JWKS verification`. Body explains *why*, not *what files*.
- **Branch flow**: branch off `main`, work on the branch, merge with `--no-ff` so the merge commit summarises the initiative.
- **Scripts**: production set is closed; new research probes go in `tasks/<name>/`, not in `scripts/`. See `scripts/README.md` for the "how not to" list.
- **No emojis in files** unless the user explicitly asks. No comments narrating *what* code does — only *why* when non-obvious.

## Workflows

| Goal | Playbook |
|---|---|
| Ship a new feature | `.claude/workflows/ship-feature.md` |
| Production is down | `.claude/workflows/triage-incident.md` |
| Close out a research task | `.claude/workflows/close-research.md` |
| Project-wide security audit | `/security-audit` skill (`.claude/skills/security-audit/`) |
| Review a diff against the threat model | `security-reviewer` subagent (`.claude/agents/security-reviewer.md`) |

## Don't-do list

- Don't add `scripts/<one_off>.py` — research probes go in `tasks/<name>/`.
- Don't commit `.env`, `access_token.txt`, `session.json`, `tmp/` — the pre-commit hook blocks `.env*` patterns but be deliberate.
- Don't push to `main` without local `npm run build` + (if backend touched) `pytest tests/` clean.
- Don't widen CSP or CORS without a register-row entry.
- Don't change `data/static/*.csv` universe files without re-fetching the prices for any new symbols.
- For work in `kite-api/app/insights/` (engines, detectors, threshold/classifier functions) and any new forward-return claim, default to TDD per `tasks/insight_engine/TDD_POLICY.md`: spec test first, see it fail, then implement. Out-of-scope for TDD: content authoring, UI layout, refactors, orchestrator field-plumbing.

## Quick references

- **URLs:** Frontend <https://marketworks.in> (Vercel). Backend <https://kite-lab-production.up.railway.app> (Railway service `kite-lab`).
- **Daily pipeline:** `python scripts/run_daily_pipeline.py --with-login`
- **Spin up locally:** `cd kite-dashboard && npm run dev` (frontend) + `cd kite-api && source ../.venv/bin/activate && uvicorn app.main:app --reload --port 8000` (backend). Frontend's NEXT_PUBLIC_API_URL falls back to `localhost:8000`; CSP allows it in dev mode (see `kite-dashboard/next.config.ts`).
- **Security audit:** `/security-audit` skill. Output lands at `reports/security/<UTC-date>/report.md`.
- **Risk register:** `docs/security/risk-register.md` (23 rows; new gaps go here).

---

If this file gets longer than ~160 lines, something belongs in a
dedicated doc instead. Keep it lean.
