"""
Database-backed API Endpoints for Categorization-Bot
Add these endpoints to main.py to enable data persistence

INTEGRATION INSTRUCTIONS:
1. Add these imports to main.py:
   from database import get_db, init_db
   from auth import get_current_user, authenticate_user, create_access_token
   import crud
   import models
   from fastapi.security import OAuth2PasswordRequestForm

2. Add database initialization on startup:
   @app.on_event("startup")
   async def startup_event():
       init_db()

3. Copy all the endpoints below to main.py
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, timedelta
from database import get_db
from auth import get_current_user, authenticate_user, create_access_token, hash_password
import crud
import models


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class DocumentCreate(BaseModel):
    document_id: str
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    schema_type: str = "generic"


class DocumentResponse(BaseModel):
    id: int
    document_id: str
    file_name: str
    status: str
    progress: int
    uploaded_at: datetime
    processed_at: Optional[datetime]
    parsed_data: Optional[dict]

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    transaction_id: str
    document_id: str  # Frontend document ID
    vendor_name: Optional[str]
    amount: float
    transaction_date: Optional[date]
    description: Optional[str]
    transaction_type: Optional[str]


class TransactionResponse(BaseModel):
    id: int
    transaction_id: str
    vendor_name: Optional[str]
    amount: float
    transaction_date: Optional[date]
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionSearchRequest(BaseModel):
    search_query: Optional[str] = None
    vendor_name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    category: Optional[str] = None
    skip: int = 0
    limit: int = 100


class StatisticsResponse(BaseModel):
    total_documents: int
    total_transactions: int
    total_amount: float
    categorized_count: int
    approved_count: int
    approval_rate: float
    reconciled_count: int


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/register", response_model=UserResponse, tags=["Authentication"])
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user

    - **username**: Unique username
    - **email**: Unique email address
    - **password**: Password (will be hashed)
    """
    # Check if username exists
    existing_user = crud.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    existing_email = crud.get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    user = crud.create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password
    )

    # Log activity
    crud.log_activity(
        db=db,
        user_id=user.id,
        action="user_registered",
        entity_type="user",
        entity_id=user.id,
        details={"username": user.username, "email": user.email}
    )

    return user


@app.post("/login", response_model=Token, tags=["Authentication"])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with username and password

    Returns JWT access token for authentication
    """
    user = authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last login
    crud.update_user_login(db, user.id)

    # Create access token
    access_token = create_access_token(data={"sub": user.username})

    # Log activity
    crud.log_activity(
        db=db,
        user_id=user.id,
        action="user_login",
        entity_type="user",
        entity_id=user.id
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@app.get("/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user


@app.get("/statistics", response_model=StatisticsResponse, tags=["Analytics"])
async def get_statistics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user statistics and analytics"""
    stats = crud.get_user_statistics(db, current_user.id)
    return stats


# ============================================================================
# DOCUMENT ENDPOINTS
# ============================================================================

@app.post("/documents", response_model=DocumentResponse, tags=["Documents"])
async def create_document(
    document: DocumentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new document record

    Call this BEFORE processing to register the document in the database
    """
    doc = crud.create_document(
        db=db,
        user_id=current_user.id,
        document_id=document.document_id,
        file_name=document.file_name,
        file_type=document.file_type,
        file_size=document.file_size,
        schema_type=document.schema_type
    )

    # Log activity
    crud.log_activity(
        db=db,
        user_id=current_user.id,
        action="document_created",
        entity_type="document",
        entity_id=doc.id,
        details={"file_name": doc.file_name, "document_id": doc.document_id}
    )

    return doc


@app.get("/documents", response_model=List[DocumentResponse], tags=["Documents"])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all documents for current user

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by status (pending, processing, completed, error)
    """
    documents = crud.get_user_documents(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status
    )
    return documents


@app.get("/documents/{document_id}", response_model=DocumentResponse, tags=["Documents"])
async def get_document(
    document_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific document by ID"""
    document = crud.get_document_by_id(db, document_id, current_user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


@app.put("/documents/{document_id}/status", tags=["Documents"])
async def update_document_status(
    document_id: str,
    status: str,
    progress: Optional[int] = None,
    error_message: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update document processing status

    Call this during document processing to update progress
    """
    crud.update_document_status(
        db=db,
        document_id=document_id,
        user_id=current_user.id,
        status=status,
        progress=progress,
        error_message=error_message
    )

    # Log activity
    crud.log_activity(
        db=db,
        user_id=current_user.id,
        action="document_status_updated",
        entity_type="document",
        details={"document_id": document_id, "status": status, "progress": progress}
    )

    return {"success": True, "message": "Document status updated"}


@app.put("/documents/{document_id}/data", tags=["Documents"])
async def update_document_data(
    document_id: str,
    parsed_data: dict,
    extraction_verified: bool = False,
    verification_data: Optional[dict] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update document with parsed data

    Call this AFTER processing completes to save extracted data
    """
    crud.update_document_parsed_data(
        db=db,
        document_id=document_id,
        user_id=current_user.id,
        parsed_data=parsed_data,
        extraction_verified=extraction_verified,
        verification_data=verification_data
    )

    # Log activity
    crud.log_activity(
        db=db,
        user_id=current_user.id,
        action="document_data_saved",
        entity_type="document",
        details={"document_id": document_id, "extraction_verified": extraction_verified}
    )

    return {"success": True, "message": "Document data saved"}


@app.delete("/documents/{document_id}", tags=["Documents"])
async def delete_document(
    document_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document (and all associated transactions)"""
    crud.delete_document(db, document_id, current_user.id)

    # Log activity
    crud.log_activity(
        db=db,
        user_id=current_user.id,
        action="document_deleted",
        entity_type="document",
        details={"document_id": document_id}
    )

    return {"success": True, "message": "Document deleted"}


# ============================================================================
# TRANSACTION ENDPOINTS
# ============================================================================

@app.post("/transactions/search", response_model=List[TransactionResponse], tags=["Transactions"])
async def search_transactions(
    search_request: TransactionSearchRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search and filter transactions

    Supports:
    - Full-text search
    - Vendor name filtering
    - Date range filtering
    - Amount range filtering
    - Category filtering
    """
    if search_request.search_query:
        # Full-text search
        transactions = crud.search_transactions(
            db=db,
            user_id=current_user.id,
            search_query=search_request.search_query,
            skip=search_request.skip,
            limit=search_request.limit
        )
    else:
        # Filtered search
        transactions = crud.get_user_transactions(
            db=db,
            user_id=current_user.id,
            vendor_name=search_request.vendor_name,
            start_date=search_request.start_date,
            end_date=search_request.end_date,
            min_amount=search_request.min_amount,
            max_amount=search_request.max_amount,
            category=search_request.category,
            skip=search_request.skip,
            limit=search_request.limit
        )

    return transactions


@app.get("/transactions", response_model=List[TransactionResponse], tags=["Transactions"])
async def get_transactions(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all transactions for current user"""
    transactions = crud.get_user_transactions(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return transactions


@app.get("/transactions/{transaction_id}", response_model=TransactionResponse, tags=["Transactions"])
async def get_transaction(
    transaction_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific transaction by ID"""
    transaction = crud.get_transaction_by_id(db, transaction_id, current_user.id)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )

    return transaction


@app.get("/transactions/unreconciled", response_model=List[TransactionResponse], tags=["Transactions"])
async def get_unreconciled_transactions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all transactions that haven't been reconciled with bank statements"""
    transactions = crud.get_unreconciled_transactions(db, current_user.id)
    return transactions


# ============================================================================
# ACTIVITY LOG ENDPOINTS
# ============================================================================

@app.get("/activity", tags=["Analytics"])
async def get_activity_log(
    skip: int = 0,
    limit: int = 50,
    action: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user activity log

    Returns audit trail of all user actions
    """
    query = db.query(models.ActivityLog).filter(
        models.ActivityLog.user_id == current_user.id
    )

    if action:
        query = query.filter(models.ActivityLog.action == action)

    activities = query.order_by(
        models.ActivityLog.created_at.desc()
    ).offset(skip).limit(limit).all()

    return activities


# ============================================================================
# INTEGRATION NOTES
# ============================================================================

"""
TO INTEGRATE INTO MAIN.PY:

1. Add imports at the top of main.py:
   from database import get_db, init_db
   from auth import get_current_user, authenticate_user, create_access_token
   import crud
   import models

2. Add startup event:
   @app.on_event("startup")
   async def startup_event():
       try:
           init_db()
           print("✓ Database initialized successfully")
       except Exception as e:
           print(f"⚠ Database initialization warning: {e}")

3. Update existing /process-pdf endpoint to save to database:
   - After processing, call crud.create_document()
   - Create transaction records with crud.create_transaction()
   - Save categorization with crud.create_categorization()

4. Update existing endpoints to use database:
   - /research-vendor: Save results with crud.get_or_create_vendor_research()
   - /categorize-transaction: Save with crud.create_categorization()
   - /store-categorization: Already saves to Pinecone, also save to DB
   - /parse-bank-statement: Save with crud.create_bank_statement()
   - /reconcile: Save matches with crud.create_reconciliation_match()

5. Add OAuth2PasswordRequestForm dependency:
   from fastapi.security import OAuth2PasswordRequestForm

FRONTEND CHANGES NEEDED:

1. Add login/registration pages
2. Store JWT token in localStorage
3. Add Authorization header to all API requests:
   headers: { 'Authorization': `Bearer ${token}` }
4. Replace localStorage document storage with API calls
5. Add transaction history view
6. Add search functionality

DATABASE SETUP:

1. Install PostgreSQL
2. Create database: categorization_bot
3. Update .env with DATABASE_URL
4. Run: python init_database.py
5. Test: python -c "from database import test_connection; test_connection()"
"""
