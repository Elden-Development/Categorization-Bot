# Local Testing Guide

## Quick Start

Your local servers are running! 🎉

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

---

## Test User Credentials

```
Email: test@example.com
Password: password123
Role: admin
```

---

## Testing Checklist

### ✅ 1. Authentication Flow

**Register a New User:**
1. Go to http://localhost:3000
2. Click **Register** (if available)
3. Fill in:
   - Email: `yourname@test.com`
   - Username: `yourname`
   - Password: `yourpassword`
4. Submit

**Login:**
1. Go to http://localhost:3000
2. Click **Login**
3. Use test credentials above
4. You should be redirected to the main dashboard

---

### ✅ 2. Document Processing

**Upload a Test Document:**
1. Login first
2. Navigate to **Upload** or **Process Document** tab
3. Select a PDF file or image (invoice, receipt, tax form)
4. Choose schema type (1040, payroll, generic, etc.)
5. Click **Process**
6. Should see:
   - Upload progress
   - Processing status
   - Extracted data displayed

**Expected Behavior:**
- Only PDF/image files accepted (✅ validation working)
- Files over 25MB rejected (✅ size limit working)
- .exe, .txt files rejected (✅ type validation working)

---

### ✅ 3. Transaction Categorization

**Categorize a Transaction:**
1. After processing a document
2. View extracted transaction data
3. Click **Categorize** or it auto-categorizes
4. Should see:
   - Suggested category (e.g., "Office Supplies")
   - Subcategory
   - Confidence score (0-100)
   - Explanation

**Test Low Confidence:**
- Upload an ambiguous invoice
- Should see confidence < 70
- Item appears in Review Queue

---

### ✅ 4. Review Queue

**Check Items Needing Review:**
1. Navigate to **Review Queue** tab
2. Should see:
   - Low-confidence categorizations
   - Color-coded indicators (green/yellow/red)
   - Statistics (total items, critical priority)

**Approve/Correct:**
1. Click on an item
2. Review the categorization
3. Either:
   - **Approve** (if correct)
   - **Edit** category and **Save Correction**
4. Item removed from queue

---

### ✅ 5. Bank Reconciliation

**Upload Bank Statement:**
1. Navigate to **Bank Reconciliation** tab
2. Upload a bank statement (CSV or PDF)
3. Should see:
   - List of bank transactions
   - Auto-matching with processed documents
   - Match confidence scores

**Manual Match:**
1. Find unmatched transaction
2. Click **Match Manually**
3. Select corresponding document
4. Confirm match

---

### ✅ 6. Vendor Research

**Research a Vendor:**
1. During categorization
2. If confidence is low, **Enhanced Research** triggers
3. Should see:
   - Industry classification
   - Business type
   - Common expense categories
   - Confidence explanation

---

### ✅ 7. Security Features Testing

**Test Rate Limiting:**
```bash
# Open terminal and run:
cd "C:\EldenDev\Categorization-Bot\Categorization-Bot\backend"

# Should succeed (under limit)
for i in {1..5}; do curl http://localhost:8000/categories; done

# Should fail with 429 after 10-15 requests
for i in {1..20}; do curl http://localhost:8000/categories; done
```

**Test File Upload Validation:**
```bash
# Should fail - invalid file type
curl -X POST http://localhost:8000/process-pdf \
  -F "file=@C:\Windows\System32\notepad.exe"

# Should fail - no file extension
echo "test" > testfile
curl -X POST http://localhost:8000/process-pdf \
  -F "file=@testfile"
```

**Test CORS:**
1. Open browser console (F12)
2. Try making request from different origin:
```javascript
fetch('http://localhost:8000/categories')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
```
- Should work (localhost is allowed)

**Test Input Validation:**
1. Try submitting empty vendor name
2. Try confidence threshold > 100 or < 0
3. Should see validation errors

---

### ✅ 8. API Documentation

**Explore Interactive API Docs:**
1. Go to http://localhost:8000/docs
2. You'll see Swagger UI with all 30+ endpoints
3. Click on any endpoint (e.g., `/categories`)
4. Click **"Try it out"**
5. Click **"Execute"**
6. See the response

**Test Authentication in Docs:**
1. Click **Authorize** button (top right)
2. Login first to get JWT token
3. Copy token from browser localStorage or network tab
4. Paste in format: `Bearer YOUR_TOKEN_HERE`
5. Now you can test protected endpoints

---

## Common Issues & Solutions

### Issue: "Connection Refused" Error
**Solution:**
- Check if backend is running: http://localhost:8000/docs
- Check if frontend is running: http://localhost:3000
- Restart servers if needed

### Issue: "401 Unauthorized" on API Calls
**Solution:**
- User not logged in
- JWT token expired (7 days by default)
- Login again to get new token

### Issue: File Upload Fails
**Solution:**
- Check file size (< 25MB)
- Check file type (PDF, PNG, JPG, CSV only)
- Check backend logs for errors

### Issue: Categorization Takes Too Long
**Solution:**
- Normal for first request (initializing Gemini/Pinecone)
- Subsequent requests faster (~5-10 seconds)
- Check API keys are valid in `.env`

### Issue: Database Errors
**Solution:**
- Check PostgreSQL is running
- Check `DATABASE_URL` in `.env`
- Check backend logs for connection errors
- Restart backend server

---

## Performance Benchmarks

**Expected Processing Times:**

| Operation | Time | Notes |
|-----------|------|-------|
| Login | < 1s | Fast |
| Document upload | 12-18s | Depends on file size |
| Categorization | 5-10s | First request slower |
| Bank reconciliation | 3-5s | Per statement |
| Vendor research | 7-10s | Enhanced research |

**Rate Limits:**

| Endpoint | Limit | Per |
|----------|-------|-----|
| Global default | 50 | minute |
| `/process-pdf` | 10 | minute |
| `/categorize-transaction-smart` | 20 | minute |
| `/research-vendor-enhanced` | 15 | minute |

---

## Viewing Logs

### Backend Logs:
The backend terminal shows all requests:
```
INFO: 127.0.0.1:52347 - "GET /me HTTP/1.1" 200 OK
INFO: 127.0.0.1:52347 - "POST /process-pdf HTTP/1.1" 200 OK
```

### Frontend Logs:
1. Open browser console (F12)
2. See React logs and API call responses
3. Check for errors (red text)

### Database Logs:
- Check backend terminal for SQL errors
- PostgreSQL logs in system logs (if needed)

---

## Test Data

**Sample Test Documents:**
- Look in `Categorization-Bot/` root for `test_invoice_*.pdf`
- Use any PDF invoice, receipt, or tax form
- Images of documents also work

**Sample Bank Statement:**
- Create CSV with columns: Date, Description, Amount
- Or use PDF bank statement

---

## Next Steps After Local Testing

1. **If everything works locally:**
   - ✅ Proceed with Railway deployment
   - Follow `RAILWAY_DEPLOYMENT.md`

2. **If issues found:**
   - Document the issue
   - Check logs for errors
   - Fix code before deploying

3. **Before deploying to Railway:**
   - ✅ Regenerate all API keys for production
   - ✅ Update CORS_ORIGINS in `.env`
   - ✅ Test security features work
   - ✅ Commit Railway config files to git

---

## Stopping the Servers

When you're done testing:

**Stop Backend:**
```bash
# Press Ctrl+C in the backend terminal
# Or kill the process
```

**Stop Frontend:**
```bash
# Press Ctrl+C in the frontend terminal
# Or kill the process
```

**Or kill all:**
```bash
# Find process IDs
netstat -ano | findstr :3000
netstat -ano | findstr :8000

# Kill processes
taskkill /PID <process_id> /F
```

---

**Happy Testing!** 🚀

If you find any bugs or issues, document them before deploying to production.
