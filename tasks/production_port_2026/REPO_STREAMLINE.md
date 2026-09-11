# Repo streamline — what moves where

Goal: one engine, one data path, research folders that are records rather than code paths.

| Item | Today | Target |
|---|---|---|
| Engine | `scripts/_clean_engine.py` + a hooked copy in `tasks/mm_rebuild/lib/_engine_iv.py` | one engine with the hooks default-off; the copy deleted after the identity test passes in CI |
| Scores, regimes, sizing | `tasks/om25_rebuild/lib/`, `tasks/mm_rebuild/lib/` | `data_pipeline/strategies/` (momentum, capture, blend, regime, sizing); research harnesses import from there |
| Research harness | `run.py` in two task folders (one imports the other by path) | a single `data_pipeline/harness.py` (run_candidate, registry, windows) used by future tasks |
| Price panels | `nse500_data*/` (production, backdated), `~/Documents/stock_data` mirrors, `data/master` | `data/master` only; the old dirs frozen read-only until the legacy books retire, then archived |
| Membership | `data/static/*_membership.csv` (production) and `data/master/membership/` (honest) | one set under `data/master/`; `data/static` keeps only the snapshot views the dashboard reads |
| Sector data | `data/static/zerodha_sectors.csv`, `sector_constituents/`, `tasks/mm_rebuild/sector/` | `data/master/sectors/` with the scheme map and a refresh script |
| Reports | `tasks/*/report/*.pdf` | `reports/portfolios/<date>/` (git-ignored PDFs, committed markdown summaries) |
| Task folders | om25_rebuild, mm_rebuild, calls_honest, index_reconstruction, market_data_spine on main; ~10 closed folders | keep the five as reference for one quarter, then archive to the snapshot branch per CONVENTIONS; `MAP.md` updated |
| Runs | `tasks/*/runs/` (gitignored, ~1.3 GB) | registries and summary CSVs kept; per-run trade logs deleted after the port (regenerable) |
| Docs | `docs/portfolios.md` describes the legacy four; CLAUDE.md invariants list old IDs | portfolios.md gains the two books; CLAUDE.md points at MECHANICS.md; runbooks for reconstitution and the nightly store under `docs/ops/` |
| Untracked | `supabase/`, `tools/git/`, dashboard AGENTS/CLAUDE files, `tasks/dip_vs_breakout_calls`, `tasks/om25_cadence_2026` | founder to say which are wanted; commit or delete |
