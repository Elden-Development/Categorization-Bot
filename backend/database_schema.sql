-- ====================================================================
-- DATABASE SCHEMA FOR CATEGORIZATION-BOT
-- Data Persistence & Historical Tracking
-- ====================================================================

-- Users Table - Authentication and session management
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}'::jsonb  -- User preferences and settings
);

-- Documents Table - Uploaded documents and metadata
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    document_id VARCHAR(255) UNIQUE NOT NULL,  -- Frontend generated ID
    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(100),
    file_size INTEGER,  -- in bytes
    file_path TEXT,  -- Storage path or S3 URL
    schema_type VARCHAR(100) DEFAULT 'generic',

    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, error
    progress INTEGER DEFAULT 0,
    error_message TEXT,

    -- Timestamps
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,

    -- Extracted data (full JSON response from Gemini)
    parsed_data JSONB,

    -- Extraction verification results
    extraction_verified BOOLEAN DEFAULT FALSE,
    verification_data JSONB,

    -- Metadata
    page_count INTEGER,

    CONSTRAINT status_check CHECK (status IN ('pending', 'processing', 'completed', 'error'))
);

-- Transactions Table - Individual transactions extracted from documents
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    document_id INTEGER REFERENCES documents(id) ON DELETE CASCADE,

    -- Transaction identification
    transaction_id VARCHAR(255) UNIQUE NOT NULL,

    -- Vendor/Source information
    vendor_name VARCHAR(500),
    vendor_type VARCHAR(100),
    vendor_address TEXT,
    vendor_contact JSONB,
    vendor_tax_id VARCHAR(100),

    -- Financial data
    amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    tax_amount DECIMAL(15, 2),
    subtotal DECIMAL(15, 2),
    discount DECIMAL(15, 2),

    -- Transaction details
    transaction_date DATE,
    due_date DATE,
    payment_status VARCHAR(50),
    payment_method VARCHAR(100),
    transaction_type VARCHAR(100),  -- Invoice, Receipt, BankStatement, etc.

    -- Document references
    document_number VARCHAR(255),
    reference_numbers JSONB,  -- Array of reference numbers

    -- Line items (for detailed transactions)
    line_items JSONB,

    -- Description and notes
    description TEXT,
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vendor Research Table - Cached vendor research results
CREATE TABLE vendor_research (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    -- Vendor identification
    vendor_name VARCHAR(500) NOT NULL,
    normalized_name VARCHAR(500),  -- Normalized for matching

    -- Research results
    company_name VARCHAR(500),
    description TEXT,
    business_type VARCHAR(255),
    products_services TEXT,
    company_size VARCHAR(100),
    locations TEXT,

    -- Full research response
    research_data JSONB,

    -- Confidence and usage tracking
    confidence_score DECIMAL(5, 2),  -- 0-100
    usage_count INTEGER DEFAULT 1,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint to avoid duplicate research
    UNIQUE(user_id, normalized_name)
);

-- Categorizations Table - AI/ML categorization results
CREATE TABLE categorizations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    vendor_research_id INTEGER REFERENCES vendor_research(id) ON DELETE SET NULL,

    -- Categorization results
    category VARCHAR(255) NOT NULL,
    subcategory VARCHAR(255),
    ledger_type VARCHAR(100),

    -- Method used for categorization
    method VARCHAR(50) NOT NULL,  -- 'ml', 'gemini', 'manual', 'hybrid'

    -- Confidence scores
    confidence_score DECIMAL(5, 2),  -- 0-100
    ml_confidence DECIMAL(5, 2),
    gemini_confidence DECIMAL(5, 2),

    -- Explanation and reasoning
    explanation TEXT,

    -- Full categorization response
    categorization_data JSONB,

    -- User validation
    user_approved BOOLEAN DEFAULT FALSE,
    user_modified BOOLEAN DEFAULT FALSE,

    -- Transaction context
    transaction_purpose TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT method_check CHECK (method IN ('ml', 'gemini', 'manual', 'hybrid'))
);

-- User Corrections Table - Track user feedback and corrections
CREATE TABLE user_corrections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    categorization_id INTEGER REFERENCES categorizations(id) ON DELETE SET NULL,

    -- Original categorization
    original_category VARCHAR(255),
    original_subcategory VARCHAR(255),
    original_ledger_type VARCHAR(100),
    original_method VARCHAR(50),

    -- Corrected categorization
    corrected_category VARCHAR(255) NOT NULL,
    corrected_subcategory VARCHAR(255),
    corrected_ledger_type VARCHAR(100),

    -- Correction details
    correction_reason TEXT,
    user_feedback TEXT,

    -- Learning weight (higher = more important for ML)
    learning_weight DECIMAL(5, 2) DEFAULT 1.0,

    -- Full correction data
    correction_data JSONB,

    -- Applied to model
    applied_to_training BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT original_method_check CHECK (original_method IN ('ml', 'gemini', 'manual', 'hybrid'))
);

-- Bank Statements Table - Uploaded bank statements
CREATE TABLE bank_statements (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    -- File information
    file_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(100),
    file_path TEXT,

    -- Statement period
    statement_date DATE,
    period_start DATE,
    period_end DATE,

    -- Account information
    bank_name VARCHAR(255),
    account_number VARCHAR(100),
    account_type VARCHAR(100),

    -- Balance information
    opening_balance DECIMAL(15, 2),
    closing_balance DECIMAL(15, 2),

    -- Transaction count
    transaction_count INTEGER,

    -- Parsed transactions (raw data)
    transactions_data JSONB,

    -- Timestamps
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP
);

-- Bank Transactions Table - Individual bank transactions
CREATE TABLE bank_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    bank_statement_id INTEGER REFERENCES bank_statements(id) ON DELETE CASCADE,

    -- Transaction details
    transaction_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    transaction_type VARCHAR(50),  -- debit, credit

    -- Optional fields
    category VARCHAR(255),
    reference VARCHAR(255),
    balance DECIMAL(15, 2),

    -- Reconciliation status
    is_reconciled BOOLEAN DEFAULT FALSE,
    reconciled_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reconciliation Matches Table - Document-to-bank transaction matches
CREATE TABLE reconciliation_matches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
    bank_transaction_id INTEGER REFERENCES bank_transactions(id) ON DELETE CASCADE,

    -- Match details
    match_type VARCHAR(50) NOT NULL,  -- 'auto', 'manual', 'suggested'
    match_confidence DECIMAL(5, 2),  -- 0-100

    -- Matching criteria scores
    name_match_score DECIMAL(5, 2),
    amount_match_score DECIMAL(5, 2),
    date_match_score DECIMAL(5, 2),

    -- Match explanation
    match_reason TEXT,

    -- User confirmation
    user_confirmed BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMP,

    -- Full match data
    match_data JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint: one transaction can only match one bank transaction
    UNIQUE(transaction_id, bank_transaction_id),

    CONSTRAINT match_type_check CHECK (match_type IN ('auto', 'manual', 'suggested'))
);

-- Activity Log Table - Audit trail for all actions
CREATE TABLE activity_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    -- Activity details
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100),  -- 'document', 'transaction', 'categorization', etc.
    entity_id INTEGER,

    -- Details and changes
    details JSONB,
    changes JSONB,  -- Before/after for updates

    -- IP and session info
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(255),

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Saved Searches Table - User's saved search queries
CREATE TABLE saved_searches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    -- Search details
    search_name VARCHAR(255) NOT NULL,
    search_query JSONB NOT NULL,  -- Stored search parameters

    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ====================================================================
-- INDEXES FOR PERFORMANCE
-- ====================================================================

-- Users indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Documents indexes
CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_uploaded_at ON documents(uploaded_at DESC);
CREATE INDEX idx_documents_document_id ON documents(document_id);

-- Transactions indexes
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_document_id ON transactions(document_id);
CREATE INDEX idx_transactions_vendor_name ON transactions(vendor_name);
CREATE INDEX idx_transactions_transaction_date ON transactions(transaction_date DESC);
CREATE INDEX idx_transactions_amount ON transactions(amount);
CREATE INDEX idx_transactions_created_at ON transactions(created_at DESC);

-- Vendor research indexes
CREATE INDEX idx_vendor_research_user_id ON vendor_research(user_id);
CREATE INDEX idx_vendor_research_vendor_name ON vendor_research(vendor_name);
CREATE INDEX idx_vendor_research_normalized_name ON vendor_research(normalized_name);

-- Categorizations indexes
CREATE INDEX idx_categorizations_user_id ON categorizations(user_id);
CREATE INDEX idx_categorizations_transaction_id ON categorizations(transaction_id);
CREATE INDEX idx_categorizations_category ON categorizations(category);
CREATE INDEX idx_categorizations_method ON categorizations(method);

-- User corrections indexes
CREATE INDEX idx_user_corrections_user_id ON user_corrections(user_id);
CREATE INDEX idx_user_corrections_transaction_id ON user_corrections(transaction_id);
CREATE INDEX idx_user_corrections_applied ON user_corrections(applied_to_training);

-- Bank statements indexes
CREATE INDEX idx_bank_statements_user_id ON bank_statements(user_id);
CREATE INDEX idx_bank_statements_statement_date ON bank_statements(statement_date DESC);

-- Bank transactions indexes
CREATE INDEX idx_bank_transactions_user_id ON bank_transactions(user_id);
CREATE INDEX idx_bank_transactions_bank_statement_id ON bank_transactions(bank_statement_id);
CREATE INDEX idx_bank_transactions_transaction_date ON bank_transactions(transaction_date DESC);
CREATE INDEX idx_bank_transactions_reconciled ON bank_transactions(is_reconciled);

-- Reconciliation matches indexes
CREATE INDEX idx_reconciliation_matches_user_id ON reconciliation_matches(user_id);
CREATE INDEX idx_reconciliation_matches_transaction_id ON reconciliation_matches(transaction_id);
CREATE INDEX idx_reconciliation_matches_bank_transaction_id ON reconciliation_matches(bank_transaction_id);
CREATE INDEX idx_reconciliation_matches_confirmed ON reconciliation_matches(user_confirmed);

-- Activity log indexes
CREATE INDEX idx_activity_log_user_id ON activity_log(user_id);
CREATE INDEX idx_activity_log_created_at ON activity_log(created_at DESC);
CREATE INDEX idx_activity_log_action ON activity_log(action);

-- ====================================================================
-- FULL TEXT SEARCH INDEXES (PostgreSQL)
-- ====================================================================

-- Add full-text search for vendor names
CREATE INDEX idx_transactions_vendor_name_fts ON transactions
    USING gin(to_tsvector('english', vendor_name));

-- Add full-text search for descriptions
CREATE INDEX idx_transactions_description_fts ON transactions
    USING gin(to_tsvector('english', description));

-- Add full-text search for bank transaction descriptions
CREATE INDEX idx_bank_transactions_description_fts ON bank_transactions
    USING gin(to_tsvector('english', description));

-- ====================================================================
-- FUNCTIONS AND TRIGGERS
-- ====================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vendor_research_updated_at BEFORE UPDATE ON vendor_research
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categorizations_updated_at BEFORE UPDATE ON categorizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reconciliation_matches_updated_at BEFORE UPDATE ON reconciliation_matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_saved_searches_updated_at BEFORE UPDATE ON saved_searches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ====================================================================
-- VIEWS FOR COMMON QUERIES
-- ====================================================================

-- Complete transaction view with categorization and reconciliation
CREATE VIEW v_complete_transactions AS
SELECT
    t.*,
    c.category,
    c.subcategory,
    c.ledger_type,
    c.confidence_score,
    c.method AS categorization_method,
    c.user_approved AS categorization_approved,
    vr.company_name AS vendor_company_name,
    vr.description AS vendor_description,
    rm.id AS reconciliation_match_id,
    rm.match_confidence,
    rm.user_confirmed AS reconciliation_confirmed,
    bt.id AS bank_transaction_id,
    bt.description AS bank_description
FROM transactions t
LEFT JOIN categorizations c ON t.id = c.transaction_id
LEFT JOIN vendor_research vr ON c.vendor_research_id = vr.id
LEFT JOIN reconciliation_matches rm ON t.id = rm.transaction_id
LEFT JOIN bank_transactions bt ON rm.bank_transaction_id = bt.id;

-- User transaction statistics view
CREATE VIEW v_user_transaction_stats AS
SELECT
    user_id,
    COUNT(*) AS total_transactions,
    COUNT(CASE WHEN transaction_date >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) AS last_30_days,
    SUM(amount) AS total_amount,
    AVG(amount) AS average_amount,
    MIN(transaction_date) AS first_transaction,
    MAX(transaction_date) AS last_transaction
FROM transactions
GROUP BY user_id;

-- Categorization accuracy view
CREATE VIEW v_categorization_accuracy AS
SELECT
    user_id,
    method,
    COUNT(*) AS total_categorizations,
    COUNT(CASE WHEN user_approved = TRUE THEN 1 END) AS approved_count,
    COUNT(CASE WHEN user_modified = TRUE THEN 1 END) AS modified_count,
    AVG(confidence_score) AS avg_confidence,
    ROUND(COUNT(CASE WHEN user_approved = TRUE THEN 1 END)::DECIMAL / COUNT(*)::DECIMAL * 100, 2) AS approval_rate
FROM categorizations
GROUP BY user_id, method;

-- ====================================================================
-- SAMPLE DATA (Optional - for testing)
-- ====================================================================

-- Insert a test user
-- INSERT INTO users (username, email, password_hash)
-- VALUES ('testuser', 'test@example.com', 'hashed_password_here');

COMMENT ON TABLE users IS 'User accounts for authentication and session management';
COMMENT ON TABLE documents IS 'Uploaded documents with extraction status and results';
COMMENT ON TABLE transactions IS 'Individual financial transactions extracted from documents';
COMMENT ON TABLE vendor_research IS 'Cached vendor research results to avoid redundant API calls';
COMMENT ON TABLE categorizations IS 'AI/ML categorization results with confidence scores';
COMMENT ON TABLE user_corrections IS 'User feedback and corrections for ML improvement';
COMMENT ON TABLE bank_statements IS 'Uploaded bank statements for reconciliation';
COMMENT ON TABLE bank_transactions IS 'Individual transactions from bank statements';
COMMENT ON TABLE reconciliation_matches IS 'Matches between document transactions and bank transactions';
COMMENT ON TABLE activity_log IS 'Audit trail of all user actions';
COMMENT ON TABLE saved_searches IS 'User-saved search queries for quick access';
