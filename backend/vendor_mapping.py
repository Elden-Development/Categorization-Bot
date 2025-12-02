"""
Vendor Mapping Module for Categorization-Bot

Provides deterministic categorization for well-known vendors before falling back to AI.
This improves accuracy and speed for common merchants.
"""

import re
from typing import Optional, Dict, Tuple
from dataclasses import dataclass


@dataclass
class VendorCategory:
    """Represents a vendor's category mapping"""
    category: str
    subcategory: str
    ledger_type: str
    confidence: float = 98.0  # High confidence for known vendors
    explanation: str = ""


# Known vendor mappings organized by category
# Format: pattern -> VendorCategory
# Patterns are matched against normalized (lowercase) vendor descriptions

VENDOR_MAPPINGS: Dict[str, VendorCategory] = {
    # ============================================================================
    # OFFICE SUPPLIES & RETAIL
    # ============================================================================
    "amazon": VendorCategory(
        category="Operating Expenses",
        subcategory="Office Supplies",
        ledger_type="Expense (Operating)",
        explanation="Amazon purchase - typically office supplies or business materials"
    ),
    "office depot": VendorCategory(
        category="Operating Expenses",
        subcategory="Office Supplies",
        ledger_type="Expense (Operating)",
        explanation="Office supply retailer"
    ),
    "officemax": VendorCategory(
        category="Operating Expenses",
        subcategory="Office Supplies",
        ledger_type="Expense (Operating)",
        explanation="Office supply retailer"
    ),
    "staples": VendorCategory(
        category="Operating Expenses",
        subcategory="Office Supplies",
        ledger_type="Expense (Operating)",
        explanation="Office supply retailer"
    ),
    "best buy": VendorCategory(
        category="Assets – Fixed / Long-term",
        subcategory="Computer Equipment",
        ledger_type="Asset (Fixed)",
        explanation="Electronics retailer - typically computer/IT equipment"
    ),
    "apple store": VendorCategory(
        category="Assets – Fixed / Long-term",
        subcategory="Computer Equipment",
        ledger_type="Asset (Fixed)",
        explanation="Apple retail - typically computer/IT equipment"
    ),
    "walmart": VendorCategory(
        category="Operating Expenses",
        subcategory="Office Supplies",
        ledger_type="Expense (Operating)",
        explanation="General retail purchase - categorized as office supplies"
    ),
    "target": VendorCategory(
        category="Operating Expenses",
        subcategory="Office Supplies",
        ledger_type="Expense (Operating)",
        explanation="General retail purchase - categorized as office supplies"
    ),
    "costco": VendorCategory(
        category="Operating Expenses",
        subcategory="Office Supplies",
        ledger_type="Expense (Operating)",
        explanation="Wholesale retailer - typically office supplies or inventory"
    ),

    # ============================================================================
    # FOOD & ENTERTAINMENT (Travel & Entertainment)
    # ============================================================================
    "starbucks": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Coffee/food purchase - meals and entertainment"
    ),
    "dunkin": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Coffee/food purchase - meals and entertainment"
    ),
    "mcdonald": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Restaurant - meals and entertainment"
    ),
    "burger king": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Restaurant - meals and entertainment"
    ),
    "wendy": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Restaurant - meals and entertainment"
    ),
    "chipotle": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Restaurant - meals and entertainment"
    ),
    "subway": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Restaurant - meals and entertainment"
    ),
    "panera": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Restaurant - meals and entertainment"
    ),
    "grubhub": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Food delivery service - meals and entertainment"
    ),
    "doordash": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Food delivery service - meals and entertainment"
    ),
    "uber eats": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Food delivery service - meals and entertainment"
    ),
    "postmates": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Food delivery service - meals and entertainment"
    ),

    # ============================================================================
    # TRANSPORTATION & TRAVEL
    # ============================================================================
    "uber": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Rideshare/transportation expense"
    ),
    "lyft": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Rideshare/transportation expense"
    ),
    "delta air": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Airline - business travel expense"
    ),
    "united air": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Airline - business travel expense"
    ),
    "american air": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Airline - business travel expense"
    ),
    "southwest": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Airline - business travel expense"
    ),
    "jetblue": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Airline - business travel expense"
    ),
    "marriott": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Hotel - business travel expense"
    ),
    "hilton": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Hotel - business travel expense"
    ),
    "hyatt": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Hotel - business travel expense"
    ),
    "airbnb": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Lodging - business travel expense"
    ),
    "hertz": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Car rental - business travel expense"
    ),
    "enterprise": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Car rental - business travel expense"
    ),
    "avis": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Car rental - business travel expense"
    ),

    # ============================================================================
    # UTILITIES
    # ============================================================================
    "electric": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Electric utility payment"
    ),
    "power company": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Electric utility payment"
    ),
    "gas company": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Gas utility payment"
    ),
    "water company": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Water utility payment"
    ),
    "comcast": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Internet/cable service"
    ),
    "xfinity": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Internet/cable service"
    ),
    "spectrum": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Internet/cable service"
    ),
    "at&t": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Telecommunications service"
    ),
    "verizon": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Telecommunications service"
    ),
    "t-mobile": VendorCategory(
        category="Operating Expenses",
        subcategory="Utilities",
        ledger_type="Expense (Operating)",
        explanation="Telecommunications service"
    ),

    # ============================================================================
    # SOFTWARE & IT SERVICES
    # ============================================================================
    "google": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Google services (Workspace, Cloud, Ads, etc.)"
    ),
    "microsoft": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Microsoft services (Office 365, Azure, etc.)"
    ),
    "adobe": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Adobe software subscription"
    ),
    "salesforce": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="CRM software subscription"
    ),
    "slack": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Team communication software"
    ),
    "zoom": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Video conferencing software"
    ),
    "dropbox": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Cloud storage service"
    ),
    "github": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Development platform subscription"
    ),
    "aws": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Amazon Web Services - cloud infrastructure"
    ),
    "amazon web services": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Amazon Web Services - cloud infrastructure"
    ),
    "digitalocean": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Cloud hosting service"
    ),
    "godaddy": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Domain/hosting service"
    ),
    "squarespace": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Website hosting/builder service"
    ),
    "shopify": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="E-commerce platform subscription"
    ),
    "quickbooks": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Accounting software subscription"
    ),
    "intuit": VendorCategory(
        category="Operating Expenses",
        subcategory="Business Software / IT Expenses",
        ledger_type="Expense (Operating)",
        explanation="Intuit software (QuickBooks, TurboTax, etc.)"
    ),
    "mailchimp": VendorCategory(
        category="Operating Expenses",
        subcategory="Marketing and Advertising",
        ledger_type="Expense (Operating)",
        explanation="Email marketing service"
    ),
    "hubspot": VendorCategory(
        category="Operating Expenses",
        subcategory="Marketing and Advertising",
        ledger_type="Expense (Operating)",
        explanation="Marketing/CRM platform"
    ),

    # ============================================================================
    # PROFESSIONAL SERVICES
    # ============================================================================
    "fedex": VendorCategory(
        category="Administrative Expenses",
        subcategory="Postage and Shipping",
        ledger_type="Expense (Administrative)",
        explanation="Shipping and delivery service"
    ),
    "ups": VendorCategory(
        category="Administrative Expenses",
        subcategory="Postage and Shipping",
        ledger_type="Expense (Administrative)",
        explanation="Shipping and delivery service"
    ),
    "usps": VendorCategory(
        category="Administrative Expenses",
        subcategory="Postage and Shipping",
        ledger_type="Expense (Administrative)",
        explanation="Postal service"
    ),
    "stamps.com": VendorCategory(
        category="Administrative Expenses",
        subcategory="Postage and Shipping",
        ledger_type="Expense (Administrative)",
        explanation="Postage service"
    ),

    # ============================================================================
    # INSURANCE
    # ============================================================================
    "insurance": VendorCategory(
        category="Operating Expenses",
        subcategory="Insurance",
        ledger_type="Expense (Operating)",
        explanation="Insurance premium payment"
    ),
    "state farm": VendorCategory(
        category="Operating Expenses",
        subcategory="Insurance",
        ledger_type="Expense (Operating)",
        explanation="Insurance premium payment"
    ),
    "geico": VendorCategory(
        category="Operating Expenses",
        subcategory="Insurance",
        ledger_type="Expense (Operating)",
        explanation="Insurance premium payment"
    ),
    "progressive": VendorCategory(
        category="Operating Expenses",
        subcategory="Insurance",
        ledger_type="Expense (Operating)",
        explanation="Insurance premium payment"
    ),
    "allstate": VendorCategory(
        category="Operating Expenses",
        subcategory="Insurance",
        ledger_type="Expense (Operating)",
        explanation="Insurance premium payment"
    ),

    # ============================================================================
    # BANKING & FINANCIAL
    # ============================================================================
    "bank fee": VendorCategory(
        category="Administrative Expenses",
        subcategory="Bank Fees and Charges",
        ledger_type="Expense (Administrative)",
        explanation="Bank service fee"
    ),
    "service charge": VendorCategory(
        category="Administrative Expenses",
        subcategory="Bank Fees and Charges",
        ledger_type="Expense (Administrative)",
        explanation="Bank service charge"
    ),
    "overdraft": VendorCategory(
        category="Administrative Expenses",
        subcategory="Bank Fees and Charges",
        ledger_type="Expense (Administrative)",
        explanation="Overdraft fee"
    ),
    "wire transfer": VendorCategory(
        category="Administrative Expenses",
        subcategory="Bank Fees and Charges",
        ledger_type="Expense (Administrative)",
        explanation="Wire transfer fee"
    ),
    "paypal": VendorCategory(
        category="Financial Expenses",
        subcategory="Credit Card Fees",
        ledger_type="Expense (Financial)",
        explanation="Payment processing fee"
    ),
    "stripe": VendorCategory(
        category="Financial Expenses",
        subcategory="Credit Card Fees",
        ledger_type="Expense (Financial)",
        explanation="Payment processing fee"
    ),
    "square": VendorCategory(
        category="Financial Expenses",
        subcategory="Credit Card Fees",
        ledger_type="Expense (Financial)",
        explanation="Payment processing fee"
    ),

    # ============================================================================
    # PAYROLL & HR
    # ============================================================================
    "payroll": VendorCategory(
        category="Operating Expenses",
        subcategory="Salaries and Wages",
        ledger_type="Expense (Operating)",
        explanation="Payroll/salary payment"
    ),
    "adp": VendorCategory(
        category="Operating Expenses",
        subcategory="Salaries and Wages",
        ledger_type="Expense (Operating)",
        explanation="Payroll service"
    ),
    "gusto": VendorCategory(
        category="Operating Expenses",
        subcategory="Salaries and Wages",
        ledger_type="Expense (Operating)",
        explanation="Payroll service"
    ),
    "paychex": VendorCategory(
        category="Operating Expenses",
        subcategory="Salaries and Wages",
        ledger_type="Expense (Operating)",
        explanation="Payroll service"
    ),

    # ============================================================================
    # MARKETING & ADVERTISING
    # ============================================================================
    "facebook": VendorCategory(
        category="Operating Expenses",
        subcategory="Marketing and Advertising",
        ledger_type="Expense (Operating)",
        explanation="Social media advertising"
    ),
    "meta": VendorCategory(
        category="Operating Expenses",
        subcategory="Marketing and Advertising",
        ledger_type="Expense (Operating)",
        explanation="Meta advertising (Facebook, Instagram)"
    ),
    "linkedin": VendorCategory(
        category="Operating Expenses",
        subcategory="Marketing and Advertising",
        ledger_type="Expense (Operating)",
        explanation="LinkedIn advertising or premium"
    ),
    "twitter": VendorCategory(
        category="Operating Expenses",
        subcategory="Marketing and Advertising",
        ledger_type="Expense (Operating)",
        explanation="Twitter/X advertising"
    ),
    "yelp": VendorCategory(
        category="Operating Expenses",
        subcategory="Marketing and Advertising",
        ledger_type="Expense (Operating)",
        explanation="Yelp advertising"
    ),

    # ============================================================================
    # GAS STATIONS (Vehicle Expenses)
    # ============================================================================
    "shell": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Fuel expense"
    ),
    "exxon": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Fuel expense"
    ),
    "mobil": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Fuel expense"
    ),
    "chevron": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Fuel expense"
    ),
    "bp": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Fuel expense"
    ),
    "gas station": VendorCategory(
        category="Operating Expenses",
        subcategory="Travel and Entertainment",
        ledger_type="Expense (Operating)",
        explanation="Fuel expense"
    ),
}


def normalize_vendor_name(description: str) -> str:
    """
    Normalize a vendor description for matching.

    - Converts to lowercase
    - Removes common prefixes (SQ *, POS, etc.)
    - Removes special characters
    - Strips extra whitespace
    """
    if not description:
        return ""

    # Convert to lowercase
    normalized = description.lower().strip()

    # Remove common payment prefixes
    prefixes_to_remove = [
        r'^sq \*',           # Square
        r'^sq\*',
        r'^tst\*',           # Toast
        r'^pos ',            # Point of Sale
        r'^pos\s+',
        r'^ach ',            # ACH transfer
        r'^wire ',           # Wire transfer
        r'^chk ',            # Check
        r'^dbt ',            # Debit
        r'^crd ',            # Credit
        r'^pp\*',            # PayPal
        r'^paypal \*',
        r'^zelle ',          # Zelle
        r'^venmo ',          # Venmo
        r'^purchase ',
        r'^payment ',
        r'^debit card ',
        r'^credit card ',
        r'^checkcard ',
        r'^recurring ',
    ]

    for prefix in prefixes_to_remove:
        normalized = re.sub(prefix, '', normalized, flags=re.IGNORECASE)

    # Remove trailing reference numbers (common in bank statements)
    # e.g., "AMAZON PURCHASE 123456789" -> "AMAZON PURCHASE"
    normalized = re.sub(r'\s+\d{6,}$', '', normalized)
    normalized = re.sub(r'\s+#\d+$', '', normalized)
    normalized = re.sub(r'\s+\*\d+$', '', normalized)

    # Remove special characters except spaces
    normalized = re.sub(r'[^\w\s]', ' ', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def match_vendor(description: str) -> Optional[Tuple[str, VendorCategory]]:
    """
    Try to match a transaction description to a known vendor.

    Returns:
        Tuple of (matched_pattern, VendorCategory) if found, None otherwise
    """
    normalized = normalize_vendor_name(description)

    if not normalized:
        return None

    # Try exact match first (for short names like "uber", "lyft")
    for pattern, category in VENDOR_MAPPINGS.items():
        if pattern in normalized or normalized.startswith(pattern):
            return (pattern, category)

    return None


def categorize_by_vendor(description: str) -> Optional[Dict]:
    """
    Attempt to categorize a transaction based on known vendor mappings.

    Args:
        description: The transaction description from bank statement

    Returns:
        Dict with categorization data if vendor is known, None otherwise
    """
    match = match_vendor(description)

    if match is None:
        return None

    pattern, vendor_cat = match

    return {
        "category": vendor_cat.category,
        "subcategory": vendor_cat.subcategory,
        "ledger_type": vendor_cat.ledger_type,
        "confidence": vendor_cat.confidence,
        "method": "vendor_mapping",
        "explanation": f"Known vendor match: {pattern.title()}. {vendor_cat.explanation}",
        "matched_pattern": pattern
    }


def get_all_known_vendors() -> Dict[str, Dict]:
    """
    Return all known vendor mappings (for API exposure).
    """
    return {
        pattern: {
            "category": vc.category,
            "subcategory": vc.subcategory,
            "ledger_type": vc.ledger_type,
            "confidence": vc.confidence
        }
        for pattern, vc in VENDOR_MAPPINGS.items()
    }


def add_custom_vendor(
    pattern: str,
    category: str,
    subcategory: str,
    ledger_type: str,
    explanation: str = ""
) -> bool:
    """
    Add a custom vendor mapping at runtime.

    Note: This only persists for the current session.
    For permanent mappings, add to VENDOR_MAPPINGS dict.
    """
    pattern = pattern.lower().strip()

    if not pattern:
        return False

    VENDOR_MAPPINGS[pattern] = VendorCategory(
        category=category,
        subcategory=subcategory,
        ledger_type=ledger_type,
        confidence=95.0,  # Slightly lower for custom mappings
        explanation=explanation or f"Custom mapping for {pattern}"
    )

    return True
