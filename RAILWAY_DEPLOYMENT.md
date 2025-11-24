# Railway Deployment Guide

## Prerequisites

- GitHub repository connected to Railway
- Railway account with PostgreSQL database provisioned
- API keys ready (Gemini, Pinecone)

---

## Deployment Architecture

Railway will run **two separate services**:

1. **Backend Service** (FastAPI)
   - Path: `Categorization-Bot/backend`
   - Port: Auto-assigned by Railway
   - Database: PostgreSQL (Railway-provided)

2. **Frontend Service** (React)
   - Path: `Categorization-Bot/frontend`
   - Port: Auto-assigned by Railway
   - Connects to backend API

---

## Step-by-Step Deployment

### 1. Create Backend Service

#### A. Add New Service
1. Go to Railway dashboard
2. Click **"New"** → **"GitHub Repo"**
3. Select your `categorization-bot` repository
4. Choose **"Deploy from a subdirectory"**
5. Set root directory: `Categorization-Bot/backend`

#### B. Configure Environment Variables

Go to **Variables** tab and add:

```bash
# API Keys
GEMINI_API_KEY=your_actual_gemini_api_key_here
PINECONE_API_KEY=your_actual_pinecone_api_key_here

# JWT Security (Generate new for production!)
# Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your_production_jwt_secret_key_here

# CORS Origins (Update after frontend deploys!)
CORS_ORIGINS=https://your-frontend-url.railway.app

# Python Settings
PYTHONUNBUFFERED=1
```

**Note:** `DATABASE_URL` is automatically set by Railway when you add PostgreSQL.

#### C. Add PostgreSQL Database
1. In your backend service, click **"New"** → **"Database"** → **"PostgreSQL"**
2. Railway automatically sets `DATABASE_URL` environment variable
3. Database will auto-initialize on first startup

#### D. Deploy Settings
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Watch Paths:** `Categorization-Bot/backend/**`

---

### 2. Create Frontend Service

#### A. Add Frontend Service
1. Click **"New"** → **"GitHub Repo"** (same repo)
2. Set root directory: `Categorization-Bot/frontend`

#### B. Update Frontend API URL

**Before deploying**, update the frontend to use the backend URL:

**File:** `frontend/src/App.js` or create `frontend/.env`

```bash
REACT_APP_API_URL=https://your-backend-service.railway.app
```

Or hardcode in `App.js`:
```javascript
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

#### C. Configure Environment Variables

```bash
REACT_APP_API_URL=https://your-backend-service.railway.app
```

#### D. Deploy Settings
- **Build Command:** `npm install && npm run build`
- **Start Command:** `npx serve -s build -p $PORT`
- **Watch Paths:** `Categorization-Bot/frontend/**`

---

### 3. Update CORS After Frontend Deploys

Once frontend is deployed, you'll get a URL like:
`https://categorization-bot-frontend.railway.app`

**Go back to backend service** and update:
```bash
CORS_ORIGINS=https://categorization-bot-frontend.railway.app
```

The backend will auto-redeploy with the new CORS settings.

---

## Environment Variables Checklist

### Backend Required Variables:
- [ ] `GEMINI_API_KEY` - Get from https://aistudio.google.com/app/apikey
- [ ] `PINECONE_API_KEY` - Get from https://www.pinecone.io/
- [ ] `SECRET_KEY` - Generate new for production
- [ ] `CORS_ORIGINS` - Set to frontend Railway URL
- [ ] `DATABASE_URL` - Auto-set by Railway (don't manually set)

### Frontend Required Variables:
- [ ] `REACT_APP_API_URL` - Backend Railway URL

---

## Security Checklist

Before deploying to production:

### ✅ Credentials
- [ ] Generated new `SECRET_KEY` for production
- [ ] Using production API keys (not development keys)
- [ ] Changed database password from default
- [ ] Removed any hardcoded secrets from code

### ✅ CORS
- [ ] `CORS_ORIGINS` set to exact frontend URL (not wildcard)
- [ ] Tested CORS from production frontend

### ✅ Rate Limiting
- [ ] Rate limiting configured (already in code)
- [ ] Tested with multiple rapid requests

### ✅ File Upload
- [ ] File validation working (already in code)
- [ ] Tested with invalid file types

### ✅ Database
- [ ] PostgreSQL provisioned on Railway
- [ ] Database auto-initializes on startup
- [ ] Connection string uses SSL (Railway default)

---

## Deployment Commands

### Deploy Backend Only:
```bash
git add Categorization-Bot/backend/
git commit -m "Update backend"
git push
```

### Deploy Frontend Only:
```bash
git add Categorization-Bot/frontend/
git commit -m "Update frontend"
git push
```

### Deploy Both:
```bash
git add .
git commit -m "Update application"
git push
```

Railway auto-deploys on push to your configured branch (usually `main`).

---

## Monitoring & Logs

### View Logs:
1. Go to Railway dashboard
2. Select your service (backend or frontend)
3. Click **"Logs"** tab
4. Real-time logs will appear

### Health Checks:

**Backend:**
- Health endpoint (after Week 2): `https://your-backend.railway.app/health`
- API docs: `https://your-backend.railway.app/docs`

**Frontend:**
- Should load without errors
- Check browser console for API connection errors

---

## Troubleshooting

### Backend Won't Start:
1. Check logs for errors
2. Verify all environment variables are set
3. Check `DATABASE_URL` is set by PostgreSQL service
4. Verify Python version in `runtime.txt` matches requirements

### Frontend Can't Connect to Backend:
1. Check `REACT_APP_API_URL` is correct
2. Verify CORS_ORIGINS includes frontend URL
3. Check backend is running (visit `/docs` endpoint)
4. Check browser console for CORS errors

### Database Connection Failed:
1. Verify PostgreSQL service is running
2. Check `DATABASE_URL` environment variable exists
3. Restart backend service
4. Check Railway PostgreSQL service logs

### Rate Limiting Issues:
1. Railway uses shared IPs, might hit limits faster
2. Consider adjusting rate limits in production
3. Implement user-specific rate limiting (future enhancement)

---

## Cost Optimization

### Railway Free Tier:
- $5 free credit per month
- Enough for testing and small projects

### Production Recommendations:
1. **Backend:** Shared CPU, 512MB RAM (~$5/month)
2. **Frontend:** Static hosting or shared CPU (~$3/month)
3. **PostgreSQL:** Shared instance (~$5/month)
4. **Total:** ~$13/month (minus $5 free credit = $8/month)

### Cost Saving Tips:
- Use Railway's free tier for development
- Scale up only when needed
- Monitor API usage (Gemini/Pinecone costs)
- Implement caching to reduce API calls

---

## Post-Deployment Testing

### 1. Test Authentication:
```bash
curl -X POST https://your-backend.railway.app/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123","username":"test"}'
```

### 2. Test Login:
```bash
curl -X POST https://your-backend.railway.app/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

### 3. Test File Upload (with JWT token):
```bash
curl -X POST https://your-backend.railway.app/process-pdf \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@test.pdf"
```

### 4. Test Rate Limiting:
```bash
# Run this multiple times quickly
for i in {1..15}; do
  curl -X GET https://your-backend.railway.app/categories
done
# Should get 429 Too Many Requests after 10-20 requests
```

---

## Rollback Strategy

If deployment fails:

1. **Quick Rollback:**
   - Railway: Go to deployments → Click "Redeploy" on previous working version

2. **Code Rollback:**
   ```bash
   git revert HEAD
   git push
   ```

3. **Database Rollback:**
   - Railway keeps automatic backups
   - Go to PostgreSQL service → Backups → Restore

---

## Next Steps After Deployment

1. **Week 2 - Add Health Checks:**
   - Create `/health` endpoint for monitoring
   - Set up Railway health checks

2. **Week 3 - Performance:**
   - Add Redis caching (Railway addon)
   - Optimize database queries

3. **Week 4 - Monitoring:**
   - Set up error tracking (Sentry)
   - Add performance monitoring (New Relic)

---

## Support

If you encounter issues:
1. Check Railway documentation: https://docs.railway.app/
2. Review logs in Railway dashboard
3. Check GitHub issues: https://github.com/anthropics/claude-code/issues

---

**Last Updated:** 2025-11-24
**Status:** Ready for deployment
