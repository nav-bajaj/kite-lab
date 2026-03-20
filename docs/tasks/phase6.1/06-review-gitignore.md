# Task 06: Review Gitignore

**Status**: `pending`
**Priority**: LOW
**Estimated Time**: 15 minutes

## Problem

Verify that experiment directories and other generated files are properly handled by `.gitignore`. The current git status shows 46+ untracked directories - need to confirm this is intentional.

## Current State

```bash
$ git status
Untracked files:
  .vercel/
  commodities_data/
  data/final_portfolio/prior_portfolio.csv
  docs/real_portfolio_tracking_plan.md
  experiments/final_portfolio/final_portfolio_20260214135227/
  ... (26 more experiment dirs)
  logs/
  nifty_100_tests/nifty100_portfolio_20260214164622/
  ... (17 more nifty100 dirs)
  nifty_250_tests/nifty250_portfolio_20260214164643/
  ... (16 more nifty250 dirs)
```

## Actions Required

### 1. Review Current .gitignore

Check what's already ignored:

```bash
cat .gitignore | grep -E "(experiment|nifty|logs)"
```

### 2. Verify Experiment Dirs Are Ignored

The timestamped experiment directories should be ignored. If not, add:

```gitignore
# Experiment runs (timestamped)
experiments/final_portfolio/final_portfolio_*/
nifty_100_tests/nifty100_portfolio_*/
nifty_250_tests/nifty250_portfolio_*/
```

### 3. Add Missing Entries

Based on untracked files, consider adding:

```gitignore
# Vercel
.vercel/

# Logs
logs/

# Commodities (if experimental)
commodities_data/

# Archives (from cleanup script)
archives/
```

### 4. Decide on Plan Files

Some docs appear untracked:
- `docs/real_portfolio_tracking_plan.md`
- `data/final_portfolio/prior_portfolio.csv`

These should likely be tracked (committed), not ignored.

## Expected Final State

After review:

| File/Directory | Action | Reason |
|----------------|--------|--------|
| `experiments/*/` | Ignore | Generated, large |
| `nifty_*_tests/*/` | Ignore | Generated, large |
| `logs/` | Ignore | Runtime logs |
| `.vercel/` | Ignore | Local Vercel config |
| `commodities_data/` | Ignore or track | Depends on use |
| `docs/*.md` | Track | Documentation |
| `prior_portfolio.csv` | Track | Reference data |

## Verification

After changes:

```bash
# Should show only files intended to be tracked
git status

# Verify patterns match
git check-ignore -v experiments/final_portfolio/final_portfolio_20260214135227/
# Expected: .gitignore:XX:pattern  experiments/...
```

## Files Modified

- `.gitignore`
- Possibly commit untracked docs

---

*Task created: 2026-03-20*
