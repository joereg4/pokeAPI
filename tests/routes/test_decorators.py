# tests/routes/test_decorators.py
"""Unit tests for routes.decorators.handle_api_errors.

Tests verify that the decorator correctly translates Python exceptions
into the appropriate Flask HTTP responses, and that Flask's own
HTTPExceptions (from abort()) pass through unmodified.
"""

import pytest
from unittest.mock import MagicMock
from flask import Flask, abort
from requests.exceptions import HTTPError
from routes.decorators import handle_api_errors


# ---------------------------------------------------------------------------
# Minimal Flask app for testing the decorator in isolation
# ---------------------------------------------------------------------------

@pytest.fixture
def decorator_app():
    """Create a minimal Flask app with routes wrapped by the decorator."""
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/happy/<name>")
    @handle_api_errors("Widget")
    def happy_path(name):
        return f"Hello, {name}!"

    @app.route("/value-error-not-found")
    @handle_api_errors("Widget")
    def value_error_not_found():
        raise ValueError("Widget 'foo' not found")

    @app.route("/value-error-bad-request")
    @handle_api_errors("Widget")
    def value_error_bad_request():
        raise ValueError("Invalid input: negative number")

    @app.route("/http-error-404")
    @handle_api_errors("Widget")
    def http_error_404():
        response = MagicMock()
        response.status_code = 404
        raise HTTPError(response=response)

    @app.route("/http-error-500")
    @handle_api_errors("Widget")
    def http_error_500():
        response = MagicMock()
        response.status_code = 500
        raise HTTPError(response=response)

    @app.route("/http-error-no-response")
    @handle_api_errors("Widget")
    def http_error_no_response():
        raise HTTPError()

    @app.route("/unexpected-error")
    @handle_api_errors("Widget")
    def unexpected_error():
        raise RuntimeError("Something went terribly wrong")

    @app.route("/abort-404")
    @handle_api_errors("Widget")
    def abort_inside():
        abort(404, description="Manually aborted")

    @app.route("/abort-403")
    @handle_api_errors("Widget")
    def abort_forbidden():
        abort(403, description="Forbidden")

    return app


@pytest.fixture
def test_client(decorator_app):
    return decorator_app.test_client()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestHappyPath:
    def test_returns_response_on_success(self, test_client):
        response = test_client.get("/happy/world")
        assert response.status_code == 200
        assert b"Hello, world!" in response.data


# ---------------------------------------------------------------------------
# ValueError handling
# ---------------------------------------------------------------------------

class TestValueError:
    def test_not_found_message_returns_404(self, test_client):
        """ValueError with 'not found' in message -> 404."""
        response = test_client.get("/value-error-not-found")
        assert response.status_code == 404

    def test_other_message_returns_400(self, test_client):
        """ValueError without 'not found' -> 400."""
        response = test_client.get("/value-error-bad-request")
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# HTTPError handling
# ---------------------------------------------------------------------------

class TestHTTPError:
    def test_upstream_404_returns_404(self, test_client):
        """HTTPError with response.status_code == 404 -> 404."""
        response = test_client.get("/http-error-404")
        assert response.status_code == 404

    def test_upstream_500_returns_500(self, test_client):
        """HTTPError with non-404 status -> 500."""
        response = test_client.get("/http-error-500")
        assert response.status_code == 500

    def test_no_response_attr_returns_500(self, test_client):
        """HTTPError with no response object -> 500 (uses getattr default)."""
        response = test_client.get("/http-error-no-response")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# Unexpected exception handling
# ---------------------------------------------------------------------------

class TestUnexpectedError:
    def test_runtime_error_returns_500(self, test_client):
        """Any non-ValueError, non-HTTPError exception -> 500."""
        response = test_client.get("/unexpected-error")
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# HTTPException passthrough (abort() inside the route)
# ---------------------------------------------------------------------------

class TestAbortPassthrough:
    def test_abort_404_passes_through(self, test_client):
        """abort(404) inside the route should not be caught by the decorator."""
        response = test_client.get("/abort-404")
        assert response.status_code == 404

    def test_abort_403_passes_through(self, test_client):
        """abort(403) should not be caught by the decorator."""
        response = test_client.get("/abort-403")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Decorator metadata
# ---------------------------------------------------------------------------

class TestDecoratorMetadata:
    def test_preserves_function_name(self, decorator_app):
        """@wraps should preserve the original function name."""
        rules = {rule.endpoint: rule for rule in decorator_app.url_map.iter_rules()}
        assert "happy_path" in rules
        assert "value_error_not_found" in rules

    def test_preserves_docstring(self):
        """The decorator should preserve the original function's docstring."""
        @handle_api_errors("Test")
        def documented_func():
            """This is a docstring."""
            pass

        assert documented_func.__doc__ == "This is a docstring."
