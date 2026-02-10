# Kite-Lab Production Dashboard - Deployment Guide

This guide covers deploying the Kite-Lab dashboard to production:
- **Frontend**: Vercel (Next.js)
- **Backend**: Railway (FastAPI + PostgreSQL)

## Prerequisites

1. GitHub repository with kite-api and kite-dashboard directories
2. Google Cloud Console project with OAuth 2.0 credentials
3. Vercel account (free tier works)
4. Railway account (Starter plan ~$5/month)

---

## Part 1: Backend Deployment (Railway)

### Step 1: Create Railway Project

1. Go to [railway.app](https://railway.app) and sign in
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository and the `kite-api` directory
4. Railway will detect the Dockerfile and deploy

### Step 2: Add PostgreSQL Database

1. In your Railway project, click "New" → "Database" → "PostgreSQL"
2. Railway automatically sets `DATABASE_URL` environment variable

### Step 3: Configure Environment Variables

In Railway dashboard → Variables, add:

```
JWT_SECRET=<generate with: openssl rand -hex 32>
ALLOWED_EMAILS=your-email@gmail.com
CORS_ORIGINS=http://localhost:3000,https://your-vercel-app.vercel.app
```

### Step 4: Deploy and Get URL

1. Railway will automatically deploy on push
2. Go to Settings → Networking → Generate Domain
3. Copy the URL (e.g., `https://kite-api-production.up.railway.app`)

### Step 5: Verify Deployment

```bash
curl https://your-railway-url.railway.app/api/health
# Should return: {"status":"healthy","database":"connected",...}
```

---

## Part 2: Frontend Deployment (Vercel)

### Step 1: Create Vercel Project

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Set Root Directory to `kite-dashboard`
5. Framework Preset: Next.js (auto-detected)

### Step 2: Configure Environment Variables

In Vercel dashboard → Settings → Environment Variables, add:

```
NEXT_PUBLIC_API_URL=https://your-railway-url.railway.app
NEXTAUTH_URL=https://your-vercel-url.vercel.app
NEXTAUTH_SECRET=<generate with: openssl rand -hex 32>
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
ALLOWED_EMAILS=your-email@gmail.com
```

### Step 3: Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create or select a project
3. Enable the Google+ API
4. Go to Credentials → Create Credentials → OAuth 2.0 Client IDs
5. Add authorized redirect URIs:
   - `http://localhost:3000/api/auth/callback/google` (development)
   - `https://your-vercel-url.vercel.app/api/auth/callback/google` (production)
6. Copy Client ID and Client Secret to Vercel

### Step 4: Deploy

1. Click "Deploy"
2. Vercel will build and deploy automatically
3. Get your production URL (e.g., `https://kite-dashboard.vercel.app`)

### Step 5: Update CORS

Back in Railway, update `CORS_ORIGINS` to include your Vercel URL:
```
CORS_ORIGINS=https://kite-dashboard.vercel.app
```

---

## Part 3: Verification

### Test Health Check
```bash
curl https://your-railway-url.railway.app/api/health
```

### Test Frontend
1. Visit your Vercel URL
2. Click "Sign in with Google"
3. Verify you can log in with an allowed email

### Test API Connection
1. After login, check browser DevTools → Network
2. Verify API calls to Railway are succeeding

---

## Troubleshooting

### "Access Denied" on Login
- Check ALLOWED_EMAILS is set correctly on both Vercel and Railway
- Ensure the email matches exactly (case-sensitive)

### CORS Errors
- Verify CORS_ORIGINS in Railway includes your Vercel URL
- Check there are no trailing slashes

### Database Connection Failed
- Railway should auto-configure DATABASE_URL
- Check the PostgreSQL service is running

### OAuth Redirect Mismatch
- Verify Google OAuth redirect URIs match exactly
- Include both http://localhost:3000 and production URL

---

## Cost Estimate

| Service | Plan | Cost |
|---------|------|------|
| Vercel | Hobby | Free |
| Railway | Starter | ~$5/month |
| Google OAuth | Free | Free |
| **Total** | | **~$5/month** |

---

## Local Development

### Backend
```bash
cd kite-api
source .venv/bin/activate
cp .env.example .env  # Edit with local values
uvicorn app.main:app --reload
```

### Frontend
```bash
cd kite-dashboard
cp .env.example .env.local  # Edit with local values
npm run dev
```

---

## CI/CD

Both Vercel and Railway support automatic deployments on push to main branch.

### Vercel
- Auto-deploys on push to main
- Preview deployments on PRs

### Railway
- Auto-deploys on push to main
- Can configure branch-specific deployments

---

Last updated: February 2026
