# Task 6: Add Authentication to API Endpoints

**Severity:** HIGH
**Status:** `completed`
**User Action Required:** No

## Problem

API endpoints were publicly accessible without authentication:
- `/api/jobs` - Create, list, cancel jobs
- `/api/portfolio` - View portfolio data
- `/api/metrics` - View performance metrics
- `/api/trades` - View trade history
- `/api/positions` - View live positions
- `/api/schedule` - Manage scheduled jobs
- `/api/sync` - Sync data
- `/api/rebalance` - Rebalance operations

## Solution Implemented

### Backend Changes

Added `Depends(get_current_user)` to all sensitive API endpoints:

- `kite-api/app/api/jobs.py` - All endpoints require auth
- `kite-api/app/api/portfolio.py` - All endpoints require auth
- `kite-api/app/api/metrics.py` - All endpoints require auth
- `kite-api/app/api/trades.py` - All endpoints require auth
- `kite-api/app/api/positions.py` - All endpoints except market-status require auth
- `kite-api/app/api/schedule.py` - All endpoints require auth
- `kite-api/app/api/sync.py` - All endpoints require auth
- `kite-api/app/api/rebalance.py` - All endpoints require auth

Added token creation endpoint:
- `POST /api/auth/token` - Creates JWT for authenticated users

### Frontend Changes

Created token exchange flow:
- `kite-dashboard/src/app/api/backend-token/route.ts` - Next.js API route that:
  1. Verifies NextAuth session server-side
  2. Requests JWT from backend
  3. Returns token to client

- `kite-dashboard/src/contexts/api-auth-context.tsx` - React context that:
  1. Gets backend token after login
  2. Stores token in state
  3. Sets global token for API client

- `kite-dashboard/src/lib/api-client.ts` - Updated to:
  1. Store global auth token
  2. Automatically include token in all requests
  3. Support `skipAuth` option for public endpoints

## Public Endpoints (No Auth Required)

- `GET /api/health` - Health check
- `GET /api/positions/market-status` - NSE market status
- `GET /api/system/status` - System status (basic info only)
- `GET /api/system/login-url` - OAuth login URL
- `GET /api/system/callback` - OAuth callback

## Testing

After deployment:
1. Visit https://kite-lab.vercel.app
2. Log in with Google
3. Verify dashboard loads and shows data
4. Check browser console for any auth errors

## Breaking Changes

- All API calls now require authentication
- Frontend automatically handles token exchange
- First request after login may have slight delay while getting token
