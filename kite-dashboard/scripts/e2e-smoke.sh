#!/usr/bin/env bash
# Auth E2E smoke runner (auth_stack_v2 H3.7).
# Pulls the service-role key from the authenticated Supabase CLI so it
# never lives in a file, then runs the Playwright suite.
set -euo pipefail
cd "$(dirname "$0")/.."

# This suite CREATES AND MUTATES USERS through the admin API.
#
# When it was written (2026-08-11) jhvkfokskanbaiipvcqu was the scratch
# project and the rule was "never point this at production". At the
# cutover that same project became production — it is the only Supabase
# project on the account — so the old default now aims a user-mutating
# suite at the live auth store, while the comment above it claimed the
# opposite. Refuse by default instead.
PROD_REF="jhvkfokskanbaiipvcqu"
PROJECT_REF="${SUPABASE_PROJECT_REF:-}"

if [ -z "$PROJECT_REF" ]; then
  echo "e2e-smoke: set SUPABASE_PROJECT_REF to the project to test against." >&2
  echo "  There is no safe default: the production project ($PROD_REF) is" >&2
  echo "  currently the only one on the account." >&2
  exit 1
fi

if [ "$PROJECT_REF" = "$PROD_REF" ] && [ "${ALLOW_PROD_E2E:-}" != "yes-i-mean-production" ]; then
  echo "e2e-smoke: refusing to run against PRODUCTION ($PROD_REF)." >&2
  echo "  This suite creates and mutates real users in the live auth store." >&2
  echo "  Create a separate scratch project, or re-run with" >&2
  echo "  ALLOW_PROD_E2E=yes-i-mean-production if that is genuinely intended." >&2
  exit 1
fi

# The spec runs outside Next, so .env.local isn't loaded — provide the
# project URL to the Playwright process directly.
export NEXT_PUBLIC_SUPABASE_URL="${NEXT_PUBLIC_SUPABASE_URL:-https://${PROJECT_REF}.supabase.co}"

SUPABASE_SERVICE_ROLE_KEY=$(
  supabase projects api-keys --project-ref "$PROJECT_REF" -o json |
    python3 -c "import json,sys; print([k['api_key'] for k in json.load(sys.stdin) if k['name']=='service_role'][0])"
)
export SUPABASE_SERVICE_ROLE_KEY

exec npx playwright test "$@"
