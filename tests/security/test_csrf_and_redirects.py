"""Security tests for CSRF protection and open-redirect prevention.

Covers:
  - safe_return_to() only allows internal relative paths
  - summary review routes never redirect to attacker-controlled external URLs
  - CSRF protection rejects POSTs without a token when enabled
"""

import pytest
from models.model import Resource, db
from routes.summary_review import safe_return_to


# ---------------------------------------------------------------------------
# safe_return_to unit tests
# ---------------------------------------------------------------------------


class TestSafeReturnTo:
    FALLBACK = "/summary-review"

    @pytest.mark.parametrize(
        "url",
        [
            "/admin/pokemon-summaries",
            "/summary-review?search=pikachu",
            "relative/path",
        ],
    )
    def test_allows_internal_paths(self, url):
        assert safe_return_to(url, self.FALLBACK) == url

    @pytest.mark.parametrize(
        "url",
        [
            "https://evil.com/phish",
            "http://evil.com",
            "//evil.com/protocol-relative",
            "javascript:alert(1)",
        ],
    )
    def test_rejects_external_urls(self, url):
        assert safe_return_to(url, self.FALLBACK) == self.FALLBACK

    def test_none_and_empty_fall_back(self):
        assert safe_return_to(None, self.FALLBACK) == self.FALLBACK
        assert safe_return_to("", self.FALLBACK) == self.FALLBACK


# ---------------------------------------------------------------------------
# Open redirect route tests
# ---------------------------------------------------------------------------


@pytest.fixture
def pokemon_resource(app):
    with app.app_context():
        resource = Resource(resource="pokemon", name="pikachu", summary="A mouse.")
        db.session.add(resource)
        db.session.commit()
        yield resource
        db.session.query(Resource).delete()
        db.session.commit()


class TestOpenRedirectPrevention:
    def test_update_summary_ignores_external_return_to(
        self, auth_client, pokemon_resource
    ):
        """Accepting a summary with an external return_to must stay on-site."""
        response = auth_client.post(
            "/summary-review/pokemon/pikachu?return_to=https://evil.com/phish",
            data={"action": "accept", "edited_summary": "Updated."},
        )
        assert response.status_code == 302
        assert "evil.com" not in response.headers["Location"]

    def test_update_summary_follows_internal_return_to(
        self, auth_client, pokemon_resource
    ):
        response = auth_client.post(
            "/summary-review/pokemon/pikachu?return_to=/admin/pokemon-summaries",
            data={"action": "accept", "edited_summary": "Updated."},
        )
        assert response.status_code == 302
        assert response.headers["Location"] == "/admin/pokemon-summaries"


# ---------------------------------------------------------------------------
# CSRF protection tests
# ---------------------------------------------------------------------------


class TestCSRFProtection:
    def test_post_without_token_rejected_when_csrf_enabled(self, app):
        """With CSRF enabled (as in production), a token-less POST fails."""
        app.config["WTF_CSRF_ENABLED"] = True
        client = app.test_client()
        response = client.post(
            "/auth/login", data={"username": "admin", "password": "wrong"}
        )
        assert response.status_code == 400

    def test_login_form_renders_csrf_token(self, app):
        app.config["WTF_CSRF_ENABLED"] = True
        client = app.test_client()
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b'name="csrf_token"' in response.data
