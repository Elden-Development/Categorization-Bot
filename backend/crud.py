"""
CRUD (Create, Read, Update, Delete) operations for Categorization-Bot
Database access layer for all models
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import models
from auth import hash_password


# ============================================================================
# USER OPERATIONS
# ============================================================================

def create_user(db: Session, username: str, email: str, password: str) -> models.User:
    """Create a new user"""
    password_hash = hash_password(password)
    user = models.User(
        username=username,
        email=email,
        password_hash=password_hash
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get user by username"""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()


def update_user_login(db: Session, user_id: int):
    """Update user's last login time"""
    db.query(models.User).filter(models.User.id == user_id).update({
        "last_login": datetime.utcnow()
    })
    db.commit()


# ============================================================================
# DOCUMENT OPERATIONS
# ============================================================================

def create_document(
    db: Session,
    user_id: int,
    document_id: str,
    file_name: str,
    file_type: str = None,
    file_size: int = None,
    schema_type: str = "generic"
) -> models.Document:
    """Create a new document record"""
    document = models.Document(
        user_id=user_id,
        document_id=document_id,
        file_name=file_name,
        file_type=file_type,
        file_size=file_size,
        schema_type=schema_type,
        status="pending",
        progress=0
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document_by_id(db: Session, document_id: str, user_id: int) -> Optional[models.Document]:
    """Get document by document_id"""
    return db.query(models.Document).filter(
        and_(
            models.Document.document_id == document_id,
            models.Document.user_id == user_id
        )
    ).first()


def get_user_documents(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None
) -> List[models.Document]:
    """Get all documents for a user with optional filtering"""
    query = db.query(models.Document).filter(models.Document.user_id == user_id)

    if status:
        query = query.filter(models.Document.status == status)

    return query.order_by(desc(models.Document.uploaded_at)).offset(skip).limit(limit).all()


def update_document_status(
    db: Session,
    document_id: str,
    user_id: int,
    status: str,
    progress: int = None,
    error_message: str = None
):
    """Update document processing status"""
    update_data = {"status": status}

    if progress is not None:
        update_data["progress"] = progress

    if error_message:
        update_data["error_message"] = error_message

    if status == "completed":
        update_data["processed_at"] = datetime.utcnow()

    db.query(models.Document).filter(
        and_(
            models.Document.document_id == document_id,
            models.Document.user_id == user_id
        )
    ).update(update_data)
    db.commit()


def update_document_parsed_data(
    db: Session,
    document_id: str,
    user_id: int,
    parsed_data: Dict,
    extraction_verified: bool = False,
    verification_data: Dict = None
):
    """Update document with parsed data"""
    update_data = {
        "parsed_data": parsed_data,
        "extraction_verified": extraction_verified
    }

    if verification_data:
        update_data["verification_data"] = verification_data

    db.query(models.Document).filter(
        and_(
            models.Document.document_id == document_id,
            models.Document.user_id == user_id
        )
    ).update(update_data)
    db.commit()


def delete_document(db: Session, document_id: str, user_id: int):
    """Delete a document"""
    db.query(models.Document).filter(
        and_(
            models.Document.document_id == document_id,
            models.Document.user_id == user_id
        )
    ).delete()
    db.commit()


# ============================================================================
# TRANSACTION OPERATIONS
# ============================================================================

def create_transaction(
    db: Session,
    user_id: int,
    document_db_id: int,
    transaction_data: Dict
) -> models.Transaction:
    """Create a new transaction from extracted document data"""
    transaction = models.Transaction(
        user_id=user_id,
        document_id=document_db_id,
        transaction_id=transaction_data.get("transaction_id"),
        vendor_name=transaction_data.get("vendor_name"),
        vendor_type=transaction_data.get("vendor_type"),
        vendor_address=transaction_data.get("vendor_address"),
        vendor_contact=transaction_data.get("vendor_contact"),
        vendor_tax_id=transaction_data.get("vendor_tax_id"),
        amount=transaction_data.get("amount"),
        currency=transaction_data.get("currency", "USD"),
        tax_amount=transaction_data.get("tax_amount"),
        subtotal=transaction_data.get("subtotal"),
        discount=transaction_data.get("discount"),
        transaction_date=transaction_data.get("transaction_date"),
        due_date=transaction_data.get("due_date"),
        payment_status=transaction_data.get("payment_status"),
        payment_method=transaction_data.get("payment_method"),
        transaction_type=transaction_data.get("transaction_type"),
        document_number=transaction_data.get("document_number"),
        reference_numbers=transaction_data.get("reference_numbers"),
        line_items=transaction_data.get("line_items"),
        description=transaction_data.get("description"),
        notes=transaction_data.get("notes")
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_transaction_by_id(
    db: Session,
    transaction_id: str,
    user_id: int
) -> Optional[models.Transaction]:
    """Get transaction by transaction_id"""
    return db.query(models.Transaction).filter(
        and_(
            models.Transaction.transaction_id == transaction_id,
            models.Transaction.user_id == user_id
        )
    ).first()


def get_user_transactions(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    vendor_name: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    category: Optional[str] = None
) -> List[models.Transaction]:
    """Get all transactions for a user with optional filtering"""
    query = db.query(models.Transaction).filter(models.Transaction.user_id == user_id)

    # Apply filters
    if vendor_name:
        query = query.filter(models.Transaction.vendor_name.ilike(f"%{vendor_name}%"))

    if start_date:
        query = query.filter(models.Transaction.transaction_date >= start_date)

    if end_date:
        query = query.filter(models.Transaction.transaction_date <= end_date)

    if min_amount:
        query = query.filter(models.Transaction.amount >= min_amount)

    if max_amount:
        query = query.filter(models.Transaction.amount <= max_amount)

    if category:
        # Join with categorizations to filter by category
        query = query.join(models.Categorization).filter(
            models.Categorization.category == category
        )

    return query.order_by(desc(models.Transaction.transaction_date)).offset(skip).limit(limit).all()


def search_transactions(
    db: Session,
    user_id: int,
    search_query: str,
    skip: int = 0,
    limit: int = 100
) -> List[models.Transaction]:
    """Full-text search for transactions"""
    search_pattern = f"%{search_query}%"

    return db.query(models.Transaction).filter(
        and_(
            models.Transaction.user_id == user_id,
            or_(
                models.Transaction.vendor_name.ilike(search_pattern),
                models.Transaction.description.ilike(search_pattern),
                models.Transaction.document_number.ilike(search_pattern)
            )
        )
    ).order_by(desc(models.Transaction.transaction_date)).offset(skip).limit(limit).all()


# ============================================================================
# VENDOR RESEARCH OPERATIONS
# ============================================================================

def get_or_create_vendor_research(
    db: Session,
    user_id: int,
    vendor_name: str,
    research_data: Dict
) -> models.VendorResearch:
    """Get existing vendor research or create new one"""
    normalized_name = vendor_name.lower().strip()

    # Try to find existing research
    existing = db.query(models.VendorResearch).filter(
        and_(
            models.VendorResearch.user_id == user_id,
            models.VendorResearch.normalized_name == normalized_name
        )
    ).first()

    if existing:
        # Update usage tracking
        existing.usage_count += 1
        existing.last_used = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    # Create new research
    vendor_research = models.VendorResearch(
        user_id=user_id,
        vendor_name=vendor_name,
        normalized_name=normalized_name,
        company_name=research_data.get("company_name"),
        description=research_data.get("description"),
        business_type=research_data.get("business_type"),
        products_services=research_data.get("products_services"),
        company_size=research_data.get("company_size"),
        locations=research_data.get("locations"),
        research_data=research_data,
        confidence_score=research_data.get("confidence_score", 0)
    )
    db.add(vendor_research)
    db.commit()
    db.refresh(vendor_research)
    return vendor_research


# ============================================================================
# CATEGORIZATION OPERATIONS
# ============================================================================

def create_categorization(
    db: Session,
    user_id: int,
    categorization_data: Dict,
    transaction_id: Optional[int] = None,
    bank_transaction_id: Optional[int] = None,
    vendor_research_id: Optional[int] = None
) -> models.Categorization:
    """Create a new categorization for either a document transaction or bank transaction"""
    categorization = models.Categorization(
        user_id=user_id,
        transaction_id=transaction_id,
        bank_transaction_id=bank_transaction_id,
        vendor_research_id=vendor_research_id,
        category=categorization_data.get("category"),
        subcategory=categorization_data.get("subcategory"),
        ledger_type=categorization_data.get("ledger_type"),
        method=categorization_data.get("method"),
        confidence_score=categorization_data.get("confidence_score"),
        ml_confidence=categorization_data.get("ml_confidence"),
        gemini_confidence=categorization_data.get("gemini_confidence"),
        explanation=categorization_data.get("explanation"),
        categorization_data=categorization_data,
        transaction_purpose=categorization_data.get("transaction_purpose", "")
    )
    db.add(categorization)
    db.commit()
    db.refresh(categorization)
    return categorization


def get_bank_transactions_by_statement(
    db: Session,
    user_id: int,
    bank_statement_id: int
) -> List[models.BankTransaction]:
    """Get all bank transactions for a specific statement"""
    return db.query(models.BankTransaction).filter(
        and_(
            models.BankTransaction.user_id == user_id,
            models.BankTransaction.bank_statement_id == bank_statement_id
        )
    ).order_by(models.BankTransaction.transaction_date).all()


def get_bank_statement_by_id(
    db: Session,
    user_id: int,
    statement_id: int
) -> Optional[models.BankStatement]:
    """Get a bank statement by ID"""
    return db.query(models.BankStatement).filter(
        and_(
            models.BankStatement.id == statement_id,
            models.BankStatement.user_id == user_id
        )
    ).first()


def get_categorization_for_bank_transaction(
    db: Session,
    user_id: int,
    bank_transaction_id: int
) -> Optional[models.Categorization]:
    """Get the categorization for a specific bank transaction"""
    return db.query(models.Categorization).filter(
        and_(
            models.Categorization.user_id == user_id,
            models.Categorization.bank_transaction_id == bank_transaction_id
        )
    ).first()


def update_bank_transaction_category(
    db: Session,
    bank_transaction_id: int,
    category: str
):
    """Update the category field on a bank transaction for quick access"""
    db.query(models.BankTransaction).filter(
        models.BankTransaction.id == bank_transaction_id
    ).update({"category": category})
    db.commit()


def update_categorization_approval(
    db: Session,
    categorization_id: int,
    user_id: int,
    approved: bool,
    modified: bool = False
):
    """Update categorization approval status"""
    db.query(models.Categorization).filter(
        and_(
            models.Categorization.id == categorization_id,
            models.Categorization.user_id == user_id
        )
    ).update({
        "user_approved": approved,
        "user_modified": modified
    })
    db.commit()


# ============================================================================
# USER CORRECTION OPERATIONS
# ============================================================================

def create_user_correction(
    db: Session,
    user_id: int,
    transaction_id: int,
    correction_data: Dict
) -> models.UserCorrection:
    """Create a user correction record"""
    correction = models.UserCorrection(
        user_id=user_id,
        transaction_id=transaction_id,
        categorization_id=correction_data.get("categorization_id"),
        original_category=correction_data.get("original_category"),
        original_subcategory=correction_data.get("original_subcategory"),
        original_ledger_type=correction_data.get("original_ledger_type"),
        original_method=correction_data.get("original_method"),
        corrected_category=correction_data.get("corrected_category"),
        corrected_subcategory=correction_data.get("corrected_subcategory"),
        corrected_ledger_type=correction_data.get("corrected_ledger_type"),
        correction_reason=correction_data.get("correction_reason"),
        user_feedback=correction_data.get("user_feedback"),
        learning_weight=correction_data.get("learning_weight", 1.0),
        correction_data=correction_data
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return correction


# ============================================================================
# BANK STATEMENT OPERATIONS
# ============================================================================

def create_bank_statement(
    db: Session,
    user_id: int,
    statement_data: Dict
) -> models.BankStatement:
    """Create a new bank statement"""
    statement = models.BankStatement(
        user_id=user_id,
        file_name=statement_data.get("file_name"),
        file_type=statement_data.get("file_type"),
        file_path=statement_data.get("file_path"),
        statement_date=statement_data.get("statement_date"),
        period_start=statement_data.get("period_start"),
        period_end=statement_data.get("period_end"),
        bank_name=statement_data.get("bank_name"),
        account_number=statement_data.get("account_number"),
        account_type=statement_data.get("account_type"),
        opening_balance=statement_data.get("opening_balance"),
        closing_balance=statement_data.get("closing_balance"),
        transaction_count=statement_data.get("transaction_count"),
        transactions_data=statement_data.get("transactions_data"),
        processed_at=datetime.utcnow()
    )
    db.add(statement)
    db.commit()
    db.refresh(statement)
    return statement


def create_bank_transaction(
    db: Session,
    user_id: int,
    bank_statement_id: int,
    transaction_data: Dict
) -> models.BankTransaction:
    """Create a bank transaction"""
    bank_transaction = models.BankTransaction(
        user_id=user_id,
        bank_statement_id=bank_statement_id,
        transaction_date=transaction_data.get("transaction_date"),
        description=transaction_data.get("description"),
        amount=transaction_data.get("amount"),
        transaction_type=transaction_data.get("transaction_type"),
        category=transaction_data.get("category"),
        reference=transaction_data.get("reference"),
        balance=transaction_data.get("balance")
    )
    db.add(bank_transaction)
    db.commit()
    db.refresh(bank_transaction)
    return bank_transaction


# ============================================================================
# RECONCILIATION OPERATIONS
# ============================================================================

def create_reconciliation_match(
    db: Session,
    user_id: int,
    transaction_id: int,
    bank_transaction_id: int,
    match_data: Dict
) -> models.ReconciliationMatch:
    """Create a reconciliation match"""
    match = models.ReconciliationMatch(
        user_id=user_id,
        transaction_id=transaction_id,
        bank_transaction_id=bank_transaction_id,
        match_type=match_data.get("match_type"),
        match_confidence=match_data.get("match_confidence"),
        name_match_score=match_data.get("name_match_score"),
        amount_match_score=match_data.get("amount_match_score"),
        date_match_score=match_data.get("date_match_score"),
        match_reason=match_data.get("match_reason"),
        match_data=match_data
    )
    db.add(match)
    db.commit()
    db.refresh(match)

    # Mark bank transaction as reconciled
    db.query(models.BankTransaction).filter(
        models.BankTransaction.id == bank_transaction_id
    ).update({
        "is_reconciled": True,
        "reconciled_at": datetime.utcnow()
    })
    db.commit()

    return match


def get_unreconciled_transactions(
    db: Session,
    user_id: int
) -> List[models.Transaction]:
    """Get all transactions that haven't been reconciled"""
    # Get transaction IDs that are already reconciled
    reconciled_ids = db.query(models.ReconciliationMatch.transaction_id).filter(
        models.ReconciliationMatch.user_id == user_id
    ).subquery()

    # Get transactions not in the reconciled list
    return db.query(models.Transaction).filter(
        and_(
            models.Transaction.user_id == user_id,
            ~models.Transaction.id.in_(reconciled_ids)
        )
    ).order_by(desc(models.Transaction.transaction_date)).all()


# ============================================================================
# ACTIVITY LOG OPERATIONS
# ============================================================================

def log_activity(
    db: Session,
    user_id: int,
    action: str,
    entity_type: str = None,
    entity_id: int = None,
    details: Dict = None,
    changes: Dict = None,
    ip_address: str = None,
    user_agent: str = None,
    session_id: str = None
):
    """Log user activity"""
    activity = models.ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id
    )
    db.add(activity)
    db.commit()


# ============================================================================
# STATISTICS AND ANALYTICS
# ============================================================================

def get_user_statistics(db: Session, user_id: int) -> Dict:
    """Get comprehensive user statistics"""
    total_documents = db.query(func.count(models.Document.id)).filter(
        models.Document.user_id == user_id
    ).scalar()

    total_transactions = db.query(func.count(models.Transaction.id)).filter(
        models.Transaction.user_id == user_id
    ).scalar()

    total_amount = db.query(func.sum(models.Transaction.amount)).filter(
        models.Transaction.user_id == user_id
    ).scalar() or 0

    categorized_count = db.query(func.count(models.Categorization.id)).filter(
        models.Categorization.user_id == user_id
    ).scalar()

    approved_count = db.query(func.count(models.Categorization.id)).filter(
        and_(
            models.Categorization.user_id == user_id,
            models.Categorization.user_approved == True
        )
    ).scalar()

    reconciled_count = db.query(func.count(models.ReconciliationMatch.id)).filter(
        models.ReconciliationMatch.user_id == user_id
    ).scalar()

    return {
        "total_documents": total_documents,
        "total_transactions": total_transactions,
        "total_amount": float(total_amount),
        "categorized_count": categorized_count,
        "approved_count": approved_count,
        "approval_rate": (approved_count / categorized_count * 100) if categorized_count > 0 else 0,
        "reconciled_count": reconciled_count
    }
