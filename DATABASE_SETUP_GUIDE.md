# Database Setup Guide - Categorization-Bot

## Overview

This guide will help you set up the PostgreSQL database for persistent data storage in the Categorization-Bot application.

## Prerequisites

- PostgreSQL 12+ installed
- Python 3.8+ with pip
- Admin/superuser access to PostgreSQL

## Step 1: Install PostgreSQL

### Windows

1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run the installer
3. Set a password for the `postgres` user (remember this!)
4. Default port: 5432
5. Install pgAdmin 4 (included) for GUI management

### Mac

```bash
brew install postgresql
brew services start postgresql
```

### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Step 2: Create Database

### Option A: Using psql (Command Line)

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE categorization_bot;

# Create user (optional - recommended for production)
CREATE USER catbot_user WITH PASSWORD 'your_secure_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE categorization_bot TO catbot_user;

# Exit
\q
```

### Option B: Using pgAdmin

1. Open pgAdmin 4
2. Connect to your PostgreSQL server
3. Right-click "Databases" → "Create" → "Database"
4. Name: `categorization_bot`
5. Click "Save"

## Step 3: Configure Environment Variables

Create or update `.env` file in the `backend` directory:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/categorization_bot

# If you created a custom user:
# DATABASE_URL=postgresql://catbot_user:your_password@localhost:5432/categorization_bot

# Existing variables
GEMINI_API_KEY=your_gemini_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here

# Security
SECRET_KEY=your-secret-key-for-jwt-tokens
# Generate a strong secret key with: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 4: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This will install:
- SQLAlchemy (ORM)
- psycopg2-binary (PostgreSQL driver)
- alembic (migrations)
- passlib, bcrypt (password hashing)
- python-jose (JWT tokens)

## Step 5: Initialize Database

Run the initialization script:

```bash
cd backend
python init_database.py
```

This script will:
1. Test database connection
2. Create PostgreSQL extensions (pg_trgm for full-text search)
3. Create all database tables
4. Verify table creation
5. Create a test user

### Expected Output

```
==============================================================
CATEGORIZATION-BOT DATABASE INITIALIZATION
==============================================================

DATABASE INFORMATION
==============================================================
  Host: localhost
  Port: 5432
  Database: categorization_bot
  Username: postgres
  Password: ********
==============================================================

Step 1: Testing database connection...
✓ Database connection successful!

Step 2: Creating PostgreSQL extensions...
✓ Extensions created successfully!

Step 3: Creating database tables...
✓ All tables created successfully!

Step 4: Verifying tables...

  Found 11 tables:
    ✓ activity_log
    ✓ bank_statements
    ✓ bank_transactions
    ✓ categorizations
    ✓ documents
    ✓ reconciliation_matches
    ✓ saved_searches
    ✓ transactions
    ✓ user_corrections
    ✓ users
    ✓ vendor_research

✓ All expected tables found!

Step 5: Creating test user...
✓ Test user created successfully!
  Username: testuser
  Password: password123
  Email: test@example.com

==============================================================
✓ DATABASE INITIALIZATION COMPLETE!
==============================================================
```

## Step 6: Verify Database Setup

### Option 1: Using psql

```bash
psql -U postgres -d categorization_bot

# List all tables
\dt

# View table structure
\d users
\d documents
\d transactions

# Check test user
SELECT id, username, email, is_active FROM users;

# Exit
\q
```

### Option 2: Using pgAdmin

1. Open pgAdmin
2. Navigate to: Servers → PostgreSQL → Databases → categorization_bot → Schemas → public → Tables
3. You should see 11 tables
4. Right-click any table → View/Edit Data → All Rows

## Database Schema Overview

### Core Tables

1. **users** - User accounts and authentication
2. **documents** - Uploaded documents with processing status
3. **transactions** - Financial transactions extracted from documents
4. **vendor_research** - Cached vendor information
5. **categorizations** - AI/ML categorization results with confidence scores
6. **user_corrections** - User feedback for improving ML models

### Reconciliation Tables

7. **bank_statements** - Uploaded bank statements
8. **bank_transactions** - Individual bank transactions
9. **reconciliation_matches** - Matches between documents and bank transactions

### Supporting Tables

10. **activity_log** - Audit trail of all user actions
11. **saved_searches** - User's saved search queries

## Troubleshooting

### Connection Failed

**Error**: `could not connect to server`

**Solutions**:
- Check PostgreSQL is running:
  - Windows: Services → PostgreSQL
  - Mac: `brew services list`
  - Linux: `sudo systemctl status postgresql`
- Verify port 5432 is not blocked by firewall
- Check DATABASE_URL in `.env`

### Authentication Failed

**Error**: `password authentication failed`

**Solutions**:
- Verify password in DATABASE_URL matches PostgreSQL user password
- Check pg_hba.conf for authentication method (should allow md5 or scram-sha-256)
- Reset password: `ALTER USER postgres PASSWORD 'newpassword';`

### Permission Denied

**Error**: `permission denied to create extension`

**Solutions**:
- Extensions require superuser privileges
- Use postgres superuser account
- Or have admin create extensions manually:
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
  ```

### Database Does Not Exist

**Error**: `database "categorization_bot" does not exist`

**Solution**:
- Create the database first (see Step 2)

### Port Already in Use

**Error**: `port 5432 is already in use`

**Solutions**:
- Another PostgreSQL instance is running
- Stop other instance or use different port
- Update DATABASE_URL to use different port

## Migration Management (Future)

For database schema changes, use Alembic:

```bash
# Initialize Alembic (already done)
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "description of changes"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Production Considerations

### Security

1. **Use a dedicated database user** (not postgres superuser)
2. **Use strong passwords** (generated with `secrets.token_urlsafe(32)`)
3. **Enable SSL** for database connections
4. **Restrict pg_hba.conf** to specific IPs
5. **Set SECRET_KEY** for JWT tokens

### Performance

1. **Enable connection pooling** (configure in database.py)
2. **Create additional indexes** for frequently queried columns
3. **Regular VACUUM** and **ANALYZE**
4. **Monitor query performance** with pg_stat_statements

### Backup

```bash
# Backup
pg_dump -U postgres categorization_bot > backup.sql

# Restore
psql -U postgres -d categorization_bot < backup.sql

# Automated backups (cron job)
0 2 * * * pg_dump -U postgres categorization_bot > /backups/catbot_$(date +\%Y\%m\%d).sql
```

### Monitoring

- Use pgAdmin or pg_stat_statements for query monitoring
- Monitor disk space (PostgreSQL can grow quickly)
- Set up log rotation
- Monitor connection count

## Next Steps

After database setup is complete:

1. **Test the API endpoints** (see API_DOCUMENTATION.md)
2. **Update frontend** to use database-backed APIs
3. **Test user registration and login**
4. **Upload test documents** and verify persistence
5. **Test search and filtering**
6. **Set up backups** for production

## Database Maintenance

### Regular Tasks

```sql
-- Analyze database for query optimization
ANALYZE;

-- Clean up dead rows
VACUUM;

-- Full vacuum (requires exclusive lock)
VACUUM FULL;

-- Check database size
SELECT pg_size_pretty(pg_database_size('categorization_bot'));

-- Check table sizes
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### Performance Tuning

```sql
-- Check slow queries
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

## Support

For issues or questions:
- Check PostgreSQL logs: `/var/log/postgresql/` (Linux) or Data Directory\pg_log (Windows)
- PostgreSQL documentation: https://www.postgresql.org/docs/
- SQLAlchemy documentation: https://docs.sqlalchemy.org/

---

**Database Version**: PostgreSQL 12+
**Last Updated**: November 2025
