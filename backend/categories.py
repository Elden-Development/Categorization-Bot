"""
Accounting Categories Configuration

This module defines all available accounting categories, subcategories,
and ledger types for the categorization system.
"""

# Complete list of all available categorizations
CATEGORIES = [
    # Revenue
    {
        "category": "Revenue",
        "subcategory": "Product Sales",
        "ledgerType": "Revenue"
    },
    {
        "category": "Revenue",
        "subcategory": "Service Revenue",
        "ledgerType": "Revenue"
    },
    {
        "category": "Revenue",
        "subcategory": "Rental Revenue",
        "ledgerType": "Revenue"
    },
    {
        "category": "Revenue",
        "subcategory": "Commission Revenue",
        "ledgerType": "Revenue"
    },
    {
        "category": "Revenue",
        "subcategory": "Subscription Revenue",
        "ledgerType": "Revenue"
    },
    {
        "category": "Revenue",
        "subcategory": "Other Income",
        "ledgerType": "Revenue"
    },

    # Cost of Goods Sold (COGS)
    {
        "category": "Cost of Goods Sold (COGS)",
        "subcategory": "Raw Materials",
        "ledgerType": "Expense (COGS)"
    },
    {
        "category": "Cost of Goods Sold (COGS)",
        "subcategory": "Direct Labor",
        "ledgerType": "Expense (COGS)"
    },
    {
        "category": "Cost of Goods Sold (COGS)",
        "subcategory": "Manufacturing Overhead",
        "ledgerType": "Expense (COGS)"
    },
    {
        "category": "Cost of Goods Sold (COGS)",
        "subcategory": "Freight and Delivery",
        "ledgerType": "Expense (COGS)"
    },

    # Operating Expenses
    {
        "category": "Operating Expenses",
        "subcategory": "Salaries and Wages",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Rent",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Utilities",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Office Supplies",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Business Software / IT Expenses",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "HR Expenses",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Marketing and Advertising",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Travel and Entertainment",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Insurance",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Repairs and Maintenance",
        "ledgerType": "Expense (Operating)"
    },
    {
        "category": "Operating Expenses",
        "subcategory": "Depreciation",
        "ledgerType": "Expense (Operating)"
    },

    # Administrative Expenses
    {
        "category": "Administrative Expenses",
        "subcategory": "Professional Fees",
        "ledgerType": "Expense (Administrative)"
    },
    {
        "category": "Administrative Expenses",
        "subcategory": "Office Expenses",
        "ledgerType": "Expense (Administrative)"
    },
    {
        "category": "Administrative Expenses",
        "subcategory": "Postage and Shipping",
        "ledgerType": "Expense (Administrative)"
    },
    {
        "category": "Administrative Expenses",
        "subcategory": "Communication Expense",
        "ledgerType": "Expense (Administrative)"
    },
    {
        "category": "Administrative Expenses",
        "subcategory": "Bank Fees and Charges",
        "ledgerType": "Expense (Administrative)"
    },

    # Financial Expenses
    {
        "category": "Financial Expenses",
        "subcategory": "Interest Expense",
        "ledgerType": "Expense (Financial)"
    },
    {
        "category": "Financial Expenses",
        "subcategory": "Loan Fees",
        "ledgerType": "Expense (Financial)"
    },
    {
        "category": "Financial Expenses",
        "subcategory": "Credit Card Fees",
        "ledgerType": "Expense (Financial)"
    },

    # Other Expenses
    {
        "category": "Other Expenses",
        "subcategory": "Miscellaneous",
        "ledgerType": "Expense (Other)"
    },
    {
        "category": "Other Expenses",
        "subcategory": "Donations/Charitable Contributions",
        "ledgerType": "Expense (Other)"
    },
    {
        "category": "Other Expenses",
        "subcategory": "Loss on Disposal of Assets",
        "ledgerType": "Expense (Other)"
    },

    # Assets – Current
    {
        "category": "Assets – Current",
        "subcategory": "Cash and Cash Equivalents",
        "ledgerType": "Asset (Current)"
    },
    {
        "category": "Assets – Current",
        "subcategory": "Accounts Receivable",
        "ledgerType": "Asset (Current)"
    },
    {
        "category": "Assets – Current",
        "subcategory": "Inventory",
        "ledgerType": "Asset (Current)"
    },
    {
        "category": "Assets – Current",
        "subcategory": "Prepaid Expenses",
        "ledgerType": "Asset (Current)"
    },
    {
        "category": "Assets – Current",
        "subcategory": "Short-term Investments",
        "ledgerType": "Asset (Current)"
    },

    # Assets – Fixed / Long-term
    {
        "category": "Assets – Fixed / Long-term",
        "subcategory": "Property, Plant, and Equipment",
        "ledgerType": "Asset (Fixed)"
    },
    {
        "category": "Assets – Fixed / Long-term",
        "subcategory": "Furniture and Fixtures",
        "ledgerType": "Asset (Fixed)"
    },
    {
        "category": "Assets – Fixed / Long-term",
        "subcategory": "Vehicles",
        "ledgerType": "Asset (Fixed)"
    },
    {
        "category": "Assets – Fixed / Long-term",
        "subcategory": "Machinery and Equipment",
        "ledgerType": "Asset (Fixed)"
    },
    {
        "category": "Assets – Fixed / Long-term",
        "subcategory": "Computer Equipment",
        "ledgerType": "Asset (Fixed)"
    },

    # Assets – Intangible
    {
        "category": "Assets – Intangible",
        "subcategory": "Patents",
        "ledgerType": "Asset (Intangible)"
    },
    {
        "category": "Assets – Intangible",
        "subcategory": "Trademarks",
        "ledgerType": "Asset (Intangible)"
    },
    {
        "category": "Assets – Intangible",
        "subcategory": "Copyrights",
        "ledgerType": "Asset (Intangible)"
    },
    {
        "category": "Assets – Intangible",
        "subcategory": "Goodwill",
        "ledgerType": "Asset (Intangible)"
    },
    {
        "category": "Assets – Intangible",
        "subcategory": "Capitalized Software",
        "ledgerType": "Asset (Intangible)"
    },

    # Liabilities – Current
    {
        "category": "Liabilities – Current",
        "subcategory": "Accounts Payable",
        "ledgerType": "Liability (Current)"
    },
    {
        "category": "Liabilities – Current",
        "subcategory": "Short-term Loans",
        "ledgerType": "Liability (Current)"
    },
    {
        "category": "Liabilities – Current",
        "subcategory": "Accrued Liabilities",
        "ledgerType": "Liability (Current)"
    },
    {
        "category": "Liabilities – Current",
        "subcategory": "Current Portion of Long-term Debt",
        "ledgerType": "Liability (Current)"
    },

    # Liabilities – Long-term
    {
        "category": "Liabilities – Long-term",
        "subcategory": "Long-term Loans",
        "ledgerType": "Liability (Long-term)"
    },
    {
        "category": "Liabilities – Long-term",
        "subcategory": "Bonds Payable",
        "ledgerType": "Liability (Long-term)"
    },
    {
        "category": "Liabilities – Long-term",
        "subcategory": "Deferred Tax Liabilities",
        "ledgerType": "Liability (Long-term)"
    },

    # Equity
    {
        "category": "Equity",
        "subcategory": "Common Stock",
        "ledgerType": "Equity"
    },
    {
        "category": "Equity",
        "subcategory": "Retained Earnings",
        "ledgerType": "Equity"
    },
    {
        "category": "Equity",
        "subcategory": "Additional Paid-in Capital",
        "ledgerType": "Equity"
    },
    {
        "category": "Equity",
        "subcategory": "Dividends/Distributions",
        "ledgerType": "Equity"
    },

    # Adjusting / Journal Entries
    {
        "category": "Adjusting / Journal Entries",
        "subcategory": "Accruals/Deferrals/Depreciation Adjustments",
        "ledgerType": "Adjustment"
    }
]


def get_all_categories():
    """Get all available categories."""
    return CATEGORIES


def get_categories_by_parent():
    """Get categories grouped by parent category."""
    result = {}
    for cat in CATEGORIES:
        parent = cat["category"]
        if parent not in result:
            result[parent] = []
        result[parent].append({
            "subcategory": cat["subcategory"],
            "ledgerType": cat["ledgerType"]
        })
    return result


def get_unique_categories():
    """Get unique parent categories."""
    return list(set(cat["category"] for cat in CATEGORIES))


def get_subcategories_for_category(category):
    """Get all subcategories for a given parent category."""
    return [
        {
            "subcategory": cat["subcategory"],
            "ledgerType": cat["ledgerType"]
        }
        for cat in CATEGORIES
        if cat["category"] == category
    ]
