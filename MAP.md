# Repo Map

Single-source index of every directory in `main`. For AI agents and
humans landing in the repo for the first time. Keep terse — one line of
purpose per entry. Update when a new top-level directory lands.

| Directory | Purpose | Stability |
|---|---|---|
| `kite-api/` | FastAPI backend deployed to Railway (Postgres-backed). | **stable** |
| `kite-dashboard/` | Next.js 16 frontend on Vercel; Clerk auth; role-gated client portal. | **stable** |
| `scripts/` | Production scripts: daily pipeline, portfolio runners, sync, DB ops. Closed dependency set — see `scripts/README.md`. | **stable** |
| `data_pipeline/` | Reusable Python library for symbol resolution, price fetching, storage. Imported by `scripts/` and `kite-api/`. | **stable** |
| `tools/security/` | Scanner configs (gitleaks, semgrep, bandit, trufflehog excludes, suppressions). | **stable** |
| `tests/` | pytest suite for the production scripts layer. | **stable** |
| `docs/` | Living documentation: ops runbook, deployment guide, lessons-learned. Curated subset; closed research lives on the archive branch. | **stable** |
| `docs/security/` | Threat model, risk register, attack surface, runbook, audit archive. | **stable** |
| `data/` | Static data tracked: universe lists, corporate actions, benchmarks. Other subdirs are runtime caches (gitignored). | **stable** |
| `tasks/` | One folder per in-flight or recently-shipped initiative. Conventions in `tasks/CONVENTIONS.md`. | **changing** |
| `reports/security/` | Output destination for `/security-audit` skill runs. Empty by default. | **runtime** |
| `.claude/` | Agent definitions, slash-command skills, workflow playbooks, settings. | **stable** |

## Closed research history → archive branch

For older research, closed task folders, dead-end experiments, and the
legacy `nse500_data_historical/` / `nifty_*_tests/` reference suites:

```bash
git fetch origin
git checkout repo-snapshot-2026-05-20    # safety + archive snapshot
# OR browse on GitHub:
# https://github.com/nav-bajaj/kite-lab/tree/repo-snapshot-2026-05-20
```

The snapshot is **immutable** — never push to it. It's the discoverable
home for everything that was on `main` as of 2026-05-20 17:00 IST.

Headline contents of the archive branch (not on main):
- `tasks/MM-tuning/`, `tasks/oos_retune_2026/`, `tasks/walk_forward/`,
  `tasks/trend_leaders/`, `tasks/pipeline_improvements/`, `tasks/security/`
  — load-bearing closed research (CLAUDE.md cites these for "why").
- `tasks/phase1/`..`tasks/phase6.1/` — dashboard build phase plans.
- `tasks/calmar_study/`, `tasks/gdf_full_backfill/`, `tasks/om25/`,
  `tasks/l6_us_tune_2026/`, `tasks/om25_us_tune_2026/`,
  `tasks/us_equities_2017/`, `tasks/trade_matching/`,
  `tasks/breadth_atlas/`, `tasks/live_portfolio/` — closed initiatives.
- `tasks/name_change/`, `tasks/move_domain/` — recent infra renames
  (shipped).
- 85 closed research scripts: `_calibration_*`, `_combo_*`, `_gdf_*`,
  `momentum_*`, `multi_strategy_*`, `walk_forward_*`,
  `breadth_atlas_*`, etc.
- Heavy data dirs: `nse500_data_historical/`, `nifty_100_tests/`,
  `nifty_250_tests/`.
- Root markdown: `ROADMAP.md`, `TODO_IMPROVEMENTS.md`, `runbook.md`,
  `TAX_ANALYSIS_GUIDE.md`, `VOLATILITY_TUNING_GUIDE.md`,
  `REPORTING_IMPROVEMENTS.md`.
- Several closed `docs/*.md` (eodhd_pricing, real_portfolio_tracking_plan,
  score_filtering_investigation, etc.).

## Loose root files on main

| File | Purpose |
|---|---|
| `CLAUDE.md` | Project context loaded into every Claude conversation. Keep it small. |
| `README.md` | Human-facing intro. |
| `MAP.md` | This file. |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `.railwayignore`, `railway.toml` | Deploy. |
| `requirements.txt` | Python deps (full `pip freeze` from the project venv). |
| `.pre-commit-config.yaml` | Pre-commit hooks (gitleaks, ruff S, eslint security on staged JS). |
| `.gitignore` | Includes `tmp/`, `reports/` (except security), data dirs. |
