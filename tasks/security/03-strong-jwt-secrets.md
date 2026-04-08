# Task 3: Generate Strong JWT Secrets

**Severity:** CRITICAL
**Status:** `completed`
**User Action Required:** Yes (update Railway/Vercel env vars with strong secrets)

## Problem

Weak default JWT secrets are used:

```
JWT_SECRET=dev-secret-change-in-production
NEXTAUTH_SECRET=dev-secret-change-in-production
```

## Risk

- Attackers can forge authentication tokens
- Session hijacking
- Complete auth bypass

## Fix Steps

### Step 1: Generate strong secrets (Claude)
```bash
openssl rand -base64 32  # For JWT_SECRET
openssl rand -base64 32  # For NEXTAUTH_SECRET
```

### Step 2: Update .env.example with instructions (Claude)
- Add comments explaining secret generation
- Never commit actual secrets

### Step 3: Update production secrets (USER ACTION)

**Railway (Backend):**
1. Go to Railway dashboard → kite-api service
2. Environment variables section
3. Update `JWT_SECRET` with generated value

**Vercel (Frontend):**
1. Go to Vercel dashboard → kite-dashboard project
2. Settings → Environment Variables
3. Update `NEXTAUTH_SECRET` with generated value
4. Redeploy

### Step 4: Update local development .env files (USER ACTION)
- Update local `.env` files with strong secrets
- Different secrets for dev vs production

## Breaking Changes

- **All existing sessions invalidated** - users must re-login
- **No downtime** - just session reset

## Verification

```bash
# After updating, test login flow
# 1. Visit https://kite-lab.vercel.app
# 2. Should redirect to Google login
# 3. After login, should see dashboard
```
