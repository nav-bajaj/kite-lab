# Repo Audit — streamline branch (2026-05-20)

Comprehensive bucket assignment for every directory + every tracked
loose file in the repo. Drives the cleanup work on `streamline`.

Bucketing scheme (per user's decision in the discussion above):
- **A** — production / actively used → **stays on main**
- **B** — active research → **stays on main**
- **C** — closed with ongoing reference value → **goes to archive branch**
- **D** — closed without ongoing reference value → **goes to archive branch**
- **E** — bloat (clearly worthless) → **deleted from main; preserved on snapshot branch only**

**Archive branch:** `repo-snapshot-2026-05-20` (already pushed). Serves
double duty as the safety snapshot AND the discoverable archive. Pointer
to it lands in MAP.md so future agents/humans know where C/D content lives.

---

## Production code (stays — bucket A)

| Path | Why |
|---|---|
| `kite-api/` | FastAPI backend (production) |
| `kite-dashboard/` | Next.js frontend (production) |
| `data_pipeline/` | Reusable data-fetch library used by scripts + backend |
| `scripts/` (subset — production) | Daily pipeline orchestrators, portfolio runners, login, sync. **Specific files listed below.** |
| `tests/` | Pytest suite for production code |
| `tools/security/` | Scanner configs (gitleaks, semgrep, bandit, etc.) |
| `.claude/` | Agents, skills, settings — runtime config |
| `docs/security/` | Threat model, risk register, attack surface, runbook |
| `data/static/`, `data/corporate_actions.json`, `data/benchmarks/` (tracked subset) | Universe lists + benchmark + adjustments (load-bearing for scripts) |
| Root: `Dockerfile`, `docker-compose.yml`, `railway.toml`, `requirements.txt`, `.pre-commit-config.yaml`, `.dockerignore`, `.railwayignore`, `CLAUDE.md`, `README.md` | Deploy + build + onboarding |
| `tasks/security_agent/`, `tasks/rebalance_page/`, `tasks/client_portal/` | Recent task folders with active ongoing reference (security agent runbook; rebalance backlog; client portal just-shipped) |

## Active research (stays — bucket B)

| Path | Why |
|---|---|
| `scripts/` (May 13–15 calibration cluster) | 17 recently-touched files investigating COMBO Defensive regime variants, Thursday alignment, trade-ledge diff. Ongoing finishing touches for production spec. |
| `experiments/` (kept gitignored) | Working dir for timestamped portfolio runs; gitignored, doesn't bloat main |
| `reports/` (with `.gitkeep` exception) | Security audit output destination; auditing skill writes here |
| `tasks/streamline/` (this folder) | The current task |

## Closed with ongoing reference value (→ archive — bucket C)

| Path | Why archived (vs delete) |
|---|---|
| `tasks/MM-tuning/` | Evidence for L6 v2 calibration + COMBO DD-reduction. CLAUDE.md references it. |
| `tasks/oos_retune_2026/` | Lock dates for v3 configs; defines current production parameters |
| `tasks/walk_forward/` | 78 OOS validations across 13 windows. Justifies "don't re-tune". |
| `tasks/trend_leaders/` | TL25 v3 design + 5-phase optimization log. Why TL25 looks the way it does. |
| `tasks/pipeline_improvements/` | Data-correctness validation + Railway backup strategy. Operational reference. |
| `tasks/security/` | The closed April 2026 audit baseline. Companion to `docs/security/audits/2026-04-baseline.md`. |
| `docs/failed_experiments.md` | Cited in CLAUDE.md; informs what NOT to retry |
| `docs/vol_floor_optimization.md` | Justifies the locked vol_floor=0.05 |
| `docs/volatility_targeting_experiments.md` | Lessons learned, cited in CLAUDE.md |
| `docs/handover.md` | Mac mini setup runbook; rarely needed but useful to keep accessible |
| `docs/benchmark_data_fix_summary.md`, `docs/portfolio_mechanics_fix.md`, `docs/zerodha_api_*.md` | Historical fix narratives — reference for re-debugging similar issues |
| `nse500_data_historical/` (35MB tracked) | GDF 2009-2019 backfill; one-time data, rarely updated. Big — moving to archive removes from main clone size |
| `nifty_100_tests/`, `nifty_250_tests/` (~145MB combined) | Reference backtest suites for the alt universes |
| `tasks/security_agent/2026-04-baseline.md` — already in docs/security/audits | (no action) |

## Closed without ongoing reference value (→ archive — bucket D)

| Path | Why archived |
|---|---|
| `tasks/phase1/` through `tasks/phase6.1/` | Dashboard build phase plans; work done, code in main |
| `tasks/live_portfolio/`, `tasks/calmar-study/`, `tasks/gdf_full_backfill/`, `tasks/om25/`, `tasks/l6_us_tune_2026/`, `tasks/om25_us_tune_2026/`, `tasks/us_equities_2017/`, `tasks/trade_matching/` | Closed initiatives; results either landed in code or were dead-ends |
| `tasks/name_change/`, `tasks/move_domain/` | Recently-shipped infra renames; could go to archive now per the user's strategy (closed work). Keeping in C/D bucket. |
| `tasks/breadth_atlas/` | Closed analysis; no production code depending on it |
| `tasks/dashboard_phases.md` | Top-level summary of the phase plan (redundant with the phase folders) |
| `scripts/` legacy signal builders (~88 files) | `build_*_signals.py`, monte-carlo runs, comparative reports from Jan-Apr 2026. Output formats no longer consumed by current pipeline. |
| `ui/` (legacy Nov 2025 prototype) | Superseded by `design_ideas/` and the deployed `kite-dashboard/` |
| `design_ideas/` (Figma export prototype) | Not deployed; superseded by current production frontend. May be referenced if/when UI redesign happens — but living in archive is fine for that lookup pattern. |
| Root `ROADMAP.md`, `TODO_IMPROVEMENTS.md`, `TAX_ANALYSIS_GUIDE.md`, `VOLATILITY_TUNING_GUIDE.md`, `runbook.md`, `REPORTING_IMPROVEMENTS.md` | Closed-state docs; useful as record but not load-bearing. |
| `docs/eodhd_pricing.md`, `docs/real_portfolio_tracking_plan.md`, `docs/score_filtering_investigation.md`, `docs/data_refresh_action_plan.md`, `docs/reporting_improvements.md` (duplicate), `docs/rebalance_trade_report.md` | Closed plans / dead-end provider experiments |

## Bloat — delete (bucket E)

**Tracked items to git-rm:**
| Path | Why delete |
|---|---|
| `ta_indicators.py` | Orphaned indicator module; not imported anywhere |
| `nse500_refetch.log` | Log file should never have been tracked |
| `tasks/advanced_analytics/`, `tasks/sector_analytics/` | Empty/abandoned task scaffolds |

**Untracked items to rm-rf (already gitignored or never tracked):**
| Path | Why |
|---|---|
| `nse500_data_backup_20260124_155115/` (30MB) | Date-stamped backup dir; already backed up to `~/Documents/stock_data/` |
| `test_backtest_filter/`, `test_backtest_FIXED/`, `test_OLD_SIGNALS_FIXED_BACKTEST/`, `test_SIGNAL_LEVEL_FILTERING/`, `test_zero_defaults/` (5 dirs) | Transient debug dirs |
| `commodities_data/`, `gdf_test/`, `truedata_test/`, `us_equities_data/` | Dead provider/research experiments |
| `notebooks/`, `src/` (empty) | Vestigial placeholders |
| `baseline_signals.csv`, `filtered_signals.csv`, `test_filtered_signals.csv`, `nifty100list.csv` | Loose research CSVs at root |
| `access_token.txt`, `session.json` | Daily-regen secrets; rm and they re-create |

**Bloat inside `scripts/` (~16 files):** archived monte-carlo runs, GDF probes from May 9 that completed, empty `__init__.py`.

---

## Execution sequence

1. Commit 1: this AUDIT.md
2. Commit 2: rm untracked E (dirs + loose CSVs)
3. Commit 3: git rm tracked E (ta_indicators, log, empty task folders)
4. Commit 4: git rm bucket D + C task folders (preserved on `repo-snapshot-2026-05-20`)
5. Commit 5: git rm bucket D scripts (preserved on snapshot)
6. Commit 6: git rm bucket C+D loose root docs + `docs/` subset (preserved on snapshot)
7. Commit 7: Add new structure — MAP.md, dir READMEs, `.claude/workflows/` scaffold, `_meta.yml` convention doc
8. Commit 8: Slim rewrite of CLAUDE.md
9. Commit 9: Update `tasks/streamline/RESULTS.md` and merge to main

The archive is `repo-snapshot-2026-05-20` (already pushed). It's the
discoverable home for everything moved off main.
