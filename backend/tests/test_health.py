"""
Tests for health check endpoints.

Run with: pytest tests/test_health.py -v
"""

import pytest


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Categorization Bot API"
        assert data["status"] == "running"
        assert "version" in data

    def test_health_quick(self, client):
        """Test quick health check returns OK."""
        response = client.get("/health/quick")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"

    def test_health_full(self, client):
        """Test full health check returns service statuses."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "api" in data["services"]
        assert "database" in data["services"]
        assert "gemini" in data["services"]
        assert "timestamp" in data

    def test_health_api_is_up(self, client):
        """Test that API service shows as up."""
        response = client.get("/health")
        data = response.json()

        assert data["services"]["api"]["status"] == "up"
