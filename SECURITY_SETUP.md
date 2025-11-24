# Security Setup Guide

## 🚨 CRITICAL: If Credentials Were Exposed

If your `.env` file was committed to git with real credentials, follow these steps immediately:

### 1. Regenerate All API Keys

#### Gemini API Key
1. Go to https://aistudio.google.com/app/apikey
2. Delete the compromised key: `AIzaSyBPF8uQ60k0RBCoYgxmGoXga7exchVhxkc`
3. Create a new API key
4. Update your `.env` file with the new key

#### Pinecone API Key
1. Go to https://app.pinecone.io/
2. Navigate to API Keys section
3. Delete the compromised key (starts with `pcsk_3EcpqZ_...`)
4. Generate a new API key
5. Update your `.env` file with the new key
6. **Important**: You may need to recreate your Pinecone index with the new key

#### Database Password
1. Connect to PostgreSQL:
   ```bash
   psql -U postgres
   ```
2. Change the password:
   ```sql
   ALTER USER postgres WITH PASSWORD 'new_secure_password_here';
   ```
3. Update `DATABASE_URL` in `.env` with the new password

#### JWT Secret Key
1. Generate a new secure secret key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Update `SECRET_KEY` in `.env`
3. **Note**: This will invalidate all existing user sessions

### 2. Remove Credentials from Git History

If this was a git repository and `.env` was committed:

```bash
# Install git-filter-repo if not already installed
pip install git-filter-repo

# Remove .env from entire git history
git filter-repo --path .env --invert-paths

# Force push to remote (if applicable)
git push origin --force --all
```

Or use BFG Repo-Cleaner:
```bash
# Download from: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files .env
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### 3. Verify Security

After regenerating credentials:
- [ ] `.env` is listed in `.gitignore`
- [ ] `.env` is not in git staging area: `git status`
- [ ] Old API keys are deleted from provider dashboards
- [ ] Database password changed
- [ ] New JWT secret generated
- [ ] `.env.example` exists with no real credentials
- [ ] All team members have updated their local `.env` files

---

## Initial Setup for New Developers

### 1. Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your credentials:
   - Get Gemini API key from https://aistudio.google.com/app/apikey
   - Get Pinecone API key from https://www.pinecone.io/
   - Set your database credentials
   - Generate a JWT secret: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

3. **NEVER** commit the `.env` file to version control

### 2. Database Setup

1. Create the PostgreSQL database:
   ```bash
   createdb categorization_bot
   ```

2. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/categorization_bot
   ```

3. Run database initialization:
   ```bash
   cd backend
   python -c "from database import init_db; init_db()"
   ```

### 3. Pinecone Setup

1. Create a Pinecone account at https://www.pinecone.io/
2. Create a new index with these settings:
   - **Name**: `categorization-index` (or your preferred name)
   - **Dimensions**: 768
   - **Metric**: cosine
   - **Region**: Choose nearest to your location
3. Copy the API key to your `.env` file
4. Update `ml_categorization.py` with your index name if different

### 4. Gemini API Setup

1. Go to https://aistudio.google.com/app/apikey
2. Create a new API key
3. Copy it to your `.env` file as `GEMINI_API_KEY`

---

## Security Best Practices

### Environment Variables
- ✅ Always use `.env` files for secrets
- ✅ Use `.env.example` as a template (no real values)
- ✅ Add `.env` to `.gitignore`
- ❌ Never hardcode secrets in source code
- ❌ Never commit `.env` files
- ❌ Never share `.env` files in chat/email

### API Keys
- Rotate keys every 90 days
- Use separate keys for dev/staging/production
- Monitor API key usage for anomalies
- Set usage limits/quotas where possible

### Database
- Use strong passwords (16+ characters, mixed case, numbers, symbols)
- Never use default passwords like "postgres" or "admin"
- Use connection pooling in production
- Enable SSL for database connections in production

### JWT Tokens
- Use strong secret keys (32+ bytes)
- Set appropriate expiration times (consider 24 hours instead of 7 days)
- Implement token refresh mechanism
- Consider rotating secrets periodically

### CORS
- Never use `allow_origins=["*"]` in production
- Whitelist specific origins only
- Review CORS settings regularly

---

## Production Checklist

Before deploying to production:
- [ ] All secrets stored in environment variables
- [ ] `.env` not in version control
- [ ] API keys rotated from development keys
- [ ] Database using strong, unique password
- [ ] JWT secret is production-specific
- [ ] CORS restricted to production domains
- [ ] API rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SSL/TLS enabled for all connections
- [ ] Monitoring and alerting configured
- [ ] Backup strategy implemented

---

## Incident Response

If you suspect credentials have been compromised:

1. **Immediate Actions** (within 1 hour):
   - Rotate all potentially compromised credentials
   - Review access logs for suspicious activity
   - Notify team members

2. **Short-term** (within 24 hours):
   - Audit all API calls made with compromised keys
   - Check for data exfiltration
   - Review and update security policies
   - Force password resets for affected users

3. **Long-term** (within 1 week):
   - Conduct security audit
   - Implement additional monitoring
   - Update incident response procedures
   - Train team on security best practices

---

## Contact

For security concerns or to report vulnerabilities:
- Email: [your-security-email]
- Do not post security issues publicly on GitHub
