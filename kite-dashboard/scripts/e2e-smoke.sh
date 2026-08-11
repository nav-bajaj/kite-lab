#!/usr/bin/env bash
# Auth E2E smoke runner (auth_stack_v2 H3.7).
# Pulls the service-role key from the authenticated Supabase CLI so it
# never lives in a file, then runs the Playwright suite.
set -euo pipefail
cd "$(dirname "$0")/.."

# Scratch project ONLY — the suite creates/links users via the admin
# API. Never point this at the production project ref.
PROJECT_REF="${SUPABASE_PROJECT_REF:-jhvkfokskanbaiipvcqu}"

# The spec runs outside Next, so .env.local isn't loaded — provide the
# project URL to the Playwright process directly.
export NEXT_PUBLIC_SUPABASE_URL="${NEXT_PUBLIC_SUPABASE_URL:-https://${PROJECT_REF}.supabase.co}"

SUPABASE_SERVICE_ROLE_KEY=$(
  supabase projects api-keys --project-ref "$PROJECT_REF" -o json |
    python3 -c "import json,sys; print([k['api_key'] for k in json.load(sys.stdin) if k['name']=='service_role'][0])"
)
export SUPABASE_SERVICE_ROLE_KEY

exec npx playwright test "$@"
