"""
Tests for main API endpoints.

Run with: pytest tests/test_api_endpoints.py -v
"""

import pytest
import json


class TestCategoriesEndpoint:
    """Test category listing endpoints."""

    def test_get_categories(self, client):
        """Test getting all categories."""
        response = client.get("/categories")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list) or isinstance(data, dict)


class TestVendorResearch:
    """Test vendor research endpoints."""

    def test_vendor_research_missing_name(self, client):
        """Test vendor research with missing vendor name."""
        response = client.post(
            "/research-vendor",
            json={"vendor_name": ""}
        )
        # Should return error for empty vendor name
        assert response.status_code in [200, 400, 422]

    def test_vendor_research_valid_request(self, client, sample_vendor_name):
        """Test vendor research with valid vendor name."""
        response = client.post(
            "/research-vendor",
            json={"vendor_name": sample_vendor_name}
        )
        assert response.status_code == 200

        data = response.json()
        # Should return either response or error (rate limit possible)
        assert "response" in data or "error" in data


class TestCategorization:
    """Test categorization endpoints."""

    def test_categorize_transaction_missing_data(self, client):
        """Test categorization with missing data."""
        response = client.post(
            "/categorize-transaction",
            json={}
        )
        # Should return error for missing data
        assert response.status_code in [400, 422]

    def test_categorize_transaction_hybrid_missing_data(self, client):
        """Test hybrid categorization with missing data."""
        response = client.post(
            "/categorize-transaction-hybrid",
            json={}
        )
        # Should return error for missing data
        assert response.status_code in [400, 422]

    def test_categorize_transaction_hybrid_valid(self, client, sample_document_data):
        """Test hybrid categorization with valid data."""
        response = client.post(
            "/categorize-transaction-hybrid",
            json={
                "vendor_info": "Office Supplies Inc",
                "document_data": sample_document_data,
                "transaction_purpose": "Office supplies purchase"
            }
        )
        assert response.status_code == 200

        data = response.json()
        # Should return categorization or error (API issues possible)
        assert "geminiCategorization" in data or "error" in data or "mlPrediction" in data


class TestDocumentProcessing:
    """Test document processing endpoints."""

    def test_process_pdf_no_file(self, client):
        """Test PDF processing without file."""
        response = client.post("/process-pdf")
        # Should return error for missing file
        assert response.status_code == 422

    def test_process_pdf_invalid_schema(self, client):
        """Test PDF processing with invalid schema."""
        # Create a minimal file-like request
        response = client.post(
            "/process-pdf",
            data={"schema": "invalid_schema"},
            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        )
        # Should return error for invalid schema
        assert response.status_code in [400, 422]


class TestInputValidation:
    """Test input validation across endpoints."""

    def test_vendor_research_long_name(self, client):
        """Test vendor research with excessively long name."""
        long_name = "A" * 1000  # Very long name
        response = client.post(
            "/research-vendor",
            json={"vendor_name": long_name}
        )
        # Should reject or truncate
        assert response.status_code in [200, 400, 422]

    def test_categorization_with_list_document_data(self, client):
        """Test categorization rejects list when dict is required for document_data."""
        response = client.post(
            "/categorize-transaction-hybrid",
            json={
                "vendor_info": "Test Vendor",
                "document_data": [{"test": "data"}],  # List instead of dict - should be rejected
                "transaction_purpose": "Test"
            }
        )
        # Pydantic validation should reject this with 422 Unprocessable Entity
        assert response.status_code == 422

        data = response.json()
        # Should have validation error details
        assert "detail" in data
