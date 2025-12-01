"""
Pytest configuration and shared fixtures for Categorization Bot tests.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_document_data():
    """Sample document data for testing categorization."""
    return {
        "documentMetadata": {
            "documentType": "Invoice",
            "documentDate": "2024-01-15",
            "source": {
                "name": "Office Supplies Inc"
            }
        },
        "financialData": {
            "totalAmount": 250.00,
            "currency": "USD"
        },
        "partyInformation": {
            "vendor": {
                "name": "Office Supplies Inc"
            }
        },
        "lineItems": [
            {"description": "Printer Paper", "quantity": 10, "unitPrice": 15.00, "totalPrice": 150.00},
            {"description": "Pens", "quantity": 20, "unitPrice": 5.00, "totalPrice": 100.00}
        ]
    }


@pytest.fixture
def sample_vendor_name():
    """Sample vendor name for testing."""
    return "Amazon"


@pytest.fixture
def test_pdf_path():
    """Path to test PDF file (if exists)."""
    test_file = os.path.join(os.path.dirname(__file__), "test_files", "test_invoice.pdf")
    if os.path.exists(test_file):
        return test_file
    return None
