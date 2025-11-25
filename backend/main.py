import io
import asyncio
import json
from fastapi import FastAPI, UploadFile, File, Body, Form, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, field_validator
from dotenv import load_dotenv
import os
from typing import Optional, List, Literal
from datetime import datetime, date
from enum import Enum
# Rate limiting temporarily disabled - will be re-implemented with a different library
# from slowapi import Limiter, _rate_limit_exceeded_handler
# from slowapi.util import get_remote_address
# from slowapi.errors import RateLimitExceeded
from google import genai
from google.genai import types
from PyPDF2 import PdfReader, PdfWriter  # Install via pip install PyPDF2
from ml_categorization import get_ml_engine
from categories import get_all_categories, get_categories_by_parent, get_subcategories_for_category
from bank_statement_parser import BankStatementParser
from reconciliation_engine import ReconciliationEngine

# Database imports
from sqlalchemy.orm import Session
from database import get_db, init_db, test_connection
from auth import get_current_user, get_optional_user, authenticate_user, create_access_token, hash_password
import crud
import models

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Categorization Bot API", version="1.0.0")

# Initialize rate limiter - TEMPORARILY DISABLED due to conflicts with Pydantic request models
# TODO: Re-implement rate limiting with a different approach that doesn't conflict with Pydantic
# limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour", "50/minute"])
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS - configured via environment variable for security
# Default to localhost for development. In production, set CORS_ORIGINS in .env
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database initialization on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup"""
    try:
        print("Testing database connection...")
        if test_connection():
            print("Initializing database tables...")
            init_db()
            print("[OK] Database initialized successfully!")
        else:
            print("[WARNING] Database connection failed. Running without persistence.")
            print("  To enable database features:")
            print("  1. Install PostgreSQL")
            print("  2. Create database: categorization_bot")
            print("  3. Set DATABASE_URL in .env file")
    except Exception as e:
        print(f"[WARNING] Database initialization failed: {e}")
        print("  Application will run without data persistence.")

# Gemini API key loaded from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize ML Engine (lazy initialization on first use)
ml_engine = None

def get_ml_categorization_engine():
    """Get or initialize the ML categorization engine."""
    global ml_engine
    if ml_engine is None:
        if not PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY not found in environment variables")
        ml_engine = get_ml_engine(
            pinecone_api_key=PINECONE_API_KEY,
            gemini_api_key=GEMINI_API_KEY
        )
    return ml_engine

# Schema validation
class DocumentSchema(str, Enum):
    """Valid document schema types"""
    GENERIC = "generic"
    FORM_1040 = "1040"
    FORM_2848 = "2848"
    FORM_8821 = "8821"
    FORM_941 = "941"
    PAYROLL = "payroll"

# File validation configuration
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB in bytes
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/bmp",
    "image/tiff",
    "text/csv",
    "application/csv",
    "text/plain"  # CSV files sometimes reported as plain text
}
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".csv"}

async def validate_file_upload(file: UploadFile) -> None:
    """
    Validate uploaded file for security and size constraints.

    Raises HTTPException if validation fails.
    """
    # Check file extension
    if file.filename:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
            )

    # Check MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"MIME type not allowed. Allowed types: {', '.join(ALLOWED_MIME_TYPES)}"
        )

    # Check file size by reading in chunks to avoid loading entire file
    file_size = 0
    chunk_size = 1024 * 1024  # 1 MB chunks

    # Read file to check size
    content = await file.read()
    file_size = len(content)

    # Reset file pointer for later processing
    await file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.0f}MB"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Empty file not allowed"
        )

# Step 1: Raw extraction prompt remains unchanged.
RAW_PROMPT = "List every single thing exactly as it appears on the document, each column and row, in full"

# Helper function to load a schema file
def load_schema(schema_id):
    """
    Load the specified JSON schema from file
    
    Parameters:
    schema_id (str): Identifier for the schema to load
    
    Returns:
    dict: The loaded schema or None if not found
    """
    schema_mapping = {
        "1040": "1040.json",
        "2848": "2848.json",
        "8821": "8821.json",
        "941": "941.json",
        "payroll": "payroll.json",
        "generic": None  # Generic schema doesn't need a specific file
    }
    
    if schema_id not in schema_mapping:
        return None
        
    filename = schema_mapping.get(schema_id)
    if filename is None:
        return None
    
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to the project root
    project_root = os.path.dirname(script_dir)
    # Construct absolute path to the schema file
    schema_path = os.path.join(project_root, filename)
    
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading schema {schema_id} from {schema_path}: {e}")
        return None

# Function to generate a schema-specific prompt
def generate_schema_prompt(schema_id, extracted_text):
    """
    Generate a prompt for extraction based on the selected schema
    
    Parameters:
    schema_id (str): Identifier for the schema to use
    extracted_text (str): Raw text extracted from the document
    
    Returns:
    str: The prompt to use for extraction
    """
    # Load the requested schema
    schema = load_schema(schema_id)
    
    # Generic document schema for fallback
    GENERIC_SCHEMA = """
    {
      "documentMetadata": {
        "documentID": "Unique identifier for the document",
        "documentType": "Type/category (e.g., Invoice, Receipt, BankStatement, MerchantStatement, CreditMemo, PurchaseOrder, etc.)",
        "documentNumber": "Official reference number from the document",
        "documentDate": "YYYY-MM-DD (date issued)",
        "uploadDate": "YYYY-MM-DDTHH:MM:SSZ (date/time uploaded)",
        "source": {
          "name": "Name of the issuer (vendor, bank, customer, etc.)",
          "type": "Category (Vendor, Customer, Bank, etc.)",
          "contact": {
            "address": "Full address if available",
            "phone": "Contact phone number",
            "email": "Contact email address"
          }
        },
        "fileInfo": {
          "fileName": "Original file name",
          "fileType": "Format (e.g., PDF, JPEG)",
          "pageCount": "Number of pages in the document",
          "OCRProcessed": "Boolean flag indicating whether OCR has been applied"
        }
      },
      "financialData": {
        "currency": "Currency code (e.g., USD, EUR)",
        "subtotal": "Amount before any discounts or additional fees",
        "taxAmount": "Total tax applied (if any) – can be zero or omitted if not applicable",
        "discount": "Any discounts or adjustments applied",
        "totalAmount": "Final total monetary value on the document",
        "paymentStatus": "Status (e.g., Paid, Unpaid, Pending)",
        "paymentTerms": "Terms such as 'Net 30'",
        "dueDate": "YYYY-MM-DD (if a due date is specified)"
      },
      "lineItems": [
        {
          "itemID": "Unique identifier for the line item or transaction",
          "description": "Short description of the product, service, or transaction",
          "quantity": "Number of units or hours (if invoicing for services)",
          "unit": "Unit of measure (e.g., hours, pieces, kg, etc.)",
          "unitPrice": "Price per unit or hourly rate",
          "totalPrice": "Calculated total for the line item",
          "tax": "Tax amount applicable to this line item (if any)",
          "transactionType": "For bank/merchant statements (e.g., Debit, Credit)",
          "balance": "Running balance after the transaction (if applicable)",
          "category": "Optional field to classify the line item (e.g., Service, Product)"
        }
      ],
      "partyInformation": {
        "vendor": {
          "name": "Vendor/Supplier name",
          "address": "Vendor address",
          "contact": "Vendor contact details (phone/email)",
          "taxID": "Tax identifier if available (optional)"
        },
        "customer": {
          "name": "Customer name",
          "address": "Customer address",
          "contact": "Customer contact details",
          "customerID": "Internal customer identifier"
        },
        "bankDetails": {
          "bankName": "Name of the bank",
          "accountNumber": "Bank account number",
          "routingNumber": "Routing or sort code"
        }
      },
      "paymentInformation": {
        "paymentMethod": "Method (e.g., Cash, Credit Card, EFT, Direct Deposit)",
        "transactionID": "Identifier for electronically processed payments",
        "paidDate": "YYYY-MM-DD (date when payment was made)",
        "bankDetails": {
          "bankName": "If relevant, bank name for the transaction",
          "accountNumber": "Account number associated with payment",
          "routingNumber": "Routing number for bank transfers"
        }
      },
      "fixedAssetData": {
        "assetID": "Unique asset identifier",
        "description": "Description of the fixed asset or inventory item",
        "acquisitionDate": "YYYY-MM-DD (date of purchase/acquisition)",
        "purchasePrice": "Cost of acquiring the asset",
        "depreciationMethod": "Method used (e.g., Straight-line, Declining Balance)",
        "currentValue": "Current book value of the asset",
        "location": "Physical location of the asset (if applicable)"
      },
      "additionalData": {
        "notes": "Any annotations or internal comments",
        "attachments": [
          "Link(s) or reference(s) to supplementary files, if applicable"
        ],
        "referenceNumbers": [
          "Other relevant reference numbers (e.g., purchase order numbers, shipping numbers)"
        ],
        "auditTrail": [
          {
            "action": "Description of the processing step (e.g., 'uploaded', 'OCR extracted')",
            "timestamp": "YYYY-MM-DDTHH:MM:SSZ",
            "user": "User or system that performed the action"
          }
        ]
      }
    }
    """
    
    # Base prompt template
    prompt_template = """
    Format the following extracted text into a JSON object that strictly follows the schema below. Ensure that the output is valid JSON with no additional commentary.
    
    Schema:
    {schema}
    
    Extracted Text:
    {extracted_text}
    """
    
    # If we have a specific schema, use it; otherwise, use the generic one
    if schema:
        schema_json = json.dumps(schema, indent=2)
        
        # For tax forms, add some specific instructions
        if schema_id in ["1040", "2848", "8821", "941"]:
            schema_prompt = f"""
            Format the following extracted text from an IRS tax form into a JSON object that strictly follows the schema below.
            This is specifically for IRS Form {schema_id}. Pay special attention to the form fields, numbers, checkboxes, and taxpayer information.
            
            Schema:
            {schema_json}
            
            Extracted Text:
            {extracted_text}
            """
        # For payroll data
        elif schema_id == "payroll":
            schema_prompt = f"""
            Format the following extracted text from a payroll document into a JSON object that strictly follows the schema below.
            This is specifically for payroll data. Pay special attention to employee details, earnings, deductions, and tax information.
            
            Schema:
            {schema_json}
            
            Extracted Text:
            {extracted_text}
            """
        else:
            schema_prompt = prompt_template.format(schema=schema_json, extracted_text=extracted_text)
    else:
        # Use the generic schema as fallback
        schema_prompt = prompt_template.format(schema=GENERIC_SCHEMA, extracted_text=extracted_text)
    
    return schema_prompt

def detect_document_type(json_data):
    """
    Detect the document type from the JSON data to apply appropriate verification rules.
    
    Parameters:
    json_data (dict): The structured JSON data extracted from the document
    
    Returns:
    str: Document type - 'invoice', 'receipt', 'payment_processing', 'bank_statement', or 'other'
    """
    # Get the document type from metadata if available
    doc_type = json_data.get("documentMetadata", {}).get("documentType", "").lower()
    
    # Check for specific document type indicators
    if doc_type in ["merchantstatement", "merchant_statement", "payment_processing_statement", 
                    "processor_statement", "acquirer_statement"]:
        return "payment_processing"
    
    # Check for bank statement indicators
    if doc_type in ["bankstatement", "bank_statement", "account_statement"]:
        return "bank_statement"
    
    # Check for invoice indicators
    if doc_type in ["invoice", "bill"]:
        return "invoice"
    
    # Check for receipt indicators
    if doc_type in ["receipt", "sales_receipt"]:
        return "receipt"
    
    # If no explicit type, analyze the content to determine type
    
    # Check for payment processing statement indicators
    if any(keyword in str(json_data).lower() for keyword in 
           ["interchange", "merchant id", "card summary", "chargebacks", 
            "settlement", "processor", "acquirer", "mastercard", "visa fees"]):
        return "payment_processing"
    
    # Check for card transaction indicators (high volume of transactions)
    line_items = json_data.get("lineItems", [])
    if len(line_items) > 20 and any("card" in str(item).lower() for item in line_items):
        return "payment_processing"
    
    # Check for special fields that indicate payment processing
    if "credits" in str(json_data).lower() and "sales" in str(json_data).lower() and "settlement" in str(json_data).lower():
        return "payment_processing"
    
    # Check for indicators of a bank statement
    if any(keyword in str(json_data).lower() for keyword in 
           ["account number", "routing number", "beginning balance", "ending balance", 
            "deposits", "withdrawals", "account summary"]):
        return "bank_statement"
    
    # Check for invoice indicators (if not already detected)
    if "invoice" in str(json_data).lower() or "bill to" in str(json_data).lower():
        return "invoice"
    
    # Default to invoice verification rules if we can't determine
    return "invoice"

async def verify_extraction(json_data):
    """
    Verify the mathematical accuracy of the extracted data by focusing on 
    calculation discrepancies rather than trivial formatting differences.
    
    Parameters:
    json_data (dict): The structured JSON data extracted from the document
    
    Returns:
    dict: Original JSON with added extraction verification results
    """
    try:
        # First, detect document type to apply appropriate verification rules
        document_type = detect_document_type(json_data)
        
        # Update the prompt to focus on mathematical verification
        verification_prompt = f"""
        Analyze this financial document data to verify MATHEMATICAL ACCURACY only.
        
        DOCUMENT TYPE: {document_type.upper()}
        
        CRITICAL INSTRUCTIONS:
        1. IGNORE all formatting differences (e.g., "90" vs 90, spaces, character encoding)
        2. IGNORE data type differences (string vs number) - only care about the numeric value
        3. FOCUS ONLY on verification of financial calculations:
           - For invoices: Check if quantity × price = line totals
           - For all documents: Verify line items sum up to stated subtotals or totals
           - Check if subtotal + tax = total amount (where applicable)
           - For statements: Verify opening balance + transactions = closing balance
         
        4. Mathematical rules that should be checked:
           - Line items: quantity × unit price = line total
           - Document totals: sum of line totals = subtotal
           - Tax calculation: subtotal × tax rate = tax amount
           - Final total: subtotal + tax + fees - discounts = total amount
        
        Financial Data:
        {json.dumps(json_data, indent=2)}
        
        Return your verification as JSON with this strict structure:
        {{
          "extractionVerified": Boolean (true if calculations are accurate, false if calculation errors exist),
          "discrepancies": [
            {{
              "type": "String (Line Total, Subtotal, Tax Calculation, etc.)",
              "location": "String (reference to where in the document this calculation occurs)",
              "expectedValue": "Number (what the calculation should produce)",
              "extractedValue": "Number (what was extracted in the document)",
              "likelyCorrectValue": "Number (the most likely correct value)",
              "formula": "String (the formula used for this calculation)",
              "confidence": "String (High, Medium, Low)"
            }}
          ],
          "summary": "String (brief explanation of calculation verification results)"
        }}
        
        ONLY include discrepancies that are TRUE CALCULATION ERRORS where numbers don't add up correctly.
        DO NOT flag differences in formatting, string representations, or character encoding.
        """
        
        # Make the API call to Gemini
        verification_response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=[verification_prompt],
            config={
                "max_output_tokens": 4000,
                "response_mime_type": "application/json"
            }
        )
        
        # Extract verification results
        try:
            verification_results = json.loads(verification_response.text)
            
            # Keep only significant calculation discrepancies
            if "discrepancies" in verification_results and len(verification_results["discrepancies"]) > 0:
                # Filter out any discrepancies where the numeric values are actually the same
                significant_issues = []
                for d in verification_results["discrepancies"]:
                    # Try to convert both values to floats for comparison
                    try:
                        expected = float(str(d.get("expectedValue", "0")).replace(",", ""))
                        actual = float(str(d.get("extractedValue", "0")).replace(",", ""))
                        
                        # Only keep discrepancies where values are numerically different
                        if abs(expected - actual) > 0.01:  # Allow for small rounding differences
                            significant_issues.append(d)
                    except:
                        # If we can't convert to float, keep the discrepancy
                        significant_issues.append(d)
                
                verification_results["discrepancies"] = significant_issues
                
                # Update the verification status based on filtered discrepancies
                verification_results["extractionVerified"] = len(significant_issues) == 0
                
                # Update summary if needed
                if len(significant_issues) == 0 and not verification_results["extractionVerified"]:
                    verification_results["summary"] = "No significant calculation discrepancies found after filtering."
                    verification_results["extractionVerified"] = True
            
            # Add verification results to the original JSON
            json_data["extractionVerification"] = verification_results
            
        except json.JSONDecodeError as e:
            # If the response isn't valid JSON, create a simple error structure
            json_data["extractionVerification"] = {
                "extractionVerified": False,
                "discrepancies": [],
                "summary": f"Error parsing verification results: {str(e)}",
                "rawResponse": verification_response.text
            }
        
        return json_data
        
    except Exception as e:
        # If verification fails, add error information to the JSON
        json_data["extractionVerification"] = {
            "extractionVerified": False,
            "discrepancies": [],
            "summary": f"Error during extraction verification: {str(e)}"
        }
        return json_data

async def process_page(page, schema="generic"):
    # Write the individual page to a BytesIO stream.
    pdf_writer = PdfWriter()
    pdf_writer.add_page(page)
    page_stream = io.BytesIO()
    pdf_writer.write(page_stream)
    page_stream.seek(0)

    # Create a Gemini Part from the page bytes.
    file_part = types.Part.from_bytes(
        data=page_stream.getvalue(),
        mime_type="application/pdf"
    )

    # Step 1: Extract raw text from the page.
    raw_response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.0-flash",
        contents=[RAW_PROMPT, file_part],
        config={
            "max_output_tokens": 40000,
            "response_mime_type": "text/plain"
        }
    )
    raw_text = raw_response.text

    # Step 2: Convert the raw text into structured JSON using the schema-specific prompt
    json_prompt = generate_schema_prompt(schema, raw_text)
    json_response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.0-flash",
        contents=[json_prompt],
        config={
            "max_output_tokens": 40000,
            "response_mime_type": "application/json"
        }
    )
    
    # Return the JSON response to be merged later
    return json_response.text

def deep_merge(base, addition):
    """
    Recursively merge two dictionaries.
    - Lists are concatenated
    - Dictionaries are merged recursively
    - For other values, non-null values are preferred over null values
    - For other cases where both values are non-null, the first occurrence (base) is kept
    
    Parameters:
    base (dict): The base dictionary to merge into
    addition (dict): The dictionary to merge from
    
    Returns:
    dict: The merged dictionary
    """
    # Create a copy to avoid modifying the original
    result = base.copy()
    
    for key, value in addition.items():
        # If key not in result, just add it
        if key not in result:
            result[key] = value
        else:
            # If both are lists, extend the base list
            if isinstance(result[key], list) and isinstance(value, list):
                result[key].extend(value)
            
            # If both are dictionaries, merge them recursively
            elif isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = deep_merge(result[key], value)
            
            # For boolean values, use logical OR (True if either is True)
            elif isinstance(result[key], bool) and isinstance(value, bool):
                result[key] = result[key] or value
            
            # For other values, prefer non-null values over null/empty ones
            elif result[key] is None and value is not None:
                result[key] = value
            # If both values exist and neither is None, keep the base value (first page)
    
    return result

def merge_page_results(page_results):
    """
    Merge JSON results from multiple pages.
    For document-level fields, we assume they are the same across pages and only keep the first occurrence.
    For list fields, we concatenate them, regardless of where they appear in the JSON structure.
    """
    merged = None
    
    # Process each page
    for result in page_results:
        try:
            data = json.loads(result)
        except json.JSONDecodeError:
            continue  # Optionally log or handle the error
            
        if merged is None:
            merged = data
        else:
            # Use deep merge to recursively combine the data
            merged = deep_merge(merged, data)
    
    # Remove any extractionVerification fields - we'll perform a new verification on the complete document
    if merged and "extractionVerification" in merged:
        del merged["extractionVerification"]
            
    return merged

@app.post("/process-pdf")
async def process_file(
    file: UploadFile = File(...),
    schema: str = Form("generic"),
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Process a document (PDF or image) and extract structured data.

    If user is authenticated, document will be saved to database for history.
    """
    # Validate schema parameter
    valid_schemas = [s.value for s in DocumentSchema]
    if schema not in valid_schemas:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schema. Must be one of: {', '.join(valid_schemas)}"
        )

    # Validate file upload
    await validate_file_upload(file)

    file_content = await file.read()

    # Generate unique document ID
    import uuid
    document_id = str(uuid.uuid4())

    # Save document to database if user is authenticated
    db_document = None
    if current_user:
        try:
            db_document = crud.create_document(
                db=db,
                user_id=current_user.id,
                document_id=document_id,
                file_name=file.filename,
                file_type=file.content_type,
                file_size=len(file_content),
                schema_type=schema
            )

            # Update status to processing
            crud.update_document_status(
                db=db,
                document_id=document_id,
                user_id=current_user.id,
                status="processing",
                progress=10
            )

            # Log activity
            crud.log_activity(
                db=db,
                user_id=current_user.id,
                action="document_uploaded",
                entity_type="document",
                entity_id=db_document.id,
                details={"file_name": file.filename, "schema": schema}
            )
        except Exception as e:
            print(f"Warning: Failed to save document to database: {e}")

    try:
        if file.content_type == "application/pdf":
            pdf_reader = PdfReader(io.BytesIO(file_content))
            # Process each page concurrently using the per-page processing function.
            tasks = [process_page(page, schema) for page in pdf_reader.pages]
            page_results = await asyncio.gather(*tasks)
            
            # Merge the JSON results from each page.
            merged_result = merge_page_results(page_results)
            
            # Perform extraction verification on the complete document
            final_result = await verify_extraction(merged_result)
            
            combined_response_text = json.dumps(final_result, indent=2)
        else:
            # For non-PDF files, process with schema selection
            file_part = types.Part.from_bytes(
                data=file_content,
                mime_type=file.content_type
            )
            raw_response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=[RAW_PROMPT, file_part],
                config={
                    "max_output_tokens": 40000,
                    "response_mime_type": "text/plain"
                }
            )
            raw_text = raw_response.text
            
            # Use schema-specific prompt template
            json_prompt = generate_schema_prompt(schema, raw_text)
            
            json_response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=[json_prompt],
                config={
                    "max_output_tokens": 40000,
                    "response_mime_type": "application/json"
                }
            )
            
            # For non-PDF files (single page), add extraction verification
            try:
                json_data = json.loads(json_response.text)
                final_json = await verify_extraction(json_data)
                combined_response_text = json.dumps(final_json, indent=2)
            except json.JSONDecodeError:
                combined_response_text = json_response.text

        # Save final result to database if user is authenticated
        if current_user and db_document:
            try:
                # Parse the JSON response
                parsed_data = json.loads(combined_response_text)

                # Save parsed data to database
                crud.update_document_parsed_data(
                    db=db,
                    document_id=document_id,
                    user_id=current_user.id,
                    parsed_data=parsed_data,
                    extraction_verified=parsed_data.get("extractionVerification", {}).get("extractionVerified", False),
                    verification_data=parsed_data.get("extractionVerification")
                )

                # Update status to completed
                crud.update_document_status(
                    db=db,
                    document_id=document_id,
                    user_id=current_user.id,
                    status="completed",
                    progress=100
                )

                # Extract and save transactions
                vendor_name = parsed_data.get("partyInformation", {}).get("vendor", {}).get("name")
                line_items = parsed_data.get("lineItems", [])

                # If we have line items, save them as transactions
                if line_items:
                    for idx, item in enumerate(line_items):
                        try:
                            transaction_id = f"{document_id}-{idx}"
                            crud.create_transaction(
                                db=db,
                                user_id=current_user.id,
                                document_id=db_document.id,
                                transaction_id=transaction_id,
                                vendor_name=vendor_name or item.get("description"),
                                amount=float(item.get("totalPrice", 0) or 0),
                                transaction_date=parsed_data.get("documentMetadata", {}).get("documentDate"),
                                description=item.get("description"),
                                transaction_type=parsed_data.get("documentMetadata", {}).get("documentType"),
                                line_items=[item]
                            )
                        except Exception as e:
                            print(f"Warning: Failed to save transaction {idx}: {e}")

                # Log completion
                crud.log_activity(
                    db=db,
                    user_id=current_user.id,
                    action="document_processed",
                    entity_type="document",
                    entity_id=db_document.id,
                    details={"document_id": document_id, "transactions_count": len(line_items)}
                )
            except Exception as e:
                print(f"Warning: Failed to save processed data to database: {e}")
                # Update status to error
                if db_document:
                    try:
                        crud.update_document_status(
                            db=db,
                            document_id=document_id,
                            user_id=current_user.id,
                            status="error",
                            error_message=str(e)
                        )
                    except:
                        pass

        # Return the merged Gemini response with document ID
        return {
            "response": combined_response_text.strip(),
            "document_id": document_id if current_user else None
        }
    except Exception as e:
        # Update document status to error if user is authenticated
        if current_user and db_document:
            try:
                crud.update_document_status(
                    db=db,
                    document_id=document_id,
                    user_id=current_user.id,
                    status="error",
                    error_message=str(e)
                )
            except:
                pass

        return {"error": "Request failed", "detail": str(e)}

# Define request model for vendor research
class VendorResearchRequest(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=500, description="Vendor name to research")

    @field_validator('vendor_name')
    @classmethod
    def validate_vendor_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Vendor name cannot be empty or whitespace")
        return v.strip()

@app.post("/research-vendor")
async def research_vendor(
    request: VendorResearchRequest,
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Research a vendor using Google Search.

    Results are cached in database if user is authenticated to avoid redundant API calls.
    """
    vendor_name = request.vendor_name

    if not vendor_name:
        return {"error": "No vendor name provided"}

    # Check cache if user is authenticated
    if current_user:
        try:
            cached_research = crud.get_or_create_vendor_research(
                db=db,
                user_id=current_user.id,
                vendor_name=vendor_name,
                fetch_if_missing=False  # Just check cache first
            )

            if cached_research and cached_research.research_data:
                # Return cached result
                print(f"Returning cached vendor research for: {vendor_name}")
                return {"response": cached_research.research_data.get("response", "")}
        except Exception as e:
            print(f"Warning: Failed to check vendor research cache: {e}")

    try:
        # Create a specific prompt asking for the single most likely entity and detailed info about it
        prompt = f"""
        Research the vendor "{vendor_name}" and identify the SINGLE most likely business or entity that this name refers to. 
        
        IMPORTANT: DO NOT list multiple possible interpretations or multiple businesses.
        Determine the most probable, prominent, or common business that matches this name and ONLY provide information about that ONE business.
        
        For this single most likely business, provide as much detail as possible about:
        - What this company does (main business focus)
        - Their products or services in detail
        - Company size, scale of operations, and market position
        - Company history and important milestones
        - Locations, reach, or distribution
        - Any other relevant details that would be helpful to know
        
        Again, I want information about the single most likely match only, not a list of possibilities.
        """
        
        # Use Google Search as a tool for grounding
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # Send the request to Gemini API with search enabled
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],
                response_modalities=["TEXT"],
                temperature=0.2, # Lower temperature to make response more focused
            )
        )
        
        # Save result to database if user is authenticated
        if current_user:
            try:
                crud.save_vendor_research(
                    db=db,
                    user_id=current_user.id,
                    vendor_name=vendor_name,
                    research_data={"response": response.text},
                    company_name=vendor_name,  # Could parse from response
                    description=response.text[:500] if len(response.text) > 500 else response.text
                )

                # Log activity
                crud.log_activity(
                    db=db,
                    user_id=current_user.id,
                    action="vendor_researched",
                    entity_type="vendor_research",
                    details={"vendor_name": vendor_name}
                )
            except Exception as e:
                print(f"Warning: Failed to save vendor research to database: {e}")

        # Return the response as-is
        return {"response": response.text}

    except Exception as e:
        print(f"Error researching vendor: {str(e)}")
        return {"error": f"Error researching vendor: {str(e)}"}

# Enhanced vendor research for ambiguous cases
class EnhancedResearchRequest(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=500, description="Vendor name to research")
    transaction_context: dict = Field(..., description="Additional context about the transaction")
    confidence_threshold: int = Field(70, ge=0, le=100, description="Minimum confidence to skip research (0-100)")

    @field_validator('vendor_name')
    @classmethod
    def validate_vendor_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Vendor name cannot be empty or whitespace")
        return v.strip()


@app.post("/research-vendor-enhanced")
async def research_vendor_enhanced(
    body: EnhancedResearchRequest,
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Enhanced vendor research for ambiguous or low-confidence transactions.

    Uses multiple analysis approaches:
    1. Industry classification
    2. Business type identification
    3. Typical transaction categorization
    4. Confidence scoring
    5. Red flag detection

    Results cached in database if user is authenticated.
    """
    vendor_name = body.vendor_name

    if not vendor_name:
        return {"error": "No vendor name provided"}

    # Check cache if user is authenticated
    if current_user:
        try:
            cached_research = crud.get_or_create_vendor_research(
                db=db,
                user_id=current_user.id,
                vendor_name=vendor_name,
                fetch_if_missing=False
            )

            if cached_research and cached_research.research_data:
                # Check if we have enhanced research data
                if cached_research.research_data.get("enhanced"):
                    print(f"Returning cached enhanced research for: {vendor_name}")
                    return cached_research.research_data
        except Exception as e:
            print(f"Warning: Failed to check research cache: {e}")

    try:
        # Enhanced research prompt with multiple analysis dimensions
        prompt = f"""
        Perform a comprehensive analysis of the vendor "{vendor_name}" for financial categorization purposes.

        Provide analysis in the following JSON structure:
        {{
            "vendorIdentification": {{
                "primaryName": "Most likely official business name",
                "aliases": ["Alternative names or abbreviations"],
                "confidence": "Score 0-100 on vendor identification certainty"
            }},
            "businessProfile": {{
                "industry": "Primary industry classification",
                "businessType": "Type of business (e.g., retailer, service provider, manufacturer)",
                "products": ["Main products or services offered"],
                "scale": "Business scale (local, regional, national, international)",
                "publiclyTraded": "Boolean - is this a public company"
            }},
            "categorizationGuidance": {{
                "typicalCategories": ["Most common expense categories for transactions with this vendor"],
                "reasoning": "Why these categories apply",
                "confidence": "Score 0-100 on categorization guidance certainty"
            }},
            "transactionContext": {{
                "commonTransactionTypes": ["Types of transactions typically made with this vendor"],
                "typicalAmountRanges": "Typical transaction amount ranges",
                "frequency": "How often businesses typically transact with this vendor"
            }},
            "ambiguityFactors": {{
                "nameClarity": "Score 0-100: How clear/unambiguous is the vendor name (100 = very clear)",
                "multipleMatches": "Boolean - could this name match multiple different businesses",
                "genericName": "Boolean - is this a generic/common business name",
                "industryAmbiguity": "Boolean - could this vendor operate in multiple industries"
            }},
            "redFlags": {{
                "hasFlags": "Boolean - any concerns detected",
                "flags": ["List of any concerns or unusual factors"],
                "severity": "low/medium/high"
            }},
            "overallConfidence": "Score 0-100: Overall confidence in this research",
            "recommendedAction": "What should be done next: 'accept' (high confidence), 'review' (medium confidence), 'manual_review' (low confidence)",
            "summary": "2-3 sentence summary of the vendor and key considerations for categorization"
        }}

        Transaction Context (if available):
        {json.dumps(body.transaction_context, indent=2) if body.transaction_context else "No additional context"}

        IMPORTANT: Be conservative with confidence scores. If there's any ambiguity, indicate it clearly.
        """

        # Use Google Search as a tool for grounding
        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        # Send the request to Gemini API with search enabled
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[google_search_tool],
                response_modalities=["TEXT"],
                response_mime_type="application/json",
                temperature=0.2,
            )
        )

        # Parse the response
        try:
            research_data = json.loads(response.text)
            research_data["enhanced"] = True  # Mark as enhanced research
            research_data["vendor_name"] = vendor_name
            research_data["timestamp"] = datetime.utcnow().isoformat()

            # Save to database if user is authenticated
            if current_user:
                try:
                    crud.save_vendor_research(
                        db=db,
                        user_id=current_user.id,
                        vendor_name=vendor_name,
                        research_data=research_data,
                        company_name=research_data.get("vendorIdentification", {}).get("primaryName", vendor_name),
                        description=research_data.get("summary", ""),
                        confidence_score=research_data.get("overallConfidence", 0)
                    )

                    # Log activity
                    crud.log_activity(
                        db=db,
                        user_id=current_user.id,
                        action="enhanced_vendor_research",
                        entity_type="vendor_research",
                        details={
                            "vendor_name": vendor_name,
                            "confidence": research_data.get("overallConfidence"),
                            "recommended_action": research_data.get("recommendedAction")
                        }
                    )
                except Exception as e:
                    print(f"Warning: Failed to save enhanced research: {e}")

            return research_data

        except json.JSONDecodeError:
            # If response isn't valid JSON, return error
            return {
                "error": "Failed to parse research response",
                "raw_response": response.text,
                "enhanced": True
            }

    except Exception as e:
        print(f"Error in enhanced vendor research: {str(e)}")
        return {"error": f"Error in enhanced vendor research: {str(e)}"}


# Define request model for financial categorization
class FinancialCategorizationRequest(BaseModel):
    vendor_info: str = Field(..., min_length=1, max_length=500, description="Vendor information")
    document_data: dict = Field(..., description="Transaction document data")
    transaction_purpose: str = Field("", max_length=1000, description="Transaction purpose")

    @field_validator('vendor_info')
    @classmethod
    def validate_vendor_info(cls, v):
        if not v or not v.strip():
            raise ValueError("Vendor info cannot be empty or whitespace")
        return v.strip()

@app.post("/categorize-transaction")
async def categorize_transaction(request: FinancialCategorizationRequest):
    vendor_info = request.vendor_info
    document_data = request.document_data
    transaction_purpose = request.transaction_purpose
    
    if not vendor_info or not document_data:
        return {"error": "Missing required information"}
    
    try:
        # Create a prompt that includes the categorization options and asks Gemini to categorize the transaction
        prompt = f"""
        Based on the information below, please categorize this transaction according to accounting principles.

        CRITICAL INSTRUCTION: You must categorize from the perspective of the INVOICE RECIPIENT (the customer being billed), NOT from the vendor's perspective.

        For example:
        - If this is an invoice FROM a vendor TO our business, it should typically be categorized as an Expense, Asset, or Liability
        - If this is a receipt we issued TO a customer FROM our business, it would be categorized as Revenue

        This categorization is for the accounting records of the business RECEIVING the invoice/document.

        Return a JSON object with the following structure:
        {{
            "companyName": "The name of the company that issued the invoice (the vendor)",
            "description": "A detailed description of what this business does",
            "category": "The most appropriate accounting category from the list below",
            "subcategory": "The most appropriate subcategory",
            "ledgerType": "The ledger entry type",
            "confidence": "A confidence score from 0-100 indicating how certain you are about this categorization. Consider factors like: clarity of vendor name, specificity of transaction details, alignment with typical business patterns, and ambiguity in the data.",
            "confidenceFactors": {{
                "vendorClarity": "Score 0-100: How clear and unambiguous is the vendor name",
                "dataCompleteness": "Score 0-100: How complete is the transaction data",
                "categoryFit": "Score 0-100: How well does the transaction fit the chosen category",
                "ambiguityLevel": "Score 0-100: Overall ambiguity (100 = very clear, 0 = very ambiguous)"
            }},
            "explanation": "A detailed explanation of why this categorization was chosen, including the factors considered and accounting principles applied",
            "needsResearch": "Boolean - true if additional vendor research would significantly improve categorization confidence"
        }}
        
        Here are the available categories, subcategories, and ledger types:
        
        Parent Category | Subcategory | Ledger Entry Type
        ---------------|-------------|------------------
        Revenue | Product Sales | Revenue
        Revenue | Service Revenue | Revenue
        Revenue | Rental Revenue | Revenue
        Revenue | Commission Revenue | Revenue
        Revenue | Subscription Revenue | Revenue
        Revenue | Other Income | Revenue
        Cost of Goods Sold (COGS) | Raw Materials | Expense (COGS)
        Cost of Goods Sold (COGS) | Direct Labor | Expense (COGS)
        Cost of Goods Sold (COGS) | Manufacturing Overhead | Expense (COGS)
        Cost of Goods Sold (COGS) | Freight and Delivery | Expense (COGS)
        Operating Expenses | Salaries and Wages | Expense (Operating)
        Operating Expenses | Rent | Expense (Operating)
        Operating Expenses | Utilities | Expense (Operating)
        Operating Expenses | Office Supplies | Expense (Operating)
        Operating Expenses | Business Software / IT Expenses | Expense (Operating)
        Operating Expenses | HR Expenses | Expense (Operating)
        Operating Expenses | Marketing and Advertising | Expense (Operating)
        Operating Expenses | Travel and Entertainment | Expense (Operating)
        Operating Expenses | Insurance | Expense (Operating)
        Operating Expenses | Repairs and Maintenance | Expense (Operating)
        Operating Expenses | Depreciation | Expense (Operating)
        Administrative Expenses | Professional Fees | Expense (Administrative)
        Administrative Expenses | Office Expenses | Expense (Administrative)
        Administrative Expenses | Postage and Shipping | Expense (Administrative)
        Administrative Expenses | Communication Expense | Expense (Administrative)
        Administrative Expenses | Bank Fees and Charges | Expense (Administrative)
        Financial Expenses | Interest Expense | Expense (Financial)
        Financial Expenses | Loan Fees | Expense (Financial)
        Financial Expenses | Credit Card Fees | Expense (Financial)
        Other Expenses | Miscellaneous | Expense (Other)
        Other Expenses | Donations/Charitable Contributions | Expense (Other)
        Other Expenses | Loss on Disposal of Assets | Expense (Other)
        Assets – Current | Cash and Cash Equivalents | Asset (Current)
        Assets – Current | Accounts Receivable | Asset (Current)
        Assets – Current | Inventory | Asset (Current)
        Assets – Current | Prepaid Expenses | Asset (Current)
        Assets – Current | Short-term Investments | Asset (Current)
        Assets – Fixed / Long-term | Property, Plant, and Equipment | Asset (Fixed)
        Assets – Fixed / Long-term | Furniture and Fixtures | Asset (Fixed)
        Assets – Fixed / Long-term | Vehicles | Asset (Fixed)
        Assets – Fixed / Long-term | Machinery and Equipment | Asset (Fixed)
        Assets – Fixed / Long-term | Computer Equipment | Asset (Fixed)
        Assets – Intangible | Patents | Asset (Intangible)
        Assets – Intangible | Trademarks | Asset (Intangible)
        Assets – Intangible | Copyrights | Asset (Intangible)
        Assets – Intangible | Goodwill | Asset (Intangible)
        Assets – Intangible | Capitalized Software | Asset (Intangible)
        Liabilities – Current | Accounts Payable | Liability (Current)
        Liabilities – Current | Short-term Loans | Liability (Current)
        Liabilities – Current | Accrued Liabilities | Liability (Current)
        Liabilities – Current | Current Portion of Long-term Debt | Liability (Current)
        Liabilities – Long-term | Long-term Loans | Liability (Long-term)
        Liabilities – Long-term | Bonds Payable | Liability (Long-term)
        Liabilities – Long-term | Deferred Tax Liabilities | Liability (Long-term)
        Equity | Common Stock | Equity
        Equity | Retained Earnings | Equity
        Equity | Additional Paid-in Capital | Equity
        Equity | Dividends/Distributions | Equity
        Adjusting / Journal Entries | Accruals/Deferrals/Depreciation Adjustments | Adjustment
        
        Vendor Information (the seller/company that sent the invoice):
        {vendor_info}
        
        Document Data:
        {json.dumps(document_data, indent=2)}
        
        Transaction Purpose (what the invoice is for):
        {transaction_purpose}
        
        REMEMBER: Categorize from the perspective of the business RECEIVING this invoice - the customer being billed, NOT from the perspective of the vendor who issued it.
        
        In the explanation field, be thorough about why this specific category, subcategory, and ledger type was chosen. 
        Consider the nature of the transaction, the items or services involved, accounting best practices, and how this 
        classification aligns with standard chart of accounts structures.
        """
        
        # Send the request to Gemini API
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "max_output_tokens": 4000,
                "response_mime_type": "application/json"
            }
        )
        
        # Return the response
        try:
            # Try to parse the response as JSON
            categorization_json = json.loads(response.text)
            return {"response": categorization_json}
        except json.JSONDecodeError:
            # If it's not valid JSON, return the raw text
            return {"response": response.text}
            
    except Exception as e:
        print(f"Error categorizing transaction: {str(e)}")
        return {"error": f"Error categorizing transaction: {str(e)}"}

# Smart categorization with automatic ambiguity resolution
class SmartCategorizationRequest(BaseModel):
    vendor_name: str = Field(..., min_length=1, max_length=500, description="Vendor name")
    document_data: dict = Field(..., description="Transaction document data")
    transaction_purpose: str = Field("", max_length=1000, description="Transaction purpose")
    confidence_threshold: int = Field(70, ge=0, le=100, description="Confidence threshold (0-100)")
    auto_research: bool = Field(True, description="Auto-trigger research on low confidence")

    @field_validator('vendor_name')
    @classmethod
    def validate_vendor_name(cls, v):
        if not v or not v.strip():
            raise ValueError("Vendor name cannot be empty or whitespace")
        return v.strip()


@app.post("/categorize-transaction-smart")
async def categorize_transaction_smart(
    body: SmartCategorizationRequest,
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Smart categorization with automatic ambiguity resolution.

    Workflow:
    1. Perform initial categorization
    2. Check confidence score
    3. If confidence < threshold AND auto_research=true: trigger enhanced vendor research
    4. Re-categorize with enhanced context
    5. Flag for manual review if still low confidence
    6. Return comprehensive results with all confidence metrics

    This endpoint provides the most intelligent categorization with built-in ambiguity handling.
    """
    vendor_name = body.vendor_name
    document_data = body.document_data
    transaction_purpose = body.transaction_purpose

    if not vendor_name or not document_data:
        return {"error": "Missing required information"}

    result = {
        "vendor_name": vendor_name,
        "workflow": [],
        "final_categorization": None,
        "confidence_metrics": {},
        "research_performed": False,
        "needs_manual_review": False,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        # Step 1: Initial categorization
        result["workflow"].append({
            "step": 1,
            "action": "initial_categorization",
            "status": "in_progress"
        })

        # Get initial categorization using Gemini
        initial_categorization = await _get_gemini_categorization(
            vendor_name,
            document_data,
            transaction_purpose
        )

        result["initial_categorization"] = initial_categorization
        result["workflow"][-1]["status"] = "completed"

        # Extract confidence score
        confidence = initial_categorization.get("confidence", 0)
        result["confidence_metrics"]["initial_confidence"] = confidence

        # Step 2: Check if enhanced research is needed
        needs_research = (
            confidence < body.confidence_threshold or
            initial_categorization.get("needsResearch", False)
        )

        result["workflow"].append({
            "step": 2,
            "action": "confidence_check",
            "confidence": confidence,
            "threshold": body.confidence_threshold,
            "needs_research": needs_research,
            "status": "completed"
        })

        # Step 3: Enhanced research if needed
        if needs_research and body.auto_research:
            result["workflow"].append({
                "step": 3,
                "action": "enhanced_research",
                "status": "in_progress"
            })

            try:
                # Perform enhanced vendor research
                enhanced_research = await research_vendor_enhanced(
                    EnhancedResearchRequest(
                        vendor_name=vendor_name,
                        transaction_context=document_data,
                        confidence_threshold=body.confidence_threshold
                    ),
                    current_user=current_user,
                    db=db
                )

                result["enhanced_research"] = enhanced_research
                result["research_performed"] = True
                result["workflow"][-1]["status"] = "completed"
                result["confidence_metrics"]["research_confidence"] = enhanced_research.get("overallConfidence", 0)

                # Step 4: Re-categorize with enhanced context
                result["workflow"].append({
                    "step": 4,
                    "action": "re_categorization_with_research",
                    "status": "in_progress"
                })

                # Create enhanced vendor info string
                enhanced_vendor_info = f"""
                Vendor: {vendor_name}

                Research Findings:
                - Official Name: {enhanced_research.get('vendorIdentification', {}).get('primaryName', vendor_name)}
                - Industry: {enhanced_research.get('businessProfile', {}).get('industry', 'Unknown')}
                - Business Type: {enhanced_research.get('businessProfile', {}).get('businessType', 'Unknown')}
                - Summary: {enhanced_research.get('summary', 'No summary available')}
                - Typical Categories: {', '.join(enhanced_research.get('categorizationGuidance', {}).get('typicalCategories', []))}
                - Research Confidence: {enhanced_research.get('overallConfidence', 0)}%
                """

                # Re-categorize with enhanced context
                final_categorization = await _get_gemini_categorization(
                    enhanced_vendor_info,
                    document_data,
                    transaction_purpose
                )

                result["final_categorization"] = final_categorization
                result["workflow"][-1]["status"] = "completed"
                result["confidence_metrics"]["final_confidence"] = final_categorization.get("confidence", 0)

            except Exception as e:
                result["workflow"][-1]["status"] = "error"
                result["workflow"][-1]["error"] = str(e)
                # Fall back to initial categorization
                result["final_categorization"] = initial_categorization
                result["confidence_metrics"]["final_confidence"] = confidence

        else:
            # Use initial categorization as final
            result["final_categorization"] = initial_categorization
            result["confidence_metrics"]["final_confidence"] = confidence

        # Step 5: Determine if manual review is needed
        final_confidence = result["confidence_metrics"]["final_confidence"]

        # Flag for manual review if:
        # - Final confidence is still below threshold, OR
        # - Research recommended manual review, OR
        # - Red flags were detected
        needs_manual_review = (
            final_confidence < request.confidence_threshold or
            (result.get("enhanced_research", {}).get("recommendedAction") == "manual_review") or
            (result.get("enhanced_research", {}).get("redFlags", {}).get("severity") in ["medium", "high"])
        )

        result["needs_manual_review"] = needs_manual_review

        result["workflow"].append({
            "step": 5,
            "action": "review_determination",
            "needs_manual_review": needs_manual_review,
            "final_confidence": final_confidence,
            "status": "completed"
        })

        # Save to database if user is authenticated
        if current_user:
            try:
                # Find the transaction in database
                transaction_id = document_data.get("id", "")
                if transaction_id:
                    db_transaction = crud.get_transaction_by_id(db, str(transaction_id), current_user.id)

                    if db_transaction:
                        # Save categorization with needs_review flag
                        crud.create_categorization(
                            db=db,
                            user_id=current_user.id,
                            transaction_id=db_transaction.id,
                            category=result["final_categorization"].get("category"),
                            subcategory=result["final_categorization"].get("subcategory"),
                            ledger_type=result["final_categorization"].get("ledgerType"),
                            method="smart_ai",
                            confidence_score=final_confidence,
                            explanation=result["final_categorization"].get("explanation"),
                            categorization_data=result,
                            transaction_purpose=transaction_purpose,
                            user_approved=not needs_manual_review  # Auto-approve if high confidence
                        )

                        # Update transaction to flag for review if needed
                        if needs_manual_review:
                            db.query(models.Transaction).filter(
                                models.Transaction.id == db_transaction.id
                            ).update({"notes": f"NEEDS REVIEW - Confidence: {final_confidence}%"})
                            db.commit()

                        # Log activity
                        crud.log_activity(
                            db=db,
                            user_id=current_user.id,
                            action="smart_categorization",
                            entity_type="categorization",
                            details={
                                "vendor_name": vendor_name,
                                "final_confidence": final_confidence,
                                "research_performed": result["research_performed"],
                                "needs_manual_review": needs_manual_review
                            }
                        )
            except Exception as e:
                print(f"Warning: Failed to save smart categorization: {e}")

        return {
            "success": True,
            **result
        }

    except Exception as e:
        print(f"Error in smart categorization: {str(e)}")
        return {
            "success": False,
            "error": f"Error in smart categorization: {str(e)}"
        }


# Define request model for hybrid categorization
class HybridCategorizationRequest(BaseModel):
    vendor_info: str
    document_data: dict
    transaction_purpose: str = ""

@app.post("/categorize-transaction-hybrid")
async def categorize_transaction_hybrid(request: HybridCategorizationRequest):
    """
    Hybrid categorization endpoint that provides BOTH ML prediction and Gemini AI categorization.

    This allows users to compare both approaches and choose the best one, while also
    enabling the system to learn from their choices.
    """
    vendor_info = request.vendor_info
    document_data = request.document_data
    transaction_purpose = request.transaction_purpose

    if not vendor_info or not document_data:
        return {"error": "Missing required information"}

    try:
        # Get ML engine
        engine = get_ml_categorization_engine()

        # Run ML prediction and Gemini categorization in parallel for speed
        ml_prediction_task = engine.predict_category(
            document_data,
            transaction_purpose
        )

        # Gemini categorization (existing logic)
        gemini_categorization_task = _get_gemini_categorization(
            vendor_info,
            document_data,
            transaction_purpose
        )

        # Wait for both to complete
        ml_prediction, gemini_categorization = await asyncio.gather(
            ml_prediction_task,
            gemini_categorization_task
        )

        # Return both predictions
        return {
            "mlPrediction": ml_prediction,
            "geminiCategorization": gemini_categorization,
            "hybridApproach": True,
            "timestamp": asyncio.get_event_loop().time()
        }

    except ValueError as ve:
        # ML engine not initialized (likely missing Pinecone API key)
        print(f"ML engine not available: {str(ve)}")

        # Fallback to Gemini only
        gemini_categorization = await _get_gemini_categorization(
            vendor_info,
            document_data,
            transaction_purpose
        )

        return {
            "mlPrediction": {
                "hasPrediction": False,
                "confidence": 0.0,
                "reason": "ML engine not configured. Please add PINECONE_API_KEY to .env file."
            },
            "geminiCategorization": gemini_categorization,
            "hybridApproach": False,
            "fallbackMode": "gemini_only"
        }

    except Exception as e:
        print(f"Error in hybrid categorization: {str(e)}")
        return {"error": f"Error in hybrid categorization: {str(e)}"}

async def _get_gemini_categorization(vendor_info: str, document_data: dict, transaction_purpose: str) -> dict:
    """
    Helper function to get Gemini AI categorization (extracted from existing endpoint).
    """
    # Create a prompt that includes the categorization options and asks Gemini to categorize the transaction
    prompt = f"""
    Based on the information below, please categorize this transaction according to accounting principles.

    CRITICAL INSTRUCTION: You must categorize from the perspective of the INVOICE RECIPIENT (the customer being billed), NOT from the vendor's perspective.

    For example:
    - If this is an invoice FROM a vendor TO our business, it should typically be categorized as an Expense, Asset, or Liability
    - If this is a receipt we issued TO a customer FROM our business, it would be categorized as Revenue

    This categorization is for the accounting records of the business RECEIVING the invoice/document.

    Return a JSON object with the following structure:
    {{
        "companyName": "The name of the company that issued the invoice (the vendor)",
        "description": "A detailed description of what this business does",
        "category": "The most appropriate accounting category from the list below",
        "subcategory": "The most appropriate subcategory",
        "ledgerType": "The ledger entry type",
        "confidence": "A confidence score from 0-100 indicating how certain you are about this categorization. Consider factors like: clarity of vendor name, specificity of transaction details, alignment with typical business patterns, and ambiguity in the data.",
        "confidenceFactors": {{
            "vendorClarity": "Score 0-100: How clear and unambiguous is the vendor name",
            "dataCompleteness": "Score 0-100: How complete is the transaction data",
            "categoryFit": "Score 0-100: How well does the transaction fit the chosen category",
            "ambiguityLevel": "Score 0-100: Overall ambiguity (100 = very clear, 0 = very ambiguous)"
        }},
        "explanation": "A detailed explanation of why this categorization was chosen, including the factors considered and accounting principles applied",
        "needsResearch": "Boolean - true if additional vendor research would significantly improve categorization confidence"
    }}

    Here are the available categories, subcategories, and ledger types:

    Parent Category | Subcategory | Ledger Entry Type
    ---------------|-------------|------------------
    Revenue | Product Sales | Revenue
    Revenue | Service Revenue | Revenue
    Revenue | Rental Revenue | Revenue
    Revenue | Commission Revenue | Revenue
    Revenue | Subscription Revenue | Revenue
    Revenue | Other Income | Revenue
    Cost of Goods Sold (COGS) | Raw Materials | Expense (COGS)
    Cost of Goods Sold (COGS) | Direct Labor | Expense (COGS)
    Cost of Goods Sold (COGS) | Manufacturing Overhead | Expense (COGS)
    Cost of Goods Sold (COGS) | Freight and Delivery | Expense (COGS)
    Operating Expenses | Salaries and Wages | Expense (Operating)
    Operating Expenses | Rent | Expense (Operating)
    Operating Expenses | Utilities | Expense (Operating)
    Operating Expenses | Office Supplies | Expense (Operating)
    Operating Expenses | Business Software / IT Expenses | Expense (Operating)
    Operating Expenses | HR Expenses | Expense (Operating)
    Operating Expenses | Marketing and Advertising | Expense (Operating)
    Operating Expenses | Travel and Entertainment | Expense (Operating)
    Operating Expenses | Insurance | Expense (Operating)
    Operating Expenses | Repairs and Maintenance | Expense (Operating)
    Operating Expenses | Depreciation | Expense (Operating)
    Administrative Expenses | Professional Fees | Expense (Administrative)
    Administrative Expenses | Office Expenses | Expense (Administrative)
    Administrative Expenses | Postage and Shipping | Expense (Administrative)
    Administrative Expenses | Communication Expense | Expense (Administrative)
    Administrative Expenses | Bank Fees and Charges | Expense (Administrative)
    Financial Expenses | Interest Expense | Expense (Financial)
    Financial Expenses | Loan Fees | Expense (Financial)
    Financial Expenses | Credit Card Fees | Expense (Financial)
    Other Expenses | Miscellaneous | Expense (Other)
    Other Expenses | Donations/Charitable Contributions | Expense (Other)
    Other Expenses | Loss on Disposal of Assets | Expense (Other)
    Assets – Current | Cash and Cash Equivalents | Asset (Current)
    Assets – Current | Accounts Receivable | Asset (Current)
    Assets – Current | Inventory | Asset (Current)
    Assets – Current | Prepaid Expenses | Asset (Current)
    Assets – Current | Short-term Investments | Asset (Current)
    Assets – Fixed / Long-term | Property, Plant, and Equipment | Asset (Fixed)
    Assets – Fixed / Long-term | Furniture and Fixtures | Asset (Fixed)
    Assets – Fixed / Long-term | Vehicles | Asset (Fixed)
    Assets – Fixed / Long-term | Machinery and Equipment | Asset (Fixed)
    Assets – Fixed / Long-term | Computer Equipment | Asset (Fixed)
    Assets – Intangible | Patents | Asset (Intangible)
    Assets – Intangible | Trademarks | Asset (Intangible)
    Assets – Intangible | Copyrights | Asset (Intangible)
    Assets – Intangible | Goodwill | Asset (Intangible)
    Assets – Intangible | Capitalized Software | Asset (Intangible)
    Liabilities – Current | Accounts Payable | Liability (Current)
    Liabilities – Current | Short-term Loans | Liability (Current)
    Liabilities – Current | Accrued Liabilities | Liability (Current)
    Liabilities – Current | Current Portion of Long-term Debt | Liability (Current)
    Liabilities – Long-term | Long-term Loans | Liability (Long-term)
    Liabilities – Long-term | Bonds Payable | Liability (Long-term)
    Liabilities – Long-term | Deferred Tax Liabilities | Liability (Long-term)
    Equity | Common Stock | Equity
    Equity | Retained Earnings | Equity
    Equity | Additional Paid-in Capital | Equity
    Equity | Dividends/Distributions | Equity
    Adjusting / Journal Entries | Accruals/Deferrals/Depreciation Adjustments | Adjustment

    Vendor Information (the seller/company that sent the invoice):
    {vendor_info}

    Document Data:
    {json.dumps(document_data, indent=2)}

    Transaction Purpose (what the invoice is for):
    {transaction_purpose}

    REMEMBER: Categorize from the perspective of the business RECEIVING this invoice - the customer being billed, NOT from the perspective of the vendor who issued it.

    In the explanation field, be thorough about why this specific category, subcategory, and ledger type was chosen.
    Consider the nature of the transaction, the items or services involved, accounting best practices, and how this
    classification aligns with standard chart of accounts structures.
    """

    # Send the request to Gemini API
    response = await asyncio.to_thread(
        client.models.generate_content,
        model="gemini-2.0-flash",
        contents=prompt,
        config={
            "max_output_tokens": 4000,
            "response_mime_type": "application/json"
        }
    )

    # Parse and return the response
    try:
        categorization_json = json.loads(response.text)
        return categorization_json
    except json.JSONDecodeError:
        return {"error": "Failed to parse Gemini response", "rawText": response.text}

# Define request model for storing categorization
class StoreCategorizationRequest(BaseModel):
    transaction_data: dict
    categorization: dict
    transaction_purpose: str = ""
    selected_method: str = "gemini"  # "ml", "gemini", or "manual"
    user_feedback: str = ""  # Optional feedback

@app.post("/store-categorization")
async def store_categorization(
    request: StoreCategorizationRequest,
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Store a categorization decision for machine learning.

    This endpoint is called after the user selects their preferred categorization
    (either ML, Gemini, or manually adjusted). The system learns from this decision.
    Saves to both Pinecone (for ML) and PostgreSQL (for history and audit).
    """
    try:
        # Get ML engine
        engine = get_ml_categorization_engine()

        # Prepare user feedback string
        feedback = f"{request.selected_method}"
        if request.user_feedback:
            feedback += f" | {request.user_feedback}"

        # Store in vector database (Pinecone)
        transaction_id = await engine.store_transaction(
            transaction_data=request.transaction_data,
            categorization=request.categorization,
            transaction_purpose=request.transaction_purpose,
            user_feedback=feedback
        )

        # Also save to PostgreSQL database if user is authenticated
        if current_user:
            try:
                # Find the transaction in our database (if it exists)
                db_transaction = crud.get_transaction_by_id(
                    db, str(request.transaction_data.get("id", "")), current_user.id
                )

                if db_transaction:
                    # Save categorization
                    crud.create_categorization(
                        db=db,
                        user_id=current_user.id,
                        transaction_id=db_transaction.id,
                        category=request.categorization.get("category"),
                        subcategory=request.categorization.get("subcategory"),
                        ledger_type=request.categorization.get("ledgerType"),
                        method=request.selected_method,
                        confidence_score=request.categorization.get("confidence", 0),
                        explanation=request.categorization.get("explanation"),
                        categorization_data=request.categorization,
                        transaction_purpose=request.transaction_purpose,
                        user_approved=True  # Since user selected it
                    )

                    # Log activity
                    crud.log_activity(
                        db=db,
                        user_id=current_user.id,
                        action="categorization_saved",
                        entity_type="categorization",
                        details={
                            "method": request.selected_method,
                            "category": request.categorization.get("category")
                        }
                    )
            except Exception as e:
                print(f"Warning: Failed to save categorization to database: {e}")

        return {
            "success": True,
            "transactionId": transaction_id,
            "message": "Categorization stored successfully for future learning"
        }

    except ValueError as ve:
        return {
            "success": False,
            "error": "ML engine not configured",
            "detail": str(ve)
        }
    except Exception as e:
        print(f"Error storing categorization: {str(e)}")
        return {
            "success": False,
            "error": f"Error storing categorization: {str(e)}"
        }

@app.get("/ml-stats")
async def get_ml_stats():
    """
    Get statistics about the ML vector database.

    Returns information about how many transactions are stored and ready for learning.
    """
    try:
        # Get ML engine
        engine = get_ml_categorization_engine()

        # Get stats
        stats = await engine.get_database_stats()

        return {
            "success": True,
            "stats": stats
        }

    except ValueError as ve:
        return {
            "success": False,
            "error": "ML engine not configured",
            "detail": str(ve),
            "stats": {
                "totalTransactions": 0,
                "status": "not_configured"
            }
        }
    except Exception as e:
        print(f"Error getting ML stats: {str(e)}")
        return {
            "success": False,
            "error": f"Error getting ML stats: {str(e)}"
        }

# Define request model for submitting corrections
class SubmitCorrectionRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1, max_length=100, description="Transaction ID")
    original_categorization: dict = Field(..., description="Original categorization data")
    corrected_categorization: dict = Field(..., description="Corrected categorization data")
    transaction_data: dict = Field(..., description="Transaction data")
    transaction_purpose: str = Field("", max_length=1000, description="Transaction purpose")
    correction_reason: str = Field("", max_length=2000, description="Reason for correction")

    @field_validator('transaction_id')
    @classmethod
    def validate_transaction_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Transaction ID cannot be empty")
        return v.strip()

@app.post("/submit-correction")
async def submit_correction(
    request: SubmitCorrectionRequest,
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Submit a user correction to improve the ML model.

    This endpoint allows users to:
    1. Reject an incorrect ML prediction
    2. Manually correct a categorization
    3. Provide feedback on why the correction was needed

    The correction is stored with higher learning weight for future predictions.
    Saves to both Pinecone (for ML) and PostgreSQL (for history and analytics).
    """
    try:
        # Get ML engine
        engine = get_ml_categorization_engine()

        # Submit the correction to Pinecone
        result = await engine.submit_correction(
            transaction_id=request.transaction_id,
            original_categorization=request.original_categorization,
            corrected_categorization=request.corrected_categorization,
            transaction_data=request.transaction_data,
            transaction_purpose=request.transaction_purpose,
            correction_reason=request.correction_reason
        )

        # Also save to PostgreSQL database if user is authenticated
        if current_user:
            try:
                # Find the transaction in our database
                db_transaction = crud.get_transaction_by_id(
                    db, request.transaction_id, current_user.id
                )

                if db_transaction:
                    # Save user correction
                    crud.create_user_correction(
                        db=db,
                        user_id=current_user.id,
                        transaction_id=db_transaction.id,
                        original_category=request.original_categorization.get("category"),
                        original_subcategory=request.original_categorization.get("subcategory"),
                        original_ledger_type=request.original_categorization.get("ledgerType"),
                        original_method=request.original_categorization.get("method", "gemini"),
                        corrected_category=request.corrected_categorization.get("category"),
                        corrected_subcategory=request.corrected_categorization.get("subcategory"),
                        corrected_ledger_type=request.corrected_categorization.get("ledgerType"),
                        correction_reason=request.correction_reason,
                        correction_data={"original": request.original_categorization, "corrected": request.corrected_categorization}
                    )

                    # Log activity
                    crud.log_activity(
                        db=db,
                        user_id=current_user.id,
                        action="categorization_corrected",
                        entity_type="user_correction",
                        details={"transaction_id": request.transaction_id, "reason": request.correction_reason}
                    )
            except Exception as e:
                print(f"Warning: Failed to save correction to database: {e}")

        return result

    except ValueError as ve:
        return {
            "success": False,
            "error": "ML engine not configured",
            "detail": str(ve)
        }
    except Exception as e:
        print(f"Error submitting correction: {str(e)}")
        return {
            "success": False,
            "error": f"Error submitting correction: {str(e)}"
        }

@app.get("/correction-stats")
async def get_correction_stats():
    """
    Get statistics about corrections and learning progress.

    Returns insights about how many corrections have been made,
    learning status, and recommendations for improvement.
    """
    try:
        # Get ML engine
        engine = get_ml_categorization_engine()

        # Get correction stats
        stats = await engine.get_correction_stats()

        return {
            "success": True,
            "stats": stats
        }

    except ValueError as ve:
        return {
            "success": False,
            "error": "ML engine not configured",
            "detail": str(ve)
        }
    except Exception as e:
        print(f"Error getting correction stats: {str(e)}")
        return {
            "success": False,
            "error": f"Error getting correction stats: {str(e)}"
        }

@app.get("/categories")
async def get_categories():
    """
    Get all available accounting categories for manual selection.

    Returns the complete list of categories, subcategories, and ledger types
    that can be used for categorization.
    """
    try:
        return {
            "success": True,
            "categories": get_all_categories(),
            "grouped": get_categories_by_parent()
        }
    except Exception as e:
        print(f"Error getting categories: {str(e)}")
        return {
            "success": False,
            "error": f"Error getting categories: {str(e)}"
        }

@app.get("/categories/{category}/subcategories")
async def get_subcategories(category: str):
    """
    Get subcategories for a specific parent category.

    Useful for cascading dropdowns where user first selects parent category,
    then subcategory.
    """
    try:
        subcategories = get_subcategories_for_category(category)
        return {
            "success": True,
            "category": category,
            "subcategories": subcategories
        }
    except Exception as e:
        print(f"Error getting subcategories: {str(e)}")
        return {
            "success": False,
            "error": f"Error getting subcategories: {str(e)}"
        }

# Bank Statement Reconciliation Endpoints

@app.post("/parse-bank-statement")
async def parse_bank_statement(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Parse a bank statement (CSV or PDF) and extract transactions.

    Returns list of transactions with date, description, and amount.
    If user is authenticated, saves to database for reconciliation history.
    """
    # Validate file upload
    await validate_file_upload(file)

    try:
        file_content = await file.read()
        file_type = file.content_type

        # Initialize parser
        parser = BankStatementParser()

        # Parse the statement
        transactions = parser.parse(file_content, file_type)

        # Save to database if user is authenticated
        db_statement = None
        if current_user:
            try:
                # Create bank statement record
                db_statement = crud.create_bank_statement(
                    db=db,
                    user_id=current_user.id,
                    file_name=file.filename,
                    file_type=file_type,
                    transactions_data=transactions,
                    transaction_count=len(transactions)
                )

                # Save individual transactions
                for transaction in transactions:
                    crud.create_bank_transaction(
                        db=db,
                        user_id=current_user.id,
                        bank_statement_id=db_statement.id,
                        transaction_date=transaction.get("date"),
                        description=transaction.get("description"),
                        amount=transaction.get("amount"),
                        transaction_type=transaction.get("type")
                    )

                # Log activity
                crud.log_activity(
                    db=db,
                    user_id=current_user.id,
                    action="bank_statement_uploaded",
                    entity_type="bank_statement",
                    entity_id=db_statement.id,
                    details={"file_name": file.filename, "transaction_count": len(transactions)}
                )
            except Exception as e:
                print(f"Warning: Failed to save bank statement to database: {e}")

        return {
            "success": True,
            "transactions": transactions,
            "count": len(transactions),
            "file_name": file.filename,
            "file_type": file_type,
            "statement_id": db_statement.id if db_statement else None
        }

    except Exception as e:
        print(f"Error parsing bank statement: {str(e)}")
        return {
            "success": False,
            "error": f"Error parsing bank statement: {str(e)}"
        }

# Define request model for reconciliation
class ReconciliationRequest(BaseModel):
    documents: list  # List of processed documents
    bank_transactions: list  # List of bank transactions
    auto_match_threshold: int = 90  # Threshold for automatic matching

@app.post("/reconcile")
async def reconcile_documents(
    request: ReconciliationRequest,
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Reconcile documents against bank statement transactions.

    Uses intelligent matching based on:
    - Vendor name (fuzzy matching)
    - Amount (exact or within tolerance)
    - Date (exact or within range)

    Returns matched, unmatched, and suggested matches.
    If user is authenticated, saves matches to database for history.
    """
    try:
        # Initialize reconciliation engine
        engine = ReconciliationEngine(
            name_threshold=80,  # Minimum 80% name match
            amount_tolerance=0.01,  # Within $0.01
            date_range_days=3  # Within 3 days
        )

        # Perform reconciliation
        results = engine.reconcile(
            documents=request.documents,
            bank_transactions=request.bank_transactions,
            auto_match_threshold=request.auto_match_threshold
        )

        # Save matches to database if user is authenticated
        if current_user:
            try:
                for match in results.get("matched", []):
                    # Find transaction and bank transaction in database
                    db_transaction = crud.get_transaction_by_id(
                        db, match.get("document", {}).get("id", ""), current_user.id
                    )
                    db_bank_transaction = db.query(models.BankTransaction).filter(
                        models.BankTransaction.user_id == current_user.id,
                        models.BankTransaction.id == match.get("bank_transaction", {}).get("id")
                    ).first()

                    if db_transaction and db_bank_transaction:
                        # Create reconciliation match
                        crud.create_reconciliation_match(
                            db=db,
                            user_id=current_user.id,
                            transaction_id=db_transaction.id,
                            bank_transaction_id=db_bank_transaction.id,
                            match_type="auto" if match.get("confidence", 0) >= request.auto_match_threshold else "suggested",
                            match_confidence=match.get("confidence"),
                            name_match_score=match.get("name_score"),
                            amount_match_score=match.get("amount_score"),
                            date_match_score=match.get("date_score"),
                            match_reason=match.get("reason"),
                            match_data=match
                        )

                # Log activity
                crud.log_activity(
                    db=db,
                    user_id=current_user.id,
                    action="reconciliation_performed",
                    entity_type="reconciliation",
                    details={
                        "matched_count": len(results.get("matched", [])),
                        "unmatched_count": len(results.get("unmatched", []))
                    }
                )
            except Exception as e:
                print(f"Warning: Failed to save reconciliation results to database: {e}")

        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        print(f"Error during reconciliation: {str(e)}")
        return {
            "success": False,
            "error": f"Error during reconciliation: {str(e)}"
        }

# Define request model for manual matching
class ManualMatchRequest(BaseModel):
    document: dict
    transaction: dict

@app.post("/manual-match")
async def manual_match(request: ManualMatchRequest):
    """
    Manually match a document with a transaction.

    User confirms a suggested match or creates a new match.
    Returns detailed match information.
    """
    try:
        # Initialize reconciliation engine
        engine = ReconciliationEngine()

        # Create manual match
        match_result = engine.manual_match(
            document=request.document,
            transaction=request.transaction
        )

        return {
            "success": True,
            "match": match_result
        }

    except Exception as e:
        print(f"Error creating manual match: {str(e)}")
        return {
            "success": False,
            "error": f"Error creating manual match: {str(e)}"
        }

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


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


# ============================================================================
# DOCUMENT & TRANSACTION HISTORY ENDPOINTS
# ============================================================================

class DocumentResponse(BaseModel):
    id: int
    document_id: str
    file_name: str
    status: str
    progress: int
    uploaded_at: datetime
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


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


@app.get("/documents", response_model=List[DocumentResponse], tags=["Documents"])
async def get_documents(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Get all documents for current user (or all if not authenticated)

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by status (pending, processing, completed, error)
    """
    if current_user:
        documents = crud.get_user_documents(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status=status
        )
    else:
        # For non-authenticated users, return empty list or demo data
        documents = []

    return documents


@app.get("/documents/{document_id}", response_model=DocumentResponse, tags=["Documents"])
async def get_document(
    document_id: str,
    current_user: models.User = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Get a specific document by ID"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    document = crud.get_document_by_id(db, document_id, current_user.id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return document


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
# MANUAL REVIEW QUEUE ENDPOINTS
# ============================================================================

class LowConfidenceTransaction(BaseModel):
    """Extended transaction response with confidence and review info"""
    id: int
    transaction_id: str
    vendor_name: Optional[str]
    amount: float
    transaction_date: Optional[date]
    description: Optional[str]
    created_at: datetime

    # Categorization info
    category: Optional[str]
    subcategory: Optional[str]
    confidence_score: Optional[float]
    needs_review_reason: Optional[str]

    # Research info
    has_research: bool
    research_confidence: Optional[float]

    class Config:
        from_attributes = True


@app.get("/review-queue", response_model=List[dict], tags=["Review"])
async def get_review_queue(
    skip: int = 0,
    limit: int = 50,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = 70.0,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get transactions flagged for manual review.

    Returns transactions where:
    - Confidence score is below threshold (default < 70%)
    - Notes contain "NEEDS REVIEW"
    - Categorization is not user-approved

    Sorted by confidence score (lowest first).
    """
    # Query transactions with low confidence categorizations
    query = db.query(
        models.Transaction,
        models.Categorization
    ).join(
        models.Categorization,
        models.Transaction.id == models.Categorization.transaction_id,
        isouter=True
    ).filter(
        models.Transaction.user_id == current_user.id
    ).filter(
        or_(
            # Low confidence score
            models.Categorization.confidence_score < max_confidence if max_confidence else True,
            # Not user approved
            models.Categorization.user_approved == False,
            # Flagged in notes
            models.Transaction.notes.like("%NEEDS REVIEW%")
        )
    )

    if min_confidence is not None:
        query = query.filter(models.Categorization.confidence_score >= min_confidence)

    # Order by confidence (lowest first)
    query = query.order_by(
        models.Categorization.confidence_score.asc().nullsfirst()
    )

    results = query.offset(skip).limit(limit).all()

    # Format results
    review_queue = []
    for transaction, categorization in results:
        item = {
            "id": transaction.id,
            "transaction_id": transaction.transaction_id,
            "vendor_name": transaction.vendor_name,
            "amount": float(transaction.amount) if transaction.amount else 0,
            "transaction_date": transaction.transaction_date,
            "description": transaction.description,
            "created_at": transaction.created_at,
            "category": categorization.category if categorization else None,
            "subcategory": categorization.subcategory if categorization else None,
            "confidence_score": float(categorization.confidence_score) if categorization and categorization.confidence_score else 0,
            "needs_review_reason": transaction.notes if "NEEDS REVIEW" in (transaction.notes or "") else "Low confidence score",
            "categorization_method": categorization.method if categorization else None,
            "user_approved": categorization.user_approved if categorization else False
        }
        review_queue.append(item)

    return review_queue


@app.get("/review-queue/stats", tags=["Review"])
async def get_review_queue_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about the review queue.

    Returns counts by confidence range and urgency level.
    """
    # Total transactions needing review
    total_needs_review = db.query(models.Transaction).join(
        models.Categorization
    ).filter(
        models.Transaction.user_id == current_user.id
    ).filter(
        or_(
            models.Categorization.confidence_score < 70,
            models.Categorization.user_approved == False,
            models.Transaction.notes.like("%NEEDS REVIEW%")
        )
    ).count()

    # Count by confidence ranges
    critical = db.query(models.Transaction).join(
        models.Categorization
    ).filter(
        models.Transaction.user_id == current_user.id,
        models.Categorization.confidence_score < 50
    ).count()

    low = db.query(models.Transaction).join(
        models.Categorization
    ).filter(
        models.Transaction.user_id == current_user.id,
        models.Categorization.confidence_score >= 50,
        models.Categorization.confidence_score < 70
    ).count()

    # Recently added (last 7 days)
    from datetime import timedelta
    recent_date = datetime.utcnow() - timedelta(days=7)
    recent = db.query(models.Transaction).join(
        models.Categorization
    ).filter(
        models.Transaction.user_id == current_user.id,
        models.Transaction.created_at >= recent_date,
        models.Categorization.confidence_score < 70
    ).count()

    return {
        "total_needs_review": total_needs_review,
        "by_urgency": {
            "critical": critical,  # < 50%
            "low": low,  # 50-70%
        },
        "recent_additions": recent,
        "average_queue_time_days": 0,  # Could calculate based on created_at
        "oldest_unreviewed": None  # Could query for oldest transaction
    }


class ApproveCategorizationRequest(BaseModel):
    transaction_id: str
    approved: bool
    corrected_category: Optional[str] = None
    corrected_subcategory: Optional[str] = None
    corrected_ledger_type: Optional[str] = None
    review_notes: Optional[str] = None


@app.post("/review-queue/approve", tags=["Review"])
async def approve_categorization(
    request: ApproveCategorizationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve or correct a categorization from the review queue.

    If approved: Mark categorization as user_approved
    If corrected: Create user correction and update categorization
    """
    try:
        # Find transaction
        transaction = crud.get_transaction_by_id(db, request.transaction_id, current_user.id)

        if not transaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found"
            )

        # Get current categorization
        categorization = db.query(models.Categorization).filter(
            models.Categorization.transaction_id == transaction.id,
            models.Categorization.user_id == current_user.id
        ).order_by(models.Categorization.created_at.desc()).first()

        if not categorization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Categorization not found"
            )

        if request.approved:
            # Simple approval
            categorization.user_approved = True
            categorization.user_modified = False

            # Clear review flag from notes
            if transaction.notes and "NEEDS REVIEW" in transaction.notes:
                transaction.notes = transaction.notes.replace("NEEDS REVIEW - ", "").strip()

            db.commit()

            # Log activity
            crud.log_activity(
                db=db,
                user_id=current_user.id,
                action="categorization_approved",
                entity_type="categorization",
                entity_id=categorization.id,
                details={"transaction_id": request.transaction_id}
            )

            return {
                "success": True,
                "message": "Categorization approved",
                "action": "approved"
            }

        else:
            # User is correcting the categorization
            if not (request.corrected_category and request.corrected_subcategory and request.corrected_ledger_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Corrected category, subcategory, and ledger type required"
                )

            # Create user correction record
            crud.create_user_correction(
                db=db,
                user_id=current_user.id,
                transaction_id=transaction.id,
                original_category=categorization.category,
                original_subcategory=categorization.subcategory,
                original_ledger_type=categorization.ledger_type,
                original_method=categorization.method,
                corrected_category=request.corrected_category,
                corrected_subcategory=request.corrected_subcategory,
                corrected_ledger_type=request.corrected_ledger_type,
                correction_reason=request.review_notes or "Manual review correction",
                correction_data={
                    "original_confidence": float(categorization.confidence_score) if categorization.confidence_score else 0
                }
            )

            # Update categorization
            categorization.category = request.corrected_category
            categorization.subcategory = request.corrected_subcategory
            categorization.ledger_type = request.corrected_ledger_type
            categorization.user_approved = True
            categorization.user_modified = True
            categorization.confidence_score = 100  # User correction is 100% confident

            # Clear review flag
            if transaction.notes and "NEEDS REVIEW" in transaction.notes:
                transaction.notes = f"Manually corrected: {request.review_notes or 'User correction'}"

            db.commit()

            # Log activity
            crud.log_activity(
                db=db,
                user_id=current_user.id,
                action="categorization_corrected",
                entity_type="categorization",
                entity_id=categorization.id,
                details={
                    "transaction_id": request.transaction_id,
                    "corrected_to": request.corrected_category
                }
            )

            return {
                "success": True,
                "message": "Categorization corrected",
                "action": "corrected"
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error approving categorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing approval: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)