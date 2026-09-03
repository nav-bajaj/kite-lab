"""
Test environment, set before ANY test module or app code is imported.

`app/main.py` builds the settings singleton at import time
(`_settings = get_settings()`, and `get_settings` is lru_cached). So
whichever test module imports app code FIRST freezes the configuration
for the entire run — any `os.environ.setdefault` in a module collected
later has no effect.

That produced a genuine heisenbug: suites passed alone and in pairs, but
48 auth tests failed in the full run with "Token issuer not recognized",
because a suite that sets no issuer happened to trigger the import first.
pytest loads conftest.py before test modules, so setting the environment
here removes the ordering dependency entirely.

Individual suites still call setdefault for readability; those are no-ops
once these are in place, which is the intent.
"""
import os

TEST_CLERK_ISSUER = "https://test.clerk.accounts.dev"
TEST_SUPABASE_ISSUER = "https://testproject.supabase.co/auth/v1"

os.environ.setdefault("CLERK_ISSUER", TEST_CLERK_ISSUER)
os.environ.setdefault("CLERK_JWKS_URL", f"{TEST_CLERK_ISSUER}/.well-known/jwks.json")
os.environ.setdefault("SUPABASE_ISSUER", TEST_SUPABASE_ISSUER)
os.environ.setdefault(
    "SUPABASE_JWKS_URL", f"{TEST_SUPABASE_ISSUER}/.well-known/jwks.json"
)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# Mirror production: the apex and www are BOTH allowed, which is what
# makes the CORS-on-304 tests meaningful — a stale header from one
# host must never be replayed against a request from the other.
os.environ.setdefault(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://marketworks.in,https://www.marketworks.in",
)
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DISABLE_AUTH", "false")
