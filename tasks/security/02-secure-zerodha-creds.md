# Task 2: Secure Zerodha API Credentials

**Severity:** CRITICAL
**Status:** `completed`
**User Action Required:** Optional - rotate keys as best practice

## Problem

Zerodha API credentials are in `.env` files:

```
.env and kite-api/.env contain:
KITE_API_KEY=pidvs82gfxwghfyi
KITE_API_SECRET=pydvv7oztrvma8xz6gbafsu7sy2x2t9n
```

## Risk

- API key abuse (rate limits, bans)
- Unauthorized trading if access token obtained
- Account compromise

## Fix Steps

### Step 1: Update .gitignore (Claude)
- Ensure `.env` patterns are in `.gitignore`
- Add explicit patterns for all env files

### Step 2: Create .env.example templates (Claude)
- Create `.env.example` with placeholder values
- Document required environment variables

### Step 3: Rotate API credentials (USER ACTION)
1. Go to https://developers.kite.trade/
2. Navigate to your app settings
3. Regenerate API key and secret
4. Update local `.env` files with new credentials
5. Update Railway environment variables

### Step 4: Remove old .env from history if committed (Claude)
- Check if `.env` files were ever committed
- Remove from history if found

## Breaking Changes

- **Pipeline scripts will fail** until new credentials are configured locally
- **Production API** will fail until Railway env vars are updated

## Verification

```bash
# Test login works with new credentials
python scripts/login_and_save_token.py

# Verify production
curl https://kite-lab-production.up.railway.app/api/system/status
```
