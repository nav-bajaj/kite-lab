# Task 4: Remove SKIP_AUTH Bypass

**Severity:** CRITICAL
**Status:** `completed`
**User Action Required:** No

## Problem

Development configuration allows bypassing authentication:

```
kite-dashboard/.env.local:
SKIP_AUTH=true
```

If accidentally deployed to production, ALL authentication is bypassed.

## Risk

- Complete authentication bypass
- Anyone can access dashboard without login
- Exposes all portfolio data

## Fix Steps

### Step 1: Remove SKIP_AUTH from .env files (Claude)
- Remove from `.env.local`
- Remove from any other env files

### Step 2: Add production safeguard (Claude)
- Modify auth code to NEVER allow skip in production
- Add explicit check: `if (NODE_ENV === 'production') SKIP_AUTH = false`

### Step 3: Remove SKIP_AUTH support entirely (Claude)
- Remove the SKIP_AUTH logic from auth.ts
- Use proper mock auth for development testing instead

### Step 4: Update .env.example (Claude)
- Document that SKIP_AUTH should never be used
- Or remove mention entirely

## Breaking Changes

- **None in production** - this only affects development
- **Development** - will require Google OAuth setup for local dev

## Alternative for Development

Instead of SKIP_AUTH, use:
1. Proper Google OAuth with localhost redirect
2. Or mock NextAuth provider for testing

## Verification

```bash
# Ensure SKIP_AUTH is not in any env file
grep -r "SKIP_AUTH" . --include="*.env*"
# Should return nothing (or only .env.example with warning)
```
