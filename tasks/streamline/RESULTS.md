# streamline — Results

**Branch:** `streamline` (this branch) → ready to merge to `main`.
**Archive branch:** `repo-snapshot-2026-05-20` (pushed; immutable).
**Outcome:** main is now A + B content only; everything else preserved off-main; AI-first scaffold added.

---

## Headline numbers

| Metric | Before | After | Change |
|---|---|---|---|
| Repo working tree | 3.1 GB | 2.8 GB | −300 MB (untracked junk) |
| Tracked files removed from main | — | ~640 | (preserved on snapshot) |
| Lines deleted from `main` | — | ~966,000 | mostly the historical NSE data CSVs |
| `scripts/*.py` count | 122 | 37 | closed dependency set of daily pipeline + dashboard |
| `tasks/*` subdirs | 30 | 4 | only active/recent (client_portal, rebalance_page, security_agent, streamline) |
| `CLAUDE.md` | 826 lines | 89 lines | content moved to dedicated docs |
| Root .md files | 9 | 4 (CLAUDE, README, MAP, .pre-commit) | guides moved to docs/ or archive |

---

## What landed (commit log on `streamline`)

```
2fd3a3a  streamline: Add AUDIT.md
568438c  streamline: Remove tracked bloat (ta_indicators, nse500_refetch.log)
118d48f  streamline: Archive 26 closed task folders + design_ideas + ui
<scripts>  streamline: scripts/ — keep 37 production files, archive 85 + archived/
<docs>     streamline: Archive 6 root .md files + 6 closed docs/ files
<data>     streamline: Archive heavy tracked data + alt-universe test dirs
<structure> streamline: Add MAP.md + tasks conventions + .claude/workflows scaffolds
<claude>   streamline: Rewrite CLAUDE.md (826 → 89 lines), extract portfolios
```

Plus an untracked-bloat cleanup pass (`rm -rf` for `test_*`, `commodities_data`,
`gdf_test`, `truedata_test`, `us_equities_data`, `nse500_data_backup_*`,
loose root CSVs, `access_token.txt`, `session.json`) that didn't need a
commit because none of it was tracked.

---

## Bucket discipline at completion

| Bucket | On `main` | On `repo-snapshot-2026-05-20` |
|---|---|---|
| **A** Production code | ✅ | (also there — snapshot has everything) |
| **B** Active research | ✅ | also there |
| **C** Closed + ongoing reference | — | ✅ |
| **D** Closed, no ongoing reference | — | ✅ |
| **E** Bloat | — | ✅ (recoverable if mis-classified) |

A new `tasks/streamline/` exists on main only — this folder is the
record-of-record for the cleanup and lives on main as in-progress
work until merged.

---

## New scaffolding (AI-first repo structure)

| Artifact | Purpose |
|---|---|
| `MAP.md` (root) | Single-source index of every dir + pointer to archive branch |
| `tasks/CONVENTIONS.md` | Task-folder lifecycle, required files, `_meta.yml` schema, naming, commit-message rules |
| `scripts/README.md` | Production-script grouping by role + explicit "how not to add bloat" |
| `.claude/workflows/` | New first-class concept alongside agents/ and skills/. Three scaffolds: `ship-feature.md`, `triage-incident.md`, `close-research.md`, plus a README explaining the Skill / Agent / Workflow distinction |
| `docs/portfolios.md` | Full production-portfolio specs lifted out of CLAUDE.md so they load only when needed |
| `CLAUDE.md` (rewritten) | 89-line repo context: what / map / invariants / conventions / workflows / don't-do / quick-refs |

---

## Things kept on main (the A + B set)

**Production code (`A`):**
- `kite-api/`, `kite-dashboard/` (services)
- `scripts/` — 37-file closed dependency set
- `data_pipeline/`, `tests/`, `tools/security/`
- `docs/security/`, `docs/portfolios.md` + 12 other living `docs/*.md`
- `data/static/`, `data/corporate_actions.json` (tracked subset)
- Root: `Dockerfile`, `docker-compose.yml`, `railway.toml`, `requirements.txt`, `.pre-commit-config.yaml`, deploy + ignore files

**Active research (`B`):**
- `tasks/client_portal/` (just shipped)
- `tasks/rebalance_page/` (open backlog)
- `tasks/security_agent/` (active runbook)
- `tasks/streamline/` (this work)

Everything else → archive branch `repo-snapshot-2026-05-20`.

---

## Discoverability invariant

Anyone (human or agent) lands at the repo and can find their way:

```
1. Open CLAUDE.md         → understand what Marketworks is, see invariants
2. Open MAP.md            → see every dir + 1-line purpose + archive pointer
3. Drill into tasks/      → see which initiatives are live (4 of them)
4. Need closed work?      → follow MAP.md to the archive branch
5. Need to do a thing?    → .claude/workflows/<thing>.md tells you how
```

Closed research that informs production (e.g. the OOS retune evidence
trail) is one `git checkout repo-snapshot-2026-05-20` away — same
commands, same paths, same content as before. The cost of accessing
it is one branch switch; the cost of having it always-on-main was
~640 tracked files and ~960k lines.

---

## Verification

- `git log --oneline main..streamline` shows 8 substantive commits
- `npm run build` in kite-dashboard: clean
- `pytest tests/test_clerk_authz.py` in kite-api: 277/277 pass
- `pre-commit run --all-files`: passes
- Daily pipeline scripts still import-clean — verified by inspecting
  the dependency closure in commit 5 ("scripts/ — keep 37 production
  files")
- `wc -l CLAUDE.md` → 89 (target was ~150)

---

## Open follow-ups

| Item | Notes |
|---|---|
| Add `_meta.yml` to the 4 remaining task folders | `tasks/CONVENTIONS.md` documents the schema; populating it for `client_portal`, `rebalance_page`, `security_agent`, `streamline` is mechanical but defer to a quiet moment |
| Build new agents/skills | Per the discussion, `task-scoper`, `backtest-runner`, `deploy-verifier` were proposed; deferred per "Just the structure" choice |
| Periodic prune pass | When the next round of "this got cluttered" feeling hits, repeat: snapshot → audit → archive → prune |
| Restore individual archived items if needed | `git checkout repo-snapshot-2026-05-20 -- <path>` brings any file back onto a branch |
