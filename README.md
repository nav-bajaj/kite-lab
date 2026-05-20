# Marketworks

A momentum-based quantitative trading platform for Indian equities, built on the Zerodha KiteConnect API. The directory layout, Railway service, and Vercel deployment are still named `kite-lab` for historical reasons; the user-facing product is Marketworks.

> **Status: Private Beta.** Production lives at <https://marketworks.in>. SEBI Research Analyst registration is currently applied for. All content and functionality is for research and educational purposes; nothing on the platform is investment advice.

## Two halves of the project

1. **Quantitative research toolkit** (Python, `scripts/` + `data_pipeline/`): fetches NSE data via Zerodha KiteConnect, builds momentum signals, applies corporate actions, runs the daily production pipeline.
2. **Web product** (`kite-dashboard/` + `kite-api/`): Next.js 16 + Tailwind frontend on Vercel, FastAPI backend on Railway, Postgres for trade/portfolio data. Authentication via Clerk (Google sign-in, role-gated). Clients see 4 production portfolios (Quality Momentum, Trend Leaders, Core Momentum, Defensive Blend); admins see all 7.

## Where to start

- **`CLAUDE.md`** — project context, active invariants, conventions, workflows.
- **`MAP.md`** — index of every directory + pointer to the archive branch.
- **`docs/portfolios.md`** — full specs of the 4 production + 3 legacy portfolios.
- **`scripts/README.md`** — production-script layout.
- **`tasks/CONVENTIONS.md`** — task-folder lifecycle and conventions.
- **Closed research history** → branch `repo-snapshot-2026-05-20`.

## Setup

```bash
git clone https://github.com/nav-bajaj/kite-lab.git
cd kite-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the project root:

```
API_KEY=your_kite_api_key
API_SECRET=your_kite_api_secret
REDIRECT_URI=http://localhost:8000/callback
```

For multi-machine setup (laptop + Mac mini), see `docs/handover.md`.

## Daily usage

```bash
# Authenticate (browser-based OAuth, writes access_token.txt)
python scripts/login_and_save_token.py

# Run the full daily pipeline: instruments → prices → signals → portfolios → DB sync → cloud upload
python scripts/run_daily_pipeline.py --with-login
```

The pipeline orchestrates the closed set of production scripts described in `scripts/README.md`. The invariant order is documented in `CLAUDE.md` under "Active invariants".

## Local web stack

```bash
# Backend (FastAPI on :8000)
cd kite-api && source ../.venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Frontend (Next.js on :3000)
cd kite-dashboard && npm run dev
```

CSP allows `localhost:8000` in dev mode (see `kite-dashboard/next.config.ts`).

## Security

- Never commit `.env`, `access_token.txt`, or `session.json` (pre-commit hook blocks `.env*` patterns).
- Risk register at `docs/security/risk-register.md`; project-wide audits via `/security-audit` skill.
- Threat-model review of any diff: `security-reviewer` subagent.

## License

MIT
