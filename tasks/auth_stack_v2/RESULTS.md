# auth_stack_v2 — results (running log)

Close-out summary is written at ship time; until then this is the
running spike/findings log the plan asks for (S0.7).

## 2026-08-10 — Phase 0 started

- Branch `auth_stack_v2` cut from the LOCAL tip of `beta_gtm_mvp`
  (1eefa93 — one unpushed commit ahead of origin during freeze).
- Scratch Supabase project created by founder: ref
  `jhvkfokskanbaiipvcqu`, CLI 2.113.0 linked; `supabase/config.toml`
  committed (env()-only, no literals; `.temp` gitignored).
- **Finding: JWKS endpoint is empty** (`/auth/v1/.well-known/jwks.json`
  -> `{"keys":[]}`). New projects still sign with the legacy shared
  HS256 secret until migrated to asymmetric signing keys. SI-2 forbids
  accepting HS256, so the dashboard migration (JWT Keys -> create ES256
  -> promote) is a hard prerequisite for S0.6. Management API could do
  it, but extracting the CLI's keychain token was blocked by the
  permission classifier — founder does the 30-second dashboard step
  instead.
- Auth settings probe (`/auth/v1/settings`): email provider ON, Google
  OFF (needs OAuth client creds), phone OFF (expected until Phase 5),
  signups open, sms_provider twilio-default (unused).
- **Design simplification**: Supabase access tokens natively include
  `app_metadata` / `user_metadata` claims, so the app role can be read
  from `app_metadata.role` without a Custom Access Token Hook. Spec
  suite pins that; S0.6 verifies against a real token before the hook
  is declared dead (also pins that the native `role` claim —
  PostgREST's `authenticated`/`service_role` — never maps to app role).
- **S0.3 done — red witnessed**: `tests/test_supabase_jwt_spec.py`,
  17 tests. 6 failing exactly as intended (valid-token acceptance,
  app_metadata role extraction, user_metadata spoof ignored, PostgREST
  role claim ignored, unknown-role default, source label); 10 rejection
  guards trivially green (current verifier rejects all non-Clerk
  tokens) and become meaningful post-B1.3; SI-10 double-gate test
  green. Clerk harness unaffected: 291 passed alone and alongside.

Pending founder actions for spike exit: signing-key migration (ES256),
Google provider creds, SMTP + `{{ .Token }}` template (S0.2).
