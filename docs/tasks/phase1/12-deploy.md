# Task 12: Deploy Initial Shells to Vercel and Railway

**Status**: `pending`
**Blocked By**: #3, #4, #9, #10, #11
**Blocks**: None (Phase 1 complete)

## Objective

Deploy the frontend to Vercel and backend to Railway, verify everything works end-to-end.

## Tasks

- [ ] Create GitHub repository (or configure existing)
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Railway with PostgreSQL
- [ ] Configure environment variables
- [ ] Verify health endpoint
- [ ] Verify Google OAuth login
- [ ] Verify universe selector works
- [ ] Test API communication

## Repository Setup

### Option A: Monorepo (Recommended)

Keep both projects in kite-lab:
```
kite-lab/
├── kite-api/           # Backend
├── kite-dashboard/     # Frontend
├── data/               # Static data
├── scripts/            # Original scripts
└── ...
```

### Option B: Separate Repos

Create separate repositories:
- `kite-lab-api` - Backend only
- `kite-lab-dashboard` - Frontend only

## Deploy Backend to Railway

### 1. Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Navigate to backend
cd kite-api

# Initialize project
railway init

# Link to existing project (if created in dashboard)
railway link
```

### 2. Add PostgreSQL

1. Go to Railway dashboard (https://railway.app)
2. Open your project
3. Click "New" → "Database" → "PostgreSQL"
4. Wait for provisioning
5. DATABASE_URL is auto-injected

### 3. Configure Environment Variables

In Railway dashboard → Variables, add:

```bash
# Required
JWT_SECRET=<generate with: openssl rand -base64 32>
ALLOWED_EMAILS=your-email@gmail.com
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app

# Optional (for live data fetch)
KITE_API_KEY=your-kite-api-key
KITE_API_SECRET=your-kite-api-secret
```

### 4. Deploy

```bash
# Deploy from CLI
railway up

# Or configure auto-deploy from GitHub:
# Railway dashboard → Settings → Connect GitHub → Select repo
```

### 5. Get Public URL

After deployment:
- Railway dashboard → Settings → Domains
- Generate domain or add custom domain
- Note the URL (e.g., `https://kite-api-production.up.railway.app`)

### 6. Verify Backend

```bash
# Test health endpoint
curl https://your-railway-url.up.railway.app/api/health

# Expected response:
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2026-02-10T..."
}
```

## Deploy Frontend to Vercel

### 1. Create Vercel Project

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to frontend
cd kite-dashboard

# Deploy
vercel

# Follow prompts:
# - Link to existing project? No
# - Project name: kite-dashboard
# - Directory: ./
# - Override settings? No
```

### 2. Configure Environment Variables

In Vercel dashboard → Settings → Environment Variables:

```bash
NEXT_PUBLIC_API_URL=https://your-railway-url.up.railway.app
NEXTAUTH_URL=https://kite-dashboard.vercel.app
NEXTAUTH_SECRET=<generate with: openssl rand -base64 32>
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
ALLOWED_EMAILS=your-email@gmail.com
```

### 3. Update Google OAuth

In Google Cloud Console:
1. APIs & Services → Credentials → Your OAuth Client
2. Add authorized redirect URI:
   ```
   https://kite-dashboard.vercel.app/api/auth/callback/google
   ```

### 4. Update Railway CORS

Update `ALLOWED_ORIGINS` in Railway to include Vercel URL:
```bash
ALLOWED_ORIGINS=http://localhost:3000,https://kite-dashboard.vercel.app
```

### 5. Redeploy

```bash
# Redeploy frontend with new env vars
vercel --prod

# Redeploy backend to pick up CORS changes
cd kite-api && railway up
```

## Verification Checklist

### Backend (Railway)

- [ ] Health check returns OK
  ```bash
  curl https://your-api.railway.app/api/health
  ```
- [ ] Database connected
- [ ] CORS allows frontend origin

### Frontend (Vercel)

- [ ] Home page loads
- [ ] Redirects to /login if not authenticated
- [ ] Google OAuth works:
  - Click "Sign in with Google"
  - Redirects to Google
  - After auth, redirects back to dashboard
- [ ] Unauthorized email rejected (test with different Google account)
- [ ] Dashboard layout displays:
  - Sidebar visible on desktop
  - Mobile menu works on small screens
  - User avatar shows in navbar
- [ ] Universe selector:
  - All three options visible (NSE 500, N250, N100)
  - Clicking changes selection
  - Refresh preserves selection
- [ ] Theme toggle works (light/dark)

### API Communication

- [ ] Open DevTools → Network
- [ ] Verify API calls go to Railway backend
- [ ] Verify Authorization header present
- [ ] Verify universe parameter in requests

## Troubleshooting

### CORS Errors
```
Access to fetch at 'https://api...' has been blocked by CORS policy
```
**Fix**: Ensure `ALLOWED_ORIGINS` in Railway includes exact Vercel URL (no trailing slash)

### OAuth Redirect Error
```
Error 400: redirect_uri_mismatch
```
**Fix**: Add exact callback URL to Google Cloud Console authorized redirects

### Database Connection Error
```
{"status": "degraded", "database": "error: connection refused"}
```
**Fix**: Check DATABASE_URL in Railway variables, ensure PostgreSQL addon is provisioned

### 401 Unauthorized on API Calls
**Fix**: Verify JWT_SECRET matches between frontend session and backend validation

## Cost Summary

| Service | Tier | Cost |
|---------|------|------|
| Vercel | Hobby | Free |
| Railway | Starter | ~$5/month |
| PostgreSQL | Included | $0 |
| **Total** | | **~$5/month** |

## Next Steps

After Phase 1 is complete:
1. Document the deployed URLs
2. Update CLAUDE.md with deployment info
3. Begin Phase 2: Portfolio View

## Deployed URLs (Fill in after deployment)

```
Frontend: https://_________________.vercel.app
Backend:  https://_________________.railway.app
API Docs: https://_________________.railway.app/docs
```

---

*Last updated: February 2026*
