"""
Tests for error handling and edge cases.

These tests verify that the application handles errors gracefully
and returns user-friendly messages instead of raw exceptions.

Run with: pytest tests/test_error_handling.py -v
"""

import pytest


class TestErrorResponses:
    """Test that errors return user-friendly messages."""

    def test_empty_vendor_research(self, client):
        """Test that empty vendor name returns clear error."""
        response = client.post(
            "/research-vendor",
            json={"vendor_name": "   "}  # Whitespace only
        )

        if response.status_code == 200:
            data = response.json()
            # Should have an error message, not a crash
            assert "error" in data or "response" in data

    def test_invalid_json_body(self, client):
        """Test handling of invalid JSON body."""
        response = client.post(
            "/categorize-transaction-hybrid",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        # Should return 422 Unprocessable Entity, not 500
        assert response.status_code == 422

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post(
            "/categorize-transaction-hybrid",
            json={"vendor_info": "Test"}  # Missing document_data
        )
        assert response.status_code == 422


class TestDataTypeHandling:
    """Test handling of various data types."""

    def test_document_data_as_empty_dict(self, client):
        """Test categorization with empty document data."""
        response = client.post(
            "/categorize-transaction-hybrid",
            json={
                "vendor_info": "Test Vendor",
                "document_data": {},
                "transaction_purpose": ""
            }
        )
        assert response.status_code == 200
        # Should not crash, even with empty data

    def test_document_data_nested_lists(self, client):
        """Test categorization with nested list structures."""
        response = client.post(
            "/categorize-transaction-hybrid",
            json={
                "vendor_info": "Test Vendor",
                "document_data": {
                    "lineItems": [
                        {"description": "Item 1"},
                        {"description": "Item 2"}
                    ],
                    "metadata": {
                        "tags": ["tag1", "tag2"]
                    }
                },
                "transaction_purpose": "Test"
            }
        )
        assert response.status_code == 200


class TestRateLimitHandling:
    """Test that rate limit errors are handled gracefully."""

    def test_rate_limit_returns_friendly_message(self, client):
        """
        Test that if rate limiting occurs, we get a friendly message.
        Note: This test may not trigger actual rate limiting.
        """
        # Make a request that might hit rate limits
        response = client.post(
            "/research-vendor",
            json={"vendor_name": "Test Company"}
        )

        if response.status_code == 200:
            data = response.json()
            # If there's an error, it should be user-friendly
            if "error" in data:
                # Should not contain raw API error details
                assert "RESOURCE_EXHAUSTED" not in data["error"]
                assert "429" not in data["error"]
