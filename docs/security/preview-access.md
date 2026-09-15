# Preview access — showing the product while the site is gated

While `SITE_MODE=under_development` / `PRIVATE_MODE=true` are set (the
SEBI RA gate, R-028), marketworks.in shows only the under-development
page and the API refuses every non-privileged token. Until 2026-09-10
the only way past that was the `admin` role, which also grants the
pipeline, sync, engine and waitlist-export endpoints — far more than
someone who just needs to look at the product.

The `preview` role is the narrow version: it passes the gate and grants
nothing else.

## What a preview holder can and cannot do

| | preview | admin |
|---|---|---|
| Pass the site gate (see the real site while gated) | yes | yes |
| Dashboard, positions, performance, trades, rebalance | yes | yes |
| `/insights` (while `NEXT_PUBLIC_INSIGHTS_ACCESS=admin`) | yes | yes |
| The 4 client universes | yes | yes |
| The 3 legacy research universes (`nse500`, `nifty100`, `nifty250`) | **no** (403) | yes |
| `/admin` | **no** | yes |
| Any mutation / engine endpoint (jobs, schedule, sync, headless-login, cache-clear, waitlist read/export/promote) | **no** (403) | yes |

The split lives in `GATE_ROLES` in `kite-api/app/auth.py` and
`canPassGate()` in `kite-dashboard/src/lib/roles.ts`. Everything else
keeps testing `role == "admin"` exactly — with one deliberate exception:
`/insights` visibility reads a third predicate, `canSeeInsightsSandbox()`,
for the reason set out under "Launch dependency" below. Read that section
before granting; it is the half of this design that a code change alone
cannot carry. `kite-api/tests/test_private_mode.py` and
`test_supabase_authz.py` assert both halves against the full endpoint
inventory — a preview token passing an admin endpoint fails the suite.

## Granting

The role lives in the Supabase JWT's `app_metadata.role`, which is
server-controlled (SI-1: `user_metadata` is end-user-editable and is
never read for authz). Setting it needs the service-role key — keep it
in the shell, never in a file, never committed.

1. **The candidate signs in first.** Send them to
   `https://marketworks.in/sign-in` (unlinked, but open while gated) and
   have them complete Google SSO or the email code. This creates the
   user row. They will land back on the under-development page — that is
   expected; they have no role yet.

2. **Find their user id:**

       curl -s "$SUPABASE_URL/auth/v1/admin/users?page=1&per_page=200" \
         -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
         -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
       | jq -r '.users[] | select(.email=="them@example.com") | .id'

3. **Grant:**

       curl -s -X PUT "$SUPABASE_URL/auth/v1/admin/users/$USER_ID" \
         -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
         -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
         -H "Content-Type: application/json" \
         -d '{"app_metadata":{"role":"preview"}}' | jq .app_metadata

   Check the echoed `app_metadata` still carries `provider` /
   `providers` alongside the new `role`. If it does not, re-send the
   call with those keys included — the account's sign-in method is
   recorded there and the account page reads it.

4. **They sign out and back in.** The role is a JWT claim, so it only
   appears in a freshly issued token. Without this they will keep
   hitting the gate and report that it did not work.

5. **Say the terms out loud, and log that you did.** Revoking the role
   later does not unsee anything: a grant lets the holder screenshot,
   record or screen-share the entire pre-registration product, and no
   technical control touches that. Tell each grantee plainly that
   Marketworks is pre-registration, the figures are not published
   material, and none of it is to be shared or reproduced. Then tick the
   holder-log column. This is the only control that exists for
   redistribution, which is why it is a numbered step and not advice.

No redeploy and no env change is involved — this is why the role exists
rather than a second deployment or a shared password. Grants and
revocations take effect on the next token.

## Verifying a grant

From the candidate's browser: `/dashboard` renders with data (not the
coming-soon page), `/insights` loads, and `/admin` bounces to `/`.

From your shell, with their access token (they can copy it from
DevTools, or use one you minted for a test account):

    curl -s -o /dev/null -w '%{http_code}\n' \
      -H "Authorization: Bearer $TOKEN" \
      https://kite-lab-production.up.railway.app/api/portfolio?universe=l6_v2   # 200
    curl -s -o /dev/null -w '%{http_code}\n' \
      -H "Authorization: Bearer $TOKEN" \
      https://kite-lab-production.up.railway.app/api/portfolio?universe=nse500  # 403
    curl -s -o /dev/null -w '%{http_code}\n' \
      -H "Authorization: Bearer $TOKEN" \
      https://kite-lab-production.up.railway.app/api/jobs                       # 403

A 200 on either of the last two means the grant is wrong — treat it as
an incident, not a config nit.

## Revoking

Set the role back:

    curl -s -X PUT "$SUPABASE_URL/auth/v1/admin/users/$USER_ID" \
      -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
      -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
      -H "Content-Type: application/json" \
      -d '{"app_metadata":{"role":"client"}}' | jq .app_metadata

Same check as the grant: confirm the echoed `app_metadata` still carries
`provider` / `providers`. Losing them here breaks the account page's
sign-in-methods list for a user who has done nothing wrong.

Their **current** access token keeps working until it expires (Supabase's
default is one hour unless the project overrides it) — the API verifies
the token's claims, not the live user row. That is acceptable for a
planned end-of-conversation revocation. If you need access cut
immediately, delete the user instead:

    curl -s -X DELETE "$SUPABASE_URL/auth/v1/admin/users/$USER_ID" \
      -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
      -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY"

## Launch dependency — revoke before ungating

When `SITE_MODE` and `PRIVATE_MODE` come off at launch, **revoke every
outstanding preview grant as part of that change**, before or with it.

The reason is not tidiness. `NEXT_PUBLIC_INSIGHTS_ACCESS` is a separate
flag from the gate and will plausibly still be `admin` for a while after
launch — the insight engine's own pre-publication hold. A preview holder
is admitted to `/insights` by `canSeeInsightsSandbox()` in
`kite-dashboard/src/lib/roles.ts`, which is deliberately a different
predicate from `canPassGate()`. So the moment the gate lifts, `preview`
stops meaning "sees what a client sees" and starts meaning "sees
`/insights`, which clients do not". Nobody granted that, and it would be
held by people whose hiring conversation ended months earlier.

Either revoke the grants, or make the `canSeeInsightsSandbox` call a
deliberate decision at that point. The predicate exists so that this is
a one-line edit someone chooses, rather than a coupling nobody notices.

## Holder log

Grants are the thing that quietly persists. The auth_stack_v2 audit
found a spike-era admin grant that had carried into production
untouched; a preview grant left behind is the same failure with a
smaller blast radius. Every grant gets a row and an expiry date decided
at grant time, and the list is re-read at each `/security-audit` run.

| Email | Granted | Expires | Revoked | Told not to share | Why |
|---|---|---|---|---|---|
| amitrajput6726@gmail.com | 2026-09-13 | 2026-09-27 | | | Developer candidate, interview |
| arjunsingh814260@gmail.com | 2026-09-13 | 2026-09-27 | | | Developer candidate, interview |
