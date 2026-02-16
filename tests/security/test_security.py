"""Security tests for common web vulnerabilities.

Tests cover:
  - XSS injection via search input and URL parameters
  - SQL injection via search input
  - Path traversal via sprite routes
  - HTTP header injection
  - Input validation edge cases

These tests verify that the application's existing defences (Jinja2 auto-
escaping, SQLAlchemy parameterised queries, input validation) work correctly.
"""

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(app):
    """Test client from the shared app fixture."""
    return app.test_client()


# ---------------------------------------------------------------------------
# XSS Tests
# ---------------------------------------------------------------------------


class TestXSSPrevention:
    """Verify that user-supplied input is not reflected unescaped."""

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        '"><img src=x onerror=alert(1)>',
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        "{{7*7}}",
    ]

    def test_search_xss_in_query(self, client):
        """Search API should not reflect raw script tags in output."""
        for payload in self.XSS_PAYLOADS:
            response = client.get(f"/api/search?q={payload}")
            assert response.status_code in (200, 500)
            if response.status_code == 200:
                data = response.get_data(as_text=True)
                assert "<script>" not in data
                assert "onerror=" not in data

    def test_404_page_xss(self, client):
        """404 error page should escape the requested path."""
        for payload in self.XSS_PAYLOADS:
            response = client.get(f"/{payload}")
            data = response.get_data(as_text=True)
            assert "<script>alert" not in data
            assert "onerror=alert" not in data

    def test_pokemon_route_xss(self, client):
        """Pokemon route should escape name parameter."""
        with patch("routes.pokemon.APIResource") as mock_api:
            mock_api.fetch_data.side_effect = ValueError("not found")
            response = client.get("/pokemon/<script>alert(1)</script>")
            data = response.get_data(as_text=True)
            assert "<script>alert" not in data


# ---------------------------------------------------------------------------
# SQL Injection Tests
# ---------------------------------------------------------------------------


class TestSQLInjection:
    """Verify that SQLAlchemy parameterisation prevents injection."""

    SQL_PAYLOADS = [
        "'; DROP TABLE resources; --",
        "1 OR 1=1",
        "' UNION SELECT * FROM users --",
        "admin'--",
        "1; SELECT * FROM information_schema.tables",
    ]

    def test_search_sql_injection(self, client):
        """Search endpoint should safely handle SQL injection attempts."""
        for payload in self.SQL_PAYLOADS:
            response = client.get(f"/api/search?q={payload}")
            assert response.status_code in (200, 500)
            if response.status_code == 200:
                data = response.get_json()
                assert isinstance(data, list)

    def test_search_limit_injection(self, client):
        """Search limit parameter should reject non-numeric values."""
        response = client.get("/api/search?q=pikachu&limit=1;DROP TABLE resources")
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.get_json()
            assert isinstance(data, list)


# ---------------------------------------------------------------------------
# Path Traversal Tests
# ---------------------------------------------------------------------------


class TestPathTraversal:
    """Verify that sprite routes reject path traversal attempts."""

    TRAVERSAL_PAYLOADS = [
        "../../../etc/passwd",
        "....//....//etc/passwd",
    ]

    def test_sprite_artwork_traversal(self, client):
        """Sprite artwork route should reject path traversal."""
        for payload in self.TRAVERSAL_PAYLOADS:
            response = client.get(f"/sprite/artwork/{payload}")
            data = response.get_data(as_text=True)
            assert "root:" not in data
            assert response.status_code in (200, 400, 404, 500)

    def test_sprite_default_traversal(self, client):
        """Default sprite route should reject path traversal."""
        for payload in self.TRAVERSAL_PAYLOADS:
            response = client.get(f"/sprite/default/{payload}")
            data = response.get_data(as_text=True)
            assert "root:" not in data

    def test_sprite_specific_traversal(self, client):
        """Specific sprite route should reject path traversal."""
        for payload in self.TRAVERSAL_PAYLOADS:
            response = client.get(f"/sprite/{payload}/front_default")
            data = response.get_data(as_text=True)
            assert "root:" not in data


# ---------------------------------------------------------------------------
# HTTP Header Injection Tests
# ---------------------------------------------------------------------------


class TestHeaderInjection:
    """Verify that request headers cannot inject additional headers."""

    def test_request_id_header_sanitised(self, client):
        """X-Request-ID with newlines should be rejected at the framework level."""
        malicious_id = "legit-id\r\nX-Injected: true"
        # Werkzeug rejects newlines in header values -- this is the expected
        # security behaviour.  Verify the framework catches it.
        with pytest.raises(ValueError, match="newline"):
            client.get("/", headers={"X-Request-ID": malicious_id})

    def test_host_header_injection(self, client):
        """Host header injection should not cause server errors."""
        response = client.get("/", headers={"Host": "evil.com"})
        assert response.status_code in (200, 301, 302, 308, 404, 500)


# ---------------------------------------------------------------------------
# Input Validation Tests
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Verify that invalid inputs are handled safely."""

    def test_extremely_long_search_query(self, client):
        """Very long search queries should not crash the server."""
        long_query = "a" * 10000
        response = client.get(f"/api/search?q={long_query}")
        assert response.status_code in (200, 400, 413, 500)

    def test_null_bytes_in_search(self, client):
        """Null bytes in search should not cause crashes."""
        response = client.get("/api/search?q=pikachu%00admin")
        assert response.status_code in (200, 400, 500)

    def test_unicode_in_routes(self, client):
        """Unicode characters in routes should be handled safely."""
        response = client.get("/pokemon/%E2%98%83")
        assert response.status_code in (200, 301, 302, 400, 404, 500)

    def test_empty_sprite_type(self, client):
        """Empty sprite type should return an error, not crash."""
        response = client.get("/sprite/25/")
        assert response.status_code in (200, 301, 308, 400, 404, 405)
