# 🚀 Railway Deployment Checklist

Complete this checklist step-by-step to ensure successful deployment.

---

## ✅ Pre-Deployment Verification

### Files Ready:
- [x] `backend/Procfile` - Exists
- [x] `backend/railway.json` - Exists
- [x] `backend/runtime.txt` - Exists (Python 3.13)
- [x] `backend/requirements.txt` - Exists
- [x] `frontend/nixpacks.toml` - Exists
- [x] `frontend/package.json` - Exists
- [x] `frontend/package-lock.json` - Synced
- [x] All changes committed and pushed to GitHub

---

## 📦 Step 1: Create Railway Project

1. Go to https://railway.app/dashboard
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose: `Elden-Development/Categorization-Bot`
5. Railway creates your project

---

## 🗄️ Step 2: Add PostgreSQL Database

1. In your Railway project, click **"New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway automatically creates `DATABASE_URL` variable
4. ✅ Database is ready (no configuration needed)

---

## 🔧 Step 3: Configure Backend Service

### 3.1 Set Root Directory

1. Click on the **backend service** (auto-created by Railway)
2. Go to **Settings** tab
3. Find **"Source"** section
4. Set **"Root Directory"** to: `backend`
5. Click **"Save"**

### 3.2 Add Environment Variables

Click on backend service → **"Variables"** tab → Add these:

#### Required Variables:

```bash
# JWT Secret (IMPORTANT: Use the generated one below)
SECRET_KEY=s4IT5I5__Vp1GVUuzZ-MFQHcHWqXlsNz140a644OOOw

# Google Gemini API
GEMINI_API_KEY=<your-production-gemini-key>

# Pinecone Vector Database
PINECONE_API_KEY=<your-production-pinecone-key>

# CORS Origins (Update after frontend deploys)
CORS_ORIGINS=http://localhost:3000

# Database URL (Reference Railway PostgreSQL)
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

#### How to Reference Database:
- Type `${{` and Railway will show autocomplete
- Select `Postgres.DATABASE_URL`
- Railway automatically links to your database

### 3.3 Verify Build Settings

Railway should detect:
- ✅ Python 3.13 from `runtime.txt`
- ✅ Install from `requirements.txt`
- ✅ Start command from `Procfile`: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3.4 Deploy Backend

1. Click **"Deploy"** (or it auto-deploys)
2. Watch the build logs
3. Wait for: **"Build successful"** and **"Deployment successful"**
4. Copy the **public URL** from Settings → Networking
   - Example: `https://categorization-bot-production.up.railway.app`

---

## 🎨 Step 4: Configure Frontend Service

### 4.1 Create Frontend Service

1. In the same project, click **"New"**
2. Select **"GitHub Repo"**
3. Choose the same repository
4. Railway creates a new service

### 4.2 Set Root Directory

1. Click on the **frontend service**
2. Go to **Settings** tab
3. Find **"Source"** section
4. Set **"Root Directory"** to: `frontend`
5. Click **"Save"**

### 4.3 Add Environment Variable

Click on frontend service → **"Variables"** tab → Add:

```bash
# Backend API URL (use the backend URL you copied)
REACT_APP_API_URL=https://categorization-bot-production.up.railway.app
```

**IMPORTANT:** Replace with YOUR actual backend URL from Step 3.4

### 4.4 Deploy Frontend

1. Click **"Deploy"** (or it auto-deploys)
2. Watch the build logs:
   - ✅ `npm ci` installs dependencies
   - ✅ `npm run build` builds React app
   - ✅ `npx serve` starts the server
3. Wait for deployment success
4. Copy the **public URL** from Settings → Networking
   - Example: `https://categorization-bot-frontend.up.railway.app`

---

## 🔄 Step 5: Update Backend CORS

Now that frontend is deployed, update backend CORS:

1. Go to **backend service** → **"Variables"** tab
2. Find `CORS_ORIGINS` variable
3. Update to include both URLs:

```bash
CORS_ORIGINS=https://categorization-bot-frontend.up.railway.app,http://localhost:3000
```

4. Click **"Redeploy"** backend for changes to take effect

---

## ✅ Step 6: Verify Deployment

### Test Backend:

1. Visit: `https://your-backend-url.railway.app/docs`
2. You should see FastAPI Swagger documentation
3. Try a simple endpoint like `/categories`

### Test Frontend:

1. Visit: `https://your-frontend-url.railway.app`
2. You should see the login page
3. Check browser console (F12) for errors
4. Verify no CORS errors

### Test Full Flow:

1. **Register a new user** or use test credentials:
   ```
   Email: test@example.com
   Password: password123
   ```
2. **Upload a test document** (PDF or image)
3. **Click "Research & Categorize"**
4. Verify the categorization works

---

## 🚨 Troubleshooting

### Backend Issues:

**"Application failed to respond"**
- Check logs for errors
- Verify `DATABASE_URL` is set correctly
- Check all required environment variables are set

**"Module not found" errors**
- Verify `requirements.txt` is complete
- Check root directory is set to `backend`

**Database connection errors**
- Verify PostgreSQL service is running
- Check `DATABASE_URL` variable references `${{Postgres.DATABASE_URL}}`

### Frontend Issues:

**"Cannot connect to backend"**
- Verify `REACT_APP_API_URL` is set correctly
- Check backend URL is accessible
- Check for CORS errors in browser console

**"npm ci" fails**
- Verify `package-lock.json` is committed
- Make sure it's in sync with `package.json`

**Build fails**
- Check build logs for specific errors
- Verify root directory is set to `frontend`

---

## 💰 Expected Costs

### Railway Pricing:

- **PostgreSQL:** ~$5/month
- **Backend Service:** ~$5/month
- **Frontend Service:** ~$3/month
- **Total:** ~$13/month
- **After $5 free credit:** ~$8/month

### Free Tier:

- $5 credit per month
- Good for testing
- No credit card required initially

---

## 🎯 Post-Deployment Tasks

### Create Test User:

If needed, you can create a test user via the API:

```bash
curl -X POST https://your-backend-url.railway.app/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourcompany.com",
    "username": "admin",
    "password": "your-secure-password"
  }'
```

### Monitor Usage:

1. Railway Dashboard → Project → "Metrics"
2. Watch CPU, Memory, Network usage
3. Monitor costs in "Usage" tab

### Set Up Alerts:

1. Project Settings → "Notifications"
2. Add email for deployment failures
3. Set budget alerts

---

## 📝 Production Security Checklist

- [ ] Changed SECRET_KEY from local environment
- [ ] Using production API keys (not dev keys)
- [ ] CORS_ORIGINS includes only your frontend URL
- [ ] .env file NOT committed to git
- [ ] Database backups enabled in Railway
- [ ] Environment variables properly set
- [ ] All secrets stored in Railway, not in code

---

## 🎉 Success Criteria

Your deployment is successful when:

✅ Backend `/docs` endpoint loads
✅ Frontend loads without errors
✅ Login/register works
✅ File upload succeeds
✅ Categorization completes
✅ No CORS errors in console
✅ Database persists data between sessions

---

**Date Created:** 2025-11-24
**Version:** 1.0.0
**Status:** Ready for Deployment

**Backend URL:** `_____________________________`  (fill in after deploy)

**Frontend URL:** `_____________________________` (fill in after deploy)
