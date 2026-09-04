#!/usr/bin/env bash
# Refuse pushes to the production branch during Indian market hours.
#
# beta_gtm_mvp deploys BOTH Vercel and the Railway `kite-lab` API, and a
# Railway deploy restarts the service regardless of what the commit
# touched — a docs-only commit restarts the API just as a code change
# does. The options worker lives on its own service and branch, so it is
# not in the blast radius, but the API is.
#
# ONE window, IST: 09:00-17:30, weekdays.
#
# Not just market hours. The options workers keep running past the close,
# so 15:30 is NOT safe despite being the end of the trading session, and
# the EOD proposal + daily pipeline run into the evening behind them.
# 17:30 is the first genuinely quiet moment. Do not narrow this back to
# 15:30 — that gap was wrong once already.
#
# Override for something genuinely urgent:
#   ALLOW_PUSH_IN_FREEZE=yes git push ...
set -euo pipefail

PROD_BRANCH="beta_gtm_mvp"
branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
[ "$branch" = "$PROD_BRANCH" ] || exit 0
[ "${ALLOW_PUSH_IN_FREEZE:-}" = "yes" ] && exit 0

now=$(TZ=Asia/Kolkata date +%H%M)
day=$(TZ=Asia/Kolkata date +%u)   # 1-5 = Mon-Fri

# Weekends are always fine — no market, no pipeline.
[ "$day" -gt 5 ] && exit 0

blocked=""
if [ "$now" -ge 0900 ] && [ "$now" -lt 1730 ]; then
  blocked="the trading-day freeze (09:00-17:30 IST)"
fi

if [ -n "$blocked" ]; then
  echo "" >&2
  echo "  PUSH BLOCKED — it is $(TZ=Asia/Kolkata date '+%H:%M IST'), inside $blocked." >&2
  echo "" >&2
  echo "  Pushing $PROD_BRANCH redeploys the Railway API, which restarts it" >&2
  echo "  even for a docs-only commit." >&2
  echo "" >&2
  echo "  Wait, or: ALLOW_PUSH_IN_FREEZE=yes git push ..." >&2
  echo "" >&2
  exit 1
fi
exit 0
