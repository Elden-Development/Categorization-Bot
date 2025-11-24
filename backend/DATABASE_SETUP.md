# Database Setup Guide

## Overview

Your Categorization Bot now has **full data persistence** integrated! This means:
- ✅ All documents and transactions are saved to PostgreSQL
- ✅ User authentication with JWT tokens
- ✅ Vendor research results are cached
- ✅ Categorization history with confidence scores
- ✅ User corrections tracked for ML improvement
- ✅ Bank statement reconciliation history
- ✅ Complete audit trail of all actions
- ✅ Transaction search and filtering

## Quick Start

### 1. Install PostgreSQL

**Windows:**
- Download from: https://www.postgresql.org/download/windows/
- Run installer and set a password for the `postgres` user
- Keep the default port (5432)

**Mac (with Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create the Database

Open PostgreSQL command line (psql):

**Windows:** Use SQL Shell (psql) from Start Menu

**Mac/Linux:**
```bash
psql postgres
```

Then run:
```sql
CREATE DATABASE categorization_bot;
\q
```

### 3. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and update:
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/categorization_bot
   SECRET_KEY=<generate-random-key>
   GEMINI_API_KEY=<your-gemini-key>
   ```

3. Generate a secure SECRET_KEY:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

### 4. Initialize the Database

Run the initialization script:
```bash
python init_database.py
```

This will:
- Create all database tables
- Set up indexes for performance
- Create a test user account
- Verify everything is working

**Test User Credentials:**
- Username: `testuser`
- Password: `password123`
- Email: `test@example.com`

### 5. Start the Server

```bash
uvicorn main:app --reload
```

The server will:
- Test database connection on startup
- Initialize tables if needed
- Show connection status in console

## Features Now Available

### 1. User Authentication

Register a new user:
```bash
POST /register
{
  "username": "myuser",
  "email": "user@example.com",
  "password": "securepassword"
}
```

Login:
```bash
POST /login
{
  "username": "myuser",
  "password": "securepassword"
}
```

Returns JWT token for authenticated requests.

### 2. Document History

All processed documents are saved with:
- Upload timestamp
- Processing status
- Extracted data
- Verification results

Get your documents:
```bash
GET /documents?skip=0&limit=100
Authorization: Bearer <your-token>
```

### 3. Transaction Search

Search transactions:
```bash
POST /transactions/search
Authorization: Bearer <your-token>
{
  "search_query": "Amazon",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "min_amount": 10.00,
  "max_amount": 1000.00
}
```

### 4. Vendor Research Cache

Vendor research results are automatically cached:
- First search: Queries Google and saves result
- Subsequent searches: Returns cached result instantly
- Reduces API calls and improves speed

### 5. Categorization History

All categorizations are saved with:
- Category, subcategory, ledger type
- Confidence scores
- Method used (ML, Gemini, manual)
- User approval/modifications
- Timestamp

### 6. User Corrections

Track corrections to improve ML:
- Original vs corrected categorization
- Correction reason
- Learning weight
- Training application status

### 7. Bank Statement Reconciliation

Upload bank statements:
```bash
POST /parse-bank-statement
Authorization: Bearer <your-token>
```

Reconciliation history saved:
- Match confidence scores
- Match type (auto, manual, suggested)
- User confirmations
- Complete audit trail

### 8. Activity Log

Every action is logged:
- Document uploads
- Categorizations
- Corrections
- Reconciliations
- Login/logout

Get activity:
```bash
GET /activity?skip=0&limit=50
Authorization: Bearer <your-token>
```

## Database Schema

The system includes these tables:

1. **users** - User accounts
2. **documents** - Uploaded documents
3. **transactions** - Extracted transactions
4. **vendor_research** - Cached vendor data
5. **categorizations** - AI/ML categorizations
6. **user_corrections** - User feedback
7. **bank_statements** - Bank statement uploads
8. **bank_transactions** - Individual bank transactions
9. **reconciliation_matches** - Document-bank matches
10. **activity_log** - Audit trail
11. **saved_searches** - User saved searches

## Backward Compatibility

The app **still works without authentication**:
- Existing functionality remains unchanged
- Non-authenticated users can still use all features
- Data just won't be saved to database
- Perfect for testing or guest usage

To use with authentication:
1. Login to get JWT token
2. Add `Authorization: Bearer <token>` header to requests
3. All data is automatically saved to your account

## Common Issues

### "Database connection failed"

**Solution:**
1. Check PostgreSQL is running:
   ```bash
   # Windows
   services.msc -> PostgreSQL

   # Mac
   brew services list

   # Linux
   sudo systemctl status postgresql
   ```

2. Verify DATABASE_URL in `.env`
3. Check password is correct
4. Ensure database exists: `psql -l`

### "Could not create tables"

**Solution:**
1. Make sure user has permissions:
   ```sql
   GRANT ALL PRIVILEGES ON DATABASE categorization_bot TO postgres;
   ```

2. Drop and recreate database if needed:
   ```sql
   DROP DATABASE categorization_bot;
   CREATE DATABASE categorization_bot;
   ```

3. Run `python init_database.py` again

### "Module 'crud' not found"

**Solution:**
Make sure you're in the backend directory:
```bash
cd backend
python init_database.py
```

## Production Deployment

For production, make sure to:

1. **Use strong SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Use production database:**
   ```env
   DATABASE_URL=postgresql://user:pass@your-db-host:5432/categorization_bot
   ```

3. **Enable SSL for database:**
   ```env
   DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
   ```

4. **Set secure CORS origins:**
   ```env
   CORS_ORIGINS=https://yourdomain.com
   ```

5. **Use environment-specific settings:**
   - Disable DEBUG mode
   - Use connection pooling
   - Set up database backups
   - Monitor logs

## Backup & Recovery

### Backup Database

```bash
pg_dump -U postgres -d categorization_bot > backup.sql
```

### Restore Database

```bash
psql -U postgres -d categorization_bot < backup.sql
```

### Automated Backups

Set up daily backups (Linux/Mac):
```bash
# Add to crontab
0 2 * * * pg_dump -U postgres categorization_bot > /backups/db_$(date +\%Y\%m\%d).sql
```

## Advanced Configuration

### Connection Pooling

For high-traffic production, edit `database.py`:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,        # Number of connections to maintain
    max_overflow=20,     # Additional connections when needed
    pool_pre_ping=True,  # Check connection before using
    echo=False
)
```

### Full-Text Search

The database includes full-text search indexes:
- Transaction vendor names
- Transaction descriptions
- Bank transaction descriptions

Uses PostgreSQL's `pg_trgm` extension for fuzzy matching.

## Support

If you encounter issues:

1. Check logs: `uvicorn main:app --log-level debug`
2. Test connection: `python -c "from database import test_connection; test_connection()"`
3. Verify tables: `python -c "from database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"`
4. Review DATABASE_SETUP.md (this file)

## Next Steps

1. ✅ Database is integrated
2. 🔄 Update frontend to use authentication
3. 🔄 Add login/registration UI
4. 🔄 Add transaction history view
5. 🔄 Add search functionality to frontend
6. 🔄 Deploy to production

Your backend is **fully ready** for data persistence!
