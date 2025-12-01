# Testing and Debugging Guide

## Overview

This guide covers how to test and debug the Categorization Bot application.

---

## Quick Health Checks

After deployment, verify the application is running:

```bash
# Quick check - just returns OK if server is running
curl https://your-backend-url.railway.app/health/quick

# Full health check - shows all service statuses
curl https://your-backend-url.railway.app/health
```

### Expected Response (Full Health Check)

```json
{
  "status": "healthy",
  "timestamp": "2025-12-01T10:30:00.000000",
  "services": {
    "api": {"status": "up"},
    "database": {"status": "up"},
    "gemini": {"status": "configured"},
    "pinecone": {"status": "configured"}
  }
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `healthy` | All services operational |
| `degraded` | Some services have issues but app is running |
| `up` | Service is running |
| `configured` | API key is set (doesn't verify connectivity) |
| `down` | Service is not available |
| `not_configured` | Missing API key or configuration |

---

## Running Tests Locally

### Prerequisites

```bash
cd backend
pip install -r requirements.txt
```

### Run All Tests

```bash
cd backend
pytest tests/ -v
```

### Run Specific Test Files

```bash
# Health check tests only
pytest tests/test_health.py -v

# API endpoint tests only
pytest tests/test_api_endpoints.py -v

# Error handling tests only
pytest tests/test_error_handling.py -v
```

### Run with Coverage

```bash
pytest tests/ -v --cov=. --cov-report=html
```

---

## Test Files

Place test documents in `backend/tests/test_files/`:

| File | Purpose |
|------|---------|
| `test_invoice.pdf` | Standard invoice testing |
| `test_receipt.png` | Image document testing |
| `test_scanned.pdf` | OCR/scanned document testing |
| `test_empty.pdf` | Error handling testing |

---

## Staging Environment Setup (Railway)

### Step 1: Create Staging Service

1. Go to Railway Dashboard
2. Click "New Project" or add service to existing project
3. Select your GitHub repo
4. Name it `backend-staging` or `frontend-staging`

### Step 2: Configure Environment Variables

Copy all environment variables from production, but use separate:
- Database (create a new PostgreSQL instance for staging)
- Optionally different API keys for testing

```
DATABASE_URL=postgresql://...staging-db...
GEMINI_API_KEY=your-key
PINECONE_API_KEY=your-key
CORS_ORIGINS=https://frontend-staging-xxx.up.railway.app
```

### Step 3: Set Up Branch Deployment

Configure Railway to deploy from a `staging` branch:

1. Go to Service Settings
2. Under "Deploy", select branch: `staging`
3. Now pushing to `staging` branch deploys to staging environment

### Workflow

```
Feature Branch → Staging → Production
     │              │           │
   develop      test here    main branch
```

```bash
# Deploy to staging
git checkout staging
git merge feature-branch
git push origin staging

# After testing, deploy to production
git checkout main
git merge staging
git push origin main
```

---

## Debugging Tips

### 1. Check Railway Logs

```bash
# View logs in Railway dashboard
# Or use Railway CLI:
railway logs
```

### 2. Common Issues

| Error | Likely Cause | Solution |
|-------|--------------|----------|
| "Service is temporarily busy" | Gemini API rate limit | Wait and retry, or upgrade API plan |
| "Server returned empty response" | Document unreadable | Try different document, check if scanned |
| "list indices must be integers" | Data format issue | Fixed in c0c7ce7, redeploy if needed |
| Database connection failed | DATABASE_URL wrong | Check Railway PostgreSQL URL |

### 3. Local Testing Against Production API

```bash
# Test a specific endpoint
curl -X POST https://your-backend.railway.app/research-vendor \
  -H "Content-Type: application/json" \
  -d '{"vendor_name": "Amazon"}'
```

### 4. Debug Mode

For more detailed logs locally:

```bash
# In .env file
DEBUG=true

# Run with auto-reload
uvicorn main:app --reload --log-level debug
```

---

## Monitoring Checklist

### After Each Deployment

- [ ] Check `/health` endpoint
- [ ] Test document upload
- [ ] Test vendor research
- [ ] Test categorization
- [ ] Check Railway logs for errors

### Weekly

- [ ] Review error logs
- [ ] Check API usage/quotas
- [ ] Verify database backups
- [ ] Test on multiple devices (desktop, mobile)

---

## Contact

For issues not covered here, check:
- Railway Dashboard for deployment logs
- Google Cloud Console for Gemini API status
- Pinecone Dashboard for ML service status
