"""
Pydantic schemas for Categorization-Bot API
Request/Response models for all endpoints
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class DocumentSchema(str, Enum):
    """Valid document schema types"""
    GENERIC = "generic"
    FORM_1040 = "1040"
    FORM_2848 = "2848"
    FORM_8821 = "8821"
    FORM_941 = "941"
    PAYROLL = "payroll"


class ExportFilter(str, Enum):
    """Export filter options"""
    ALL = "all"
    CATEGORIZED = "categorized"
    UNCATEGORIZED = "uncategorized"
    APPROVED = "approved"
    PENDING = "pending"


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class UserCreate(BaseModel):
    """Request model for user registration"""
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response model for user data"""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Response model for authentication token"""
    access_token: str
    token_type: str
    user: UserResponse


class UserSettings(BaseModel):
    """User preferences and settings"""
    confidence_threshold: float = Field(
        default=70.0,
        ge=0,
        le=100,
        description="Minimum confidence score (0-100) to auto-approve categorizations"
    )
    auto_approve_vendor_mapping: bool = Field(
        default=True,
        description="Automatically approve categorizations from known vendor mapping"
    )
    default_export_format: str = Field(
        default="csv",
        description="Default export format (csv or excel)"
    )

    class Config:
        extra = "allow"  # Allow additional settings to be stored


class UserSettingsResponse(BaseModel):
    """Response model for user settings"""
    settings: UserSettings
    updated_at: Optional[datetime] = None


# ============================================================================
# VENDOR RESEARCH SCHEMAS
# ============================================================================

class VendorResearchRequest(BaseModel):
    """Request model for vendor research"""
    vendor_name: str = Field(..., min_length=1, max_length=500, description="Vendor name to research")

    @field_validator('vendor_name')
    @classmethod
    def validate_vendor_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Vendor name cannot be empty or whitespace")
        return v.strip()


class EnhancedResearchRequest(BaseModel):
    """Request model for enhanced vendor research"""
    vendor_name: str = Field(..., min_length=1, max_length=500, description="Vendor name to research")
    transaction_context: dict = Field(..., description="Additional context about the transaction")
    confidence_threshold: int = Field(70, ge=0, le=100, description="Minimum confidence to skip research (0-100)")


# ============================================================================
# CATEGORIZATION SCHEMAS
# ============================================================================

class FinancialCategorizationRequest(BaseModel):
    """Request model for basic financial categorization"""
    vendor_info: str = Field(..., min_length=1, max_length=2000, description="Vendor information")
    document_data: dict = Field(..., description="Parsed document data")
    transaction_purpose: Optional[str] = Field(None, max_length=1000, description="Purpose of transaction")

    @field_validator('vendor_info')
    @classmethod
    def validate_vendor_info(cls, v):
        if not v or not v.strip():
            raise ValueError("Vendor info cannot be empty or whitespace")
        return v.strip()


class SmartCategorizationRequest(BaseModel):
    """Request model for smart categorization with auto-research"""
    vendor_name: str = Field(..., min_length=1, max_length=500, description="Vendor name")
    document_data: dict = Field(..., description="Parsed document data")
    transaction_purpose: Optional[str] = Field(None, max_length=1000, description="Transaction purpose")
    confidence_threshold: int = Field(70, ge=0, le=100, description="Threshold for triggering research")
    auto_research: bool = Field(True, description="Whether to auto-research low confidence vendors")

    @field_validator('vendor_name')
    @classmethod
    def validate_vendor_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Vendor name cannot be empty or whitespace")
        return v.strip()


class HybridCategorizationRequest(BaseModel):
    """Request model for hybrid ML + Gemini categorization"""
    vendor_info: str = Field(..., min_length=1, max_length=2000, description="Vendor information")
    document_data: dict = Field(..., description="Parsed document data")
    transaction_purpose: Optional[str] = Field(None, max_length=1000, description="Transaction purpose")

    @field_validator('vendor_info')
    @classmethod
    def validate_vendor_info(cls, v):
        if not v or not v.strip():
            raise ValueError("Vendor info cannot be empty or whitespace")
        return v.strip()


class StoreCategorizationRequest(BaseModel):
    """Request model for storing a categorization result"""
    document_id: str = Field(..., min_length=1, max_length=100, description="Document ID")
    category: str = Field(..., min_length=1, max_length=200, description="Category")
    subcategory: str = Field(..., min_length=1, max_length=200, description="Subcategory")
    ledger_type: str = Field(..., min_length=1, max_length=100, description="Ledger type")
    confidence: float = Field(..., ge=0, le=100, description="Confidence score")
    method: str = Field(..., min_length=1, max_length=50, description="Categorization method used")
    explanation: Optional[str] = Field(None, max_length=2000, description="Explanation for the categorization")


class SubmitCorrectionRequest(BaseModel):
    """Request model for submitting a user correction"""
    document_id: str = Field(..., min_length=1, max_length=100, description="Document ID")
    original_category: str = Field(..., min_length=1, max_length=200, description="Original category")
    original_subcategory: str = Field(..., min_length=1, max_length=200, description="Original subcategory")
    corrected_category: str = Field(..., min_length=1, max_length=200, description="Corrected category")
    corrected_subcategory: str = Field(..., min_length=1, max_length=200, description="Corrected subcategory")
    corrected_ledger_type: Optional[str] = Field(None, max_length=100, description="Corrected ledger type")
    correction_reason: Optional[str] = Field(None, max_length=1000, description="Reason for correction")
    feedback: Optional[str] = Field(None, max_length=2000, description="Additional feedback")


# ============================================================================
# RECONCILIATION SCHEMAS
# ============================================================================

class ReconciliationRequest(BaseModel):
    """Request model for document-bank reconciliation"""
    documents: List[dict] = Field(..., description="List of processed documents")
    bank_transactions: List[dict] = Field(..., description="List of bank transactions")


class ManualMatchRequest(BaseModel):
    """Request model for manual reconciliation match"""
    document: dict = Field(..., description="Document to match")
    transaction: dict = Field(..., description="Bank transaction to match with")


# ============================================================================
# DOCUMENT SCHEMAS
# ============================================================================

class DocumentResponse(BaseModel):
    """Response model for document data"""
    id: int
    document_id: str
    file_name: str
    file_type: Optional[str]
    file_size: Optional[int]
    schema_type: Optional[str]
    status: str
    progress: int
    parsed_data: Optional[dict]
    uploaded_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """Response model for transaction data"""
    id: int
    transaction_id: Optional[str]
    document_id: int
    vendor_name: Optional[str]
    vendor_type: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    transaction_date: Optional[datetime]
    transaction_type: Optional[str]
    document_number: Optional[str]
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionSearchRequest(BaseModel):
    """Request model for transaction search"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results to return")
    skip: int = Field(0, ge=0, description="Number of results to skip")


# ============================================================================
# REVIEW QUEUE SCHEMAS
# ============================================================================

class LowConfidenceTransaction(BaseModel):
    """Model for low-confidence transactions in review queue"""
    id: int
    transaction_id: Optional[str]
    vendor_name: Optional[str]
    amount: Optional[float]
    category: Optional[str]
    subcategory: Optional[str]
    ledger_type: Optional[str]
    confidence_score: Optional[float]
    method: Optional[str]
    explanation: Optional[str]
    needs_review: bool = True


class ApproveCategorizationRequest(BaseModel):
    """Request model for approving a single categorization"""
    transaction_id: int = Field(..., description="Transaction ID to approve")
    approved: bool = Field(True, description="Whether to approve")
    corrected_category: Optional[str] = Field(None, max_length=200)
    corrected_subcategory: Optional[str] = Field(None, max_length=200)
    corrected_ledger_type: Optional[str] = Field(None, max_length=100)
    review_notes: Optional[str] = Field(None, max_length=1000)


class ApproveBankTransactionRequest(BaseModel):
    """Request model for approving a bank transaction categorization"""
    bank_transaction_id: int = Field(..., description="Bank transaction ID")
    approved: bool = Field(True, description="Whether to approve")
    corrected_category: Optional[str] = Field(None, max_length=200)
    corrected_subcategory: Optional[str] = Field(None, max_length=200)
    corrected_ledger_type: Optional[str] = Field(None, max_length=100)


class BulkApproveBankTransactionsRequest(BaseModel):
    """Request model for bulk approving bank transaction categorizations"""
    bank_transaction_ids: Optional[List[int]] = Field(None, description="List of bank transaction IDs to approve")
    bank_statement_id: Optional[int] = Field(None, description="Approve all transactions in this statement")
    min_confidence: Optional[float] = Field(None, ge=0, le=100, description="Only approve above this confidence")
    approve_all_high_confidence: bool = Field(False, description="Approve all above user's threshold")


class BulkApproveRequest(BaseModel):
    """Request model for bulk approval of review queue items"""
    item_ids: Optional[List[int]] = Field(None, description="Specific item IDs to approve")
    min_confidence: Optional[float] = Field(None, ge=0, le=100, description="Approve all above this confidence")
    max_confidence: Optional[float] = Field(None, ge=0, le=100, description="Approve all below this confidence")
    category_filter: Optional[str] = Field(None, max_length=200, description="Only approve this category")


class BulkApproveResponse(BaseModel):
    """Response model for bulk approval"""
    success: bool
    approved_count: int
    skipped_count: int
    errors: List[str] = []
    approved_ids: List[int] = []


# ============================================================================
# BATCH PROCESSING SCHEMAS
# ============================================================================

class BatchCategorizationRequest(BaseModel):
    """Request model for batch categorization of bank statement"""
    bank_statement_id: int = Field(..., description="Bank statement ID to categorize")
    confidence_threshold: Optional[float] = Field(None, ge=0, le=100, description="Override user's threshold")
    use_vendor_mapping: Optional[bool] = Field(None, description="Whether to use vendor mapping")


class BatchCategorizationResponse(BaseModel):
    """Response model for batch categorization"""
    success: bool
    statement_id: int
    total_transactions: int
    processed: int
    failed: int
    high_confidence: int
    low_confidence: int
    results: List[dict] = []
    summary: dict = {}


class AsyncBatchRequest(BaseModel):
    """Request model for async batch categorization"""
    bank_statement_id: int = Field(..., description="Bank statement ID")
    confidence_threshold: Optional[float] = Field(None, ge=0, le=100)
    use_vendor_mapping: Optional[bool] = Field(None)


class AsyncBatchResponse(BaseModel):
    """Response model for async batch job creation"""
    success: bool
    job_id: str
    message: str
    total_transactions: int


class JobStatusResponse(BaseModel):
    """Response model for batch job status"""
    job_id: str
    status: str
    progress: int
    total: int
    processed: int
    high_confidence: int
    low_confidence: int
    failed: int
    current_item: Optional[str]
    error: Optional[str]
    results: List[dict] = []
    category_counts: dict = {}
