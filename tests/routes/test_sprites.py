# tests/routes/test_sprites.py
"""Tests for the sprite blueprint routes.

All sprite fetching is mocked -- no real filesystem or upstream calls.

Note: The sprite blueprint is registered at /sprite/ to avoid conflicts
with the generic utilities route handler.

After Phase 4b, missing sprites serve a placeholder image (200 with PNG)
instead of a JSON 404.  This prevents broken <img> tags on the frontend.
"""

import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os


@pytest.fixture
def sprite_file():
    """Create a temporary PNG file to use as a sprite."""
    # Minimal 1x1 transparent PNG
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    f.write(png_bytes)
    f.close()
    yield f.name
    os.unlink(f.name)


class TestArtworkRoute:
    def test_artwork_returns_image(self, client, sprite_file):
        sprite_data = {"img_data": b"bytes", "path": sprite_file}
        with patch("routes.sprite.get_sprite", return_value=sprite_data):
            response = client.get("/sprite/artwork/25")
        assert response.status_code == 200
        assert response.content_type == "image/png"
        assert "Cache-Control" in response.headers
        assert "max-age=31536000" in response.headers["Cache-Control"]

    def test_artwork_serves_placeholder_when_missing(self, client):
        """Missing artwork now serves placeholder PNG, not JSON 404."""
        with patch("routes.sprite.get_sprite", return_value=None):
            response = client.get("/sprite/artwork/99999")
        assert response.status_code == 200
        assert response.content_type == "image/png"
        # Placeholder uses shorter cache
        assert "max-age=3600" in response.headers["Cache-Control"]

    def test_artwork_serves_placeholder_when_no_path(self, client):
        with patch("routes.sprite.get_sprite", return_value={"img_data": b"bytes"}):
            response = client.get("/sprite/artwork/25")
        assert response.status_code == 200
        assert response.content_type == "image/png"

    def test_artwork_serves_placeholder_on_exception(self, client):
        """Exceptions during sprite fetch serve placeholder gracefully."""
        with patch("routes.sprite.get_sprite", side_effect=RuntimeError("boom")):
            response = client.get("/sprite/artwork/25")
        assert response.status_code == 200
        assert response.content_type == "image/png"

    def test_artwork_resolves_form_id(self, client, sprite_file):
        """Form IDs (>= 10000) are resolved to species ID before fetching."""
        sprite_data = {"img_data": b"bytes", "path": sprite_file}
        with patch("routes.sprite.resolve_species_id", return_value=386) as mock_resolve, \
             patch("routes.sprite.get_sprite", return_value=sprite_data) as mock_get:
            response = client.get("/sprite/artwork/10001")

        mock_resolve.assert_called_once_with("10001")
        mock_get.assert_called_once_with("pokemon", 386, other=True, official_artwork=True)
        assert response.status_code == 200


class TestDefaultSpriteRoute:
    def test_default_sprite_returns_image(self, client, sprite_file):
        sprite_data = {"img_data": b"bytes", "path": sprite_file}
        with patch("routes.sprite.get_sprite", return_value=sprite_data):
            response = client.get("/sprite/default/25")
        assert response.status_code == 200
        assert response.content_type == "image/png"

    def test_default_sprite_serves_placeholder_when_missing(self, client):
        with patch("routes.sprite.get_sprite", return_value=None):
            response = client.get("/sprite/default/99999")
        assert response.status_code == 200
        assert response.content_type == "image/png"


class TestSpecificSpriteRoute:
    def test_specific_sprite_returns_image(self, client, sprite_file):
        sprite_data = {"img_data": b"bytes", "path": sprite_file}
        with patch("routes.sprite.get_sprite", return_value=sprite_data):
            response = client.get("/sprite/25/front_shiny")
        assert response.status_code == 200

    def test_invalid_sprite_type_returns_400(self, client):
        response = client.get("/sprite/25/not_a_real_sprite_type")
        assert response.status_code == 400
        data = response.get_json()
        assert data["error"] == "Invalid sprite type"

    def test_specific_sprite_serves_placeholder_when_missing(self, client):
        with patch("routes.sprite.get_sprite", return_value=None):
            response = client.get("/sprite/25/front_default")
        assert response.status_code == 200
        assert response.content_type == "image/png"


class TestPlaceholderFallback:
    """Tests for the placeholder serving mechanism."""

    def test_placeholder_file_exists(self):
        """The placeholder image must exist in the expected location."""
        from routes.sprite import _PLACEHOLDER_PATH
        assert os.path.exists(_PLACEHOLDER_PATH), (
            f"Placeholder image not found at {_PLACEHOLDER_PATH}"
        )

    def test_placeholder_is_valid_png(self):
        """The placeholder must be a valid PNG file."""
        from routes.sprite import _PLACEHOLDER_PATH
        with open(_PLACEHOLDER_PATH, "rb") as f:
            header = f.read(8)
        # PNG magic bytes
        assert header[:4] == b"\x89PNG"

    def test_placeholder_returns_short_cache(self, client):
        """Placeholder responses use a short cache TTL (1 hour)."""
        with patch("routes.sprite.get_sprite", return_value=None):
            response = client.get("/sprite/artwork/99999")
        assert "max-age=3600" in response.headers.get("Cache-Control", "")

    def test_missing_placeholder_returns_json_404(self, client):
        """If placeholder file is also missing, fall back to JSON 404."""
        with patch("routes.sprite.get_sprite", return_value=None), \
             patch("routes.sprite._PLACEHOLDER_PATH", "/nonexistent/path.png"):
            response = client.get("/sprite/artwork/99999")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data


class TestSpriteUrlHelper:
    def test_artwork_url(self, app):
        """get_sprite_url with is_artwork=True should use the artwork route."""
        from routes.sprite import get_sprite_url
        with app.test_request_context():
            url = get_sprite_url(25, is_artwork=True)
        assert "/sprite/artwork/25" in url

    def test_default_url(self, app):
        from routes.sprite import get_sprite_url
        with app.test_request_context():
            url = get_sprite_url(25)
        assert "/sprite/default/25" in url

    def test_specific_sprite_url(self, app):
        from routes.sprite import get_sprite_url
        with app.test_request_context():
            url = get_sprite_url(25, sprite_type="front_shiny")
        assert "/sprite/25/front_shiny" in url
