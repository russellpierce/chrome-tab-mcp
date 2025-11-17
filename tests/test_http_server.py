#!/usr/bin/env python3
"""
Functional Tests for Chrome Tab Reader HTTP Server (FastAPI)

Tests the actual HTTP endpoints using FastAPI's TestClient.
Tests include:
- Authentication (Bearer token validation)
- All API endpoints (health, current_tab, extract, navigate_and_extract)
- Request/response validation
- Error handling
- Different scenarios (success, auth failures, extraction failures)

Requirements:
- pytest
- fastapi
- httpx (for TestClient)
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the FastAPI app
from chrome_tab_http_server import app, verify_token, ChromeTabExtractor, VALID_TOKENS


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def valid_token():
    """Provide a valid test token"""
    return "test_valid_token_12345"


@pytest.fixture
def mock_valid_tokens(valid_token):
    """Mock the VALID_TOKENS set with a test token"""
    with patch('chrome_tab_http_server.VALID_TOKENS', {valid_token}):
        yield valid_token


@pytest.fixture
def client(mock_valid_tokens):
    """Create a TestClient with mocked authentication"""
    return TestClient(app)


@pytest.fixture
def auth_headers(valid_token):
    """Provide authentication headers with valid Bearer token"""
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def invalid_auth_headers():
    """Provide authentication headers with invalid token"""
    return {"Authorization": "Bearer invalid_token_xyz"}


# ============================================================================
# Authentication Tests
# ============================================================================

class TestAuthentication:
    """Test Bearer token authentication"""

    def test_health_endpoint_requires_auth(self, client):
        """Test that health endpoint requires authentication"""
        response = client.get("/api/health")
        assert response.status_code == 403  # No auth header

    def test_health_endpoint_with_invalid_token(self, client, invalid_auth_headers):
        """Test health endpoint with invalid token"""
        response = client.get("/api/health", headers=invalid_auth_headers)
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "Unauthorized"

    def test_health_endpoint_with_valid_token(self, client, auth_headers):
        """Test health endpoint with valid token"""
        response = client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_extract_endpoint_requires_auth(self, client):
        """Test that extract endpoint requires authentication"""
        response = client.post("/api/extract", json={"action": "extract_current_tab"})
        assert response.status_code == 403

    def test_current_tab_endpoint_requires_auth(self, client):
        """Test that current_tab endpoint requires authentication"""
        response = client.get("/api/current_tab")
        assert response.status_code == 403


# ============================================================================
# Health Check Endpoint Tests
# ============================================================================

class TestHealthEndpoint:
    """Test /api/health endpoint"""

    def test_health_check_success(self, client, auth_headers):
        """Test successful health check"""
        response = client.get("/api/health", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "extension_version" in data
        assert data["extension_version"] == "1.0.0"
        assert "port" in data
        assert data["port"] == 8888
        assert "platform" in data
        assert isinstance(data["platform"], str)

    def test_health_response_schema(self, client, auth_headers):
        """Test health endpoint response matches schema"""
        response = client.get("/api/health", headers=auth_headers)
        data = response.json()

        # Verify all required fields are present
        required_fields = ["status", "extension_version", "port", "platform"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


# ============================================================================
# Current Tab Endpoint Tests
# ============================================================================

class TestCurrentTabEndpoint:
    """Test /api/current_tab endpoint"""

    def test_current_tab_success(self, client, auth_headers):
        """Test successful current tab info retrieval"""
        mock_result = {
            "tab_id": "test_tab_123",
            "url": "https://example.com",
            "title": "Example Domain",
            "is_loading": False
        }

        with patch.object(ChromeTabExtractor, 'get_current_tab_info', return_value=mock_result):
            response = client.get("/api/current_tab", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert data["tab_id"] == "test_tab_123"
            assert data["url"] == "https://example.com"
            assert data["title"] == "Example Domain"
            assert data["is_loading"] is False

    def test_current_tab_error(self, client, auth_headers):
        """Test current tab endpoint when extraction fails"""
        mock_result = {
            "status": "error",
            "error": "Chrome not running"
        }

        with patch.object(ChromeTabExtractor, 'get_current_tab_info', return_value=mock_result):
            response = client.get("/api/current_tab", headers=auth_headers)
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_current_tab_without_auth(self, client):
        """Test current tab endpoint without authentication"""
        response = client.get("/api/current_tab")
        assert response.status_code == 403


# ============================================================================
# Extract Endpoint Tests
# ============================================================================

class TestExtractEndpoint:
    """Test /api/extract endpoint"""

    def test_extract_success(self, client, auth_headers):
        """Test successful content extraction"""
        mock_result = {
            "status": "success",
            "content": "This is the extracted content from the page.",
            "title": "Test Page",
            "url": "https://test.example.com",
            "extraction_time_ms": 2500.5
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_result):
            response = client.post(
                "/api/extract",
                json={"action": "extract_current_tab", "strategy": "three-phase"},
                headers=auth_headers
            )
            assert response.status_code == 200

            data = response.json()
            assert data["status"] == "success"
            assert data["content"] == "This is the extracted content from the page."
            assert data["title"] == "Test Page"
            assert data["url"] == "https://test.example.com"
            assert data["extraction_time_ms"] == 2500.5

    def test_extract_with_immediate_strategy(self, client, auth_headers):
        """Test extraction with immediate strategy"""
        mock_result = {
            "status": "success",
            "content": "Immediate extraction content",
            "title": "Quick Page",
            "url": "https://quick.example.com",
            "extraction_time_ms": 100
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_result):
            response = client.post(
                "/api/extract",
                json={"action": "extract_current_tab", "strategy": "immediate"},
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_extract_default_values(self, client, auth_headers):
        """Test extraction with default values (no explicit parameters)"""
        mock_result = {
            "status": "success",
            "content": "Default extraction",
            "title": "Default Page",
            "url": "https://default.example.com",
            "extraction_time_ms": 1500
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_result):
            response = client.post(
                "/api/extract",
                json={},  # Use default values
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_extract_error_chrome_not_running(self, client, auth_headers):
        """Test extraction when Chrome is not running"""
        mock_result = {
            "status": "error",
            "error": "Chrome is not running"
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_result):
            response = client.post(
                "/api/extract",
                json={"action": "extract_current_tab"},
                headers=auth_headers
            )
            assert response.status_code == 500

    def test_extract_error_applescript_failure(self, client, auth_headers):
        """Test extraction when AppleScript fails"""
        mock_result = {
            "status": "error",
            "error": "AppleScript error: execution failed"
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_result):
            response = client.post(
                "/api/extract",
                json={"action": "extract_current_tab"},
                headers=auth_headers
            )
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_extract_without_auth(self, client):
        """Test extraction without authentication"""
        response = client.post(
            "/api/extract",
            json={"action": "extract_current_tab"}
        )
        assert response.status_code == 403


# ============================================================================
# Navigate and Extract Endpoint Tests
# ============================================================================

class TestNavigateAndExtractEndpoint:
    """Test /api/navigate_and_extract endpoint"""

    def test_navigate_and_extract_not_implemented(self, client, auth_headers):
        """Test that navigate_and_extract returns not implemented error"""
        mock_result = {
            "status": "error",
            "error": "Navigate and extract not yet implemented. Use extract endpoint on the target page instead."
        }

        with patch.object(ChromeTabExtractor, 'navigate_and_extract', return_value=mock_result):
            response = client.post(
                "/api/navigate_and_extract",
                json={"url": "https://example.com"},
                headers=auth_headers
            )
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data

    def test_navigate_and_extract_with_all_params(self, client, auth_headers):
        """Test navigate_and_extract with all parameters"""
        mock_result = {
            "status": "error",
            "error": "Not implemented"
        }

        with patch.object(ChromeTabExtractor, 'navigate_and_extract', return_value=mock_result):
            response = client.post(
                "/api/navigate_and_extract",
                json={
                    "url": "https://example.com",
                    "strategy": "three-phase",
                    "wait_for_ms": 5000
                },
                headers=auth_headers
            )
            assert response.status_code == 500

    def test_navigate_and_extract_without_auth(self, client):
        """Test navigate_and_extract without authentication"""
        response = client.post(
            "/api/navigate_and_extract",
            json={"url": "https://example.com"}
        )
        assert response.status_code == 403

    def test_navigate_and_extract_invalid_wait_time(self, client, auth_headers):
        """Test navigate_and_extract with invalid wait time"""
        response = client.post(
            "/api/navigate_and_extract",
            json={
                "url": "https://example.com",
                "wait_for_ms": -1000  # Negative value should be rejected
            },
            headers=auth_headers
        )
        # Should fail validation (422 Unprocessable Entity)
        assert response.status_code == 422


# ============================================================================
# Root Endpoint Tests
# ============================================================================

class TestRootEndpoint:
    """Test / root endpoint"""

    def test_root_redirects_to_docs(self, client):
        """Test that root redirects to /docs"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # Temporary redirect
        assert response.headers["location"] == "/docs"


# ============================================================================
# Request/Response Schema Validation Tests
# ============================================================================

class TestSchemaValidation:
    """Test request and response schema validation"""

    def test_extract_request_validation(self, client, auth_headers):
        """Test that extract endpoint validates request schema"""
        # Valid request should work
        mock_result = {
            "status": "success",
            "content": "Test content",
            "title": "Test",
            "url": "https://test.com",
            "extraction_time_ms": 1000
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_result):
            response = client.post(
                "/api/extract",
                json={"strategy": "three-phase"},
                headers=auth_headers
            )
            assert response.status_code == 200

    def test_navigate_request_missing_url(self, client, auth_headers):
        """Test that navigate_and_extract requires URL"""
        response = client.post(
            "/api/navigate_and_extract",
            json={"strategy": "three-phase"},  # Missing required 'url' field
            headers=auth_headers
        )
        # Should fail validation
        assert response.status_code == 422

    def test_extract_response_contains_all_fields(self, client, auth_headers):
        """Test that successful extraction response contains all expected fields"""
        mock_result = {
            "status": "success",
            "content": "Full content here",
            "title": "Full Page",
            "url": "https://full.example.com",
            "extraction_time_ms": 3456.78
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_result):
            response = client.post(
                "/api/extract",
                json={"action": "extract_current_tab"},
                headers=auth_headers
            )
            data = response.json()

            # Check all fields are present
            assert "status" in data
            assert "content" in data
            assert "title" in data
            assert "url" in data
            assert "extraction_time_ms" in data


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for multiple endpoint interactions"""

    def test_health_then_extract_flow(self, client, auth_headers):
        """Test typical usage flow: check health, then extract"""
        # First check health
        health_response = client.get("/api/health", headers=auth_headers)
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "ok"

        # Then extract content
        mock_result = {
            "status": "success",
            "content": "Integration test content",
            "title": "Integration Page",
            "url": "https://integration.example.com",
            "extraction_time_ms": 2000
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_result):
            extract_response = client.post(
                "/api/extract",
                json={"strategy": "three-phase"},
                headers=auth_headers
            )
            assert extract_response.status_code == 200
            assert extract_response.json()["status"] == "success"

    def test_current_tab_then_extract_flow(self, client, auth_headers):
        """Test flow: get current tab info, then extract"""
        # First get tab info
        mock_tab_info = {
            "tab_id": "tab_456",
            "url": "https://workflow.example.com",
            "title": "Workflow Page",
            "is_loading": False
        }

        with patch.object(ChromeTabExtractor, 'get_current_tab_info', return_value=mock_tab_info):
            tab_response = client.get("/api/current_tab", headers=auth_headers)
            assert tab_response.status_code == 200

        # Then extract content
        mock_extract = {
            "status": "success",
            "content": "Workflow content",
            "title": "Workflow Page",
            "url": "https://workflow.example.com",
            "extraction_time_ms": 1800
        }

        with patch.object(ChromeTabExtractor, 'extract_current_tab', return_value=mock_extract):
            extract_response = client.post(
                "/api/extract",
                json={},
                headers=auth_headers
            )
            assert extract_response.status_code == 200


# ============================================================================
# OpenAPI Schema Tests
# ============================================================================

class TestOpenAPISchema:
    """Test OpenAPI schema generation"""

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_all_endpoints_in_schema(self, client):
        """Test that all endpoints are documented in OpenAPI schema"""
        response = client.get("/openapi.json")
        schema = response.json()
        paths = schema["paths"]

        expected_endpoints = [
            "/api/health",
            "/api/current_tab",
            "/api/extract",
            "/api/navigate_and_extract"
        ]

        for endpoint in expected_endpoints:
            assert endpoint in paths, f"Endpoint {endpoint} missing from OpenAPI schema"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test various error scenarios"""

    def test_malformed_json_request(self, client, auth_headers):
        """Test handling of malformed JSON in request"""
        response = client.post(
            "/api/extract",
            data="invalid json{{{",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        # FastAPI should return 422 for invalid JSON
        assert response.status_code == 422

    def test_missing_content_type(self, client, auth_headers):
        """Test request without proper content-type header"""
        response = client.post(
            "/api/extract",
            data='{"strategy": "three-phase"}',
            headers=auth_headers
        )
        # Should still work or return proper error
        assert response.status_code in [200, 422, 500]

    def test_empty_bearer_token(self, client):
        """Test request with empty bearer token"""
        response = client.get(
            "/api/health",
            headers={"Authorization": "Bearer "}
        )
        # FastAPI returns 403 for invalid/empty bearer tokens
        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
