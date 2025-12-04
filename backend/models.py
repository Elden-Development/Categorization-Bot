"""
SQLAlchemy ORM Models for Categorization-Bot
Implements the database schema for data persistence
"""

from sqlalchemy import (
    Boolean, Column, Integer, String, Text, DECIMAL, Date, DateTime,
    ForeignKey, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime


class User(Base):
    """User accounts for authentication and session management"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)  # 'user' or 'admin'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    settings = Column(JSONB, default={})

    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    vendor_research = relationship("VendorResearch", back_populates="user", cascade="all, delete-orphan")
    categorizations = relationship("Categorization", back_populates="user", cascade="all, delete-orphan")
    user_corrections = relationship("UserCorrection", back_populates="user", cascade="all, delete-orphan")
    bank_statements = relationship("BankStatement", back_populates="user", cascade="all, delete-orphan")
    bank_transactions = relationship("BankTransaction", back_populates="user", cascade="all, delete-orphan")
    reconciliation_matches = relationship("ReconciliationMatch", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="user")
    saved_searches = relationship("SavedSearch", back_populates="user", cascade="all, delete-orphan")


class Document(Base):
    """Uploaded documents with extraction status and results"""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(255), unique=True, nullable=False, index=True)
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(100))
    file_size = Column(Integer)
    file_path = Column(Text)
    schema_type = Column(String(100), default="generic")

    # Status tracking
    status = Column(String(50), default="pending", index=True)
    progress = Column(Integer, default=0)
    error_message = Column(Text)

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    processed_at = Column(DateTime(timezone=True))

    # Extracted data
    parsed_data = Column(JSONB)

    # Extraction verification
    extraction_verified = Column(Boolean, default=False)
    verification_data = Column(JSONB)

    # Metadata
    page_count = Column(Integer)

    # Relationships
    user = relationship("User", back_populates="documents")
    transactions = relationship("Transaction", back_populates="document", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'error')",
            name="documents_status_check"
        ),
    )


class Transaction(Base):
    """Individual financial transactions extracted from documents"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transaction identification
    transaction_id = Column(String(255), unique=True, nullable=False)

    # Vendor/Source information
    vendor_name = Column(String(500), index=True)
    vendor_type = Column(String(100))
    vendor_address = Column(Text)
    vendor_contact = Column(JSONB)
    vendor_tax_id = Column(String(100))

    # Financial data
    amount = Column(DECIMAL(15, 2), nullable=False, index=True)
    currency = Column(String(10), default="USD")
    tax_amount = Column(DECIMAL(15, 2))
    subtotal = Column(DECIMAL(15, 2))
    discount = Column(DECIMAL(15, 2))

    # Transaction details
    transaction_date = Column(Date, index=True)
    due_date = Column(Date)
    payment_status = Column(String(50))
    payment_method = Column(String(100))
    transaction_type = Column(String(100))

    # Document references
    document_number = Column(String(255))
    reference_numbers = Column(JSONB)

    # Line items
    line_items = Column(JSONB)

    # Description and notes
    description = Column(Text)
    notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="transactions")
    document = relationship("Document", back_populates="transactions")
    categorizations = relationship("Categorization", back_populates="transaction", cascade="all, delete-orphan")
    user_corrections = relationship("UserCorrection", back_populates="transaction", cascade="all, delete-orphan")
    reconciliation_matches = relationship("ReconciliationMatch", back_populates="transaction", cascade="all, delete-orphan")

    # Indexes for full-text search
    __table_args__ = (
        Index('idx_transactions_vendor_name_fts', 'vendor_name', postgresql_using='gin',
              postgresql_ops={'vendor_name': 'gin_trgm_ops'}),
        Index('idx_transactions_description_fts', 'description', postgresql_using='gin',
              postgresql_ops={'description': 'gin_trgm_ops'}),
    )


class VendorResearch(Base):
    """Cached vendor research results"""
    __tablename__ = "vendor_research"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Vendor identification
    vendor_name = Column(String(500), nullable=False, index=True)
    normalized_name = Column(String(500), index=True)

    # Research results
    company_name = Column(String(500))
    description = Column(Text)
    business_type = Column(String(255))
    products_services = Column(Text)
    company_size = Column(String(100))
    locations = Column(Text)

    # Full research response
    research_data = Column(JSONB)

    # Confidence and usage tracking
    confidence_score = Column(DECIMAL(5, 2))
    usage_count = Column(Integer, default=1)
    last_used = Column(DateTime(timezone=True), server_default=func.now())

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="vendor_research")
    categorizations = relationship("Categorization", back_populates="vendor_research")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'normalized_name', name='uq_user_vendor'),
    )


class Categorization(Base):
    """AI/ML categorization results with confidence scores"""
    __tablename__ = "categorizations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=True, index=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id", ondelete="CASCADE"), nullable=True, index=True)
    vendor_research_id = Column(Integer, ForeignKey("vendor_research.id", ondelete="SET NULL"))

    # Categorization results
    category = Column(String(255), nullable=False, index=True)
    subcategory = Column(String(255))
    ledger_type = Column(String(100))

    # Method used
    method = Column(String(50), nullable=False, index=True)

    # Confidence scores
    confidence_score = Column(DECIMAL(5, 2))
    ml_confidence = Column(DECIMAL(5, 2))
    gemini_confidence = Column(DECIMAL(5, 2))

    # Explanation
    explanation = Column(Text)

    # Full categorization response
    categorization_data = Column(JSONB)

    # User validation
    user_approved = Column(Boolean, default=False)
    user_modified = Column(Boolean, default=False)

    # Transaction context
    transaction_purpose = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="categorizations")
    transaction = relationship("Transaction", back_populates="categorizations")
    bank_transaction = relationship("BankTransaction", back_populates="categorizations")
    vendor_research = relationship("VendorResearch", back_populates="categorizations")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "method IN ('ml', 'gemini', 'manual', 'hybrid', 'vendor_mapping')",
            name="categorizations_method_check"
        ),
    )


class UserCorrection(Base):
    """User feedback and corrections for ML improvement"""
    __tablename__ = "user_corrections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    categorization_id = Column(Integer, ForeignKey("categorizations.id", ondelete="SET NULL"))

    # Original categorization
    original_category = Column(String(255))
    original_subcategory = Column(String(255))
    original_ledger_type = Column(String(100))
    original_method = Column(String(50))

    # Corrected categorization
    corrected_category = Column(String(255), nullable=False)
    corrected_subcategory = Column(String(255))
    corrected_ledger_type = Column(String(100))

    # Correction details
    correction_reason = Column(Text)
    user_feedback = Column(Text)

    # Learning weight
    learning_weight = Column(DECIMAL(5, 2), default=1.0)

    # Full correction data
    correction_data = Column(JSONB)

    # Applied to model
    applied_to_training = Column(Boolean, default=False, index=True)
    applied_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="user_corrections")
    transaction = relationship("Transaction", back_populates="user_corrections")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "original_method IN ('ml', 'gemini', 'manual', 'hybrid')",
            name="user_corrections_original_method_check"
        ),
    )


class BankStatement(Base):
    """Uploaded bank statements for reconciliation"""
    __tablename__ = "bank_statements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # File information
    file_name = Column(String(500), nullable=False)
    file_type = Column(String(100))
    file_path = Column(Text)

    # Statement period
    statement_date = Column(Date, index=True)
    period_start = Column(Date)
    period_end = Column(Date)

    # Account information
    bank_name = Column(String(255))
    account_number = Column(String(100))
    account_type = Column(String(100))

    # Balance information
    opening_balance = Column(DECIMAL(15, 2))
    closing_balance = Column(DECIMAL(15, 2))

    # Transaction count
    transaction_count = Column(Integer)

    # Parsed transactions
    transactions_data = Column(JSONB)

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="bank_statements")
    bank_transactions = relationship("BankTransaction", back_populates="bank_statement", cascade="all, delete-orphan")


class BankTransaction(Base):
    """Individual transactions from bank statements"""
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_statement_id = Column(Integer, ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=False, index=True)

    # Transaction details
    transaction_date = Column(Date, nullable=False, index=True)
    description = Column(Text, nullable=False)
    amount = Column(DECIMAL(15, 2), nullable=False)
    transaction_type = Column(String(50))

    # Optional fields
    category = Column(String(255))
    reference = Column(String(255))
    balance = Column(DECIMAL(15, 2))

    # Reconciliation status
    is_reconciled = Column(Boolean, default=False, index=True)
    reconciled_at = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="bank_transactions")
    bank_statement = relationship("BankStatement", back_populates="bank_transactions")
    reconciliation_matches = relationship("ReconciliationMatch", back_populates="bank_transaction", cascade="all, delete-orphan")
    categorizations = relationship("Categorization", back_populates="bank_transaction", cascade="all, delete-orphan")

    # Indexes for full-text search
    __table_args__ = (
        Index('idx_bank_transactions_description_fts', 'description', postgresql_using='gin',
              postgresql_ops={'description': 'gin_trgm_ops'}),
    )


class ReconciliationMatch(Base):
    """Matches between document transactions and bank transactions"""
    __tablename__ = "reconciliation_matches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_transaction_id = Column(Integer, ForeignKey("bank_transactions.id", ondelete="CASCADE"), nullable=False, index=True)

    # Match details
    match_type = Column(String(50), nullable=False)
    match_confidence = Column(DECIMAL(5, 2))

    # Matching criteria scores
    name_match_score = Column(DECIMAL(5, 2))
    amount_match_score = Column(DECIMAL(5, 2))
    date_match_score = Column(DECIMAL(5, 2))

    # Match explanation
    match_reason = Column(Text)

    # User confirmation
    user_confirmed = Column(Boolean, default=False, index=True)
    confirmed_at = Column(DateTime(timezone=True))

    # Full match data
    match_data = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="reconciliation_matches")
    transaction = relationship("Transaction", back_populates="reconciliation_matches")
    bank_transaction = relationship("BankTransaction", back_populates="reconciliation_matches")

    # Constraints
    __table_args__ = (
        UniqueConstraint('transaction_id', 'bank_transaction_id', name='uq_transaction_bank_transaction'),
        CheckConstraint(
            "match_type IN ('auto', 'manual', 'suggested')",
            name="reconciliation_matches_match_type_check"
        ),
    )


class ActivityLog(Base):
    """Audit trail for all user actions"""
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True)

    # Activity details
    action = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(100))
    entity_id = Column(Integer)

    # Details and changes
    details = Column(JSONB)
    changes = Column(JSONB)

    # IP and session info
    ip_address = Column(String(45))
    user_agent = Column(Text)
    session_id = Column(String(255))

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="activity_logs")


class SavedSearch(Base):
    """User's saved search queries"""
    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Search details
    search_name = Column(String(255), nullable=False)
    search_query = Column(JSONB, nullable=False)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True))

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="saved_searches")
