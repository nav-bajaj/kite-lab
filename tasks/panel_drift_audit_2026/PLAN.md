# Panel drift + membership audit

**Status:** in-progress · **Opened:** 2026-09-08

## Why

`tasks/om25_cadence_2026` set out to test OM25 entry cadence and, in the
control check, found that OM25 v3's published OOS figures (44.78% CAGR /
1.86 Sharpe) no longer reproduce on today's `nse500_data_merged` — the same
locked config now backtests to ~35%. That is a live-documentation problem
that outgrew the cadence task.

Two questions:

1. **Is it OM25-specific or repo-wide?** Run the other production portfolios
   through the same reproduction check. L6 v2 first.
2. **What does effective-dated membership actually do to a published number?**
   It shipped 2026-07-15, after every published figure was computed, and it
   changes cross-sectional scores for every stock — not just the ones whose
   membership changed.

## Method

Use the production runners unmodified. Membership on/off is already a
supported flag (`--membership <nonexistent path>` forces the legacy snapshot
path), so no new backtest code is needed. Compare against:

- the archive-branch equity curves where they exist
  (`tasks/oos_retune_2026/winner_artifacts/`), else
- the published figures and windows in `docs/portfolios.md`.

## Scope

In: L6 v2 (done), TL25 v3, COMBO Defensive. Reproduction + membership
attribution only.

Out: deciding which panel state is *correct* — that is
`tasks/corporate_actions_fix`. No production changes. No re-tuning.

## Critical files

| Path | Role |
|---|---|
| `scripts/run_l6_v2_portfolio.py` | Run unmodified, both membership modes |
| `scripts/universe_membership.py` | `resolve_universe` / `candidate_fn` / `membership_fn` |
| `tasks/om25_cadence_2026/` | Where the drift was found; its RESULTS.md was corrected from here |
| `runs/l6_memON/`, `runs/l6_memOFF/` | Artifacts |
