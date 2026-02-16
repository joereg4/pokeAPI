"""
Tests for the sprite blueprint routes.

All sprite fetching is mocked -- no real filesystem or upstream calls.

Note: The sprite blueprint is registered at /sprite/ to avoid conflicts
with the generic utilities route handler.
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

    def test_artwork_returns_404_when_missing(self, client):
        with patch("routes.sprite.get_sprite", return_value=None):
            response = client.get("/sprite/artwork/99999")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data

    def test_artwork_returns_404_when_no_path(self, client):
        with patch("routes.sprite.get_sprite", return_value={"img_data": b"bytes"}):
            response = client.get("/sprite/artwork/25")
        assert response.status_code == 404


class TestDefaultSpriteRoute:
    def test_default_sprite_returns_image(self, client, sprite_file):
        sprite_data = {"img_data": b"bytes", "path": sprite_file}
        with patch("routes.sprite.get_sprite", return_value=sprite_data):
            response = client.get("/sprite/default/25")
        assert response.status_code == 200
        assert response.content_type == "image/png"

    def test_default_sprite_returns_404_when_missing(self, client):
        with patch("routes.sprite.get_sprite", return_value=None):
            response = client.get("/sprite/default/99999")
        assert response.status_code == 404


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

    def test_specific_sprite_returns_404_when_missing(self, client):
        with patch("routes.sprite.get_sprite", return_value=None):
            response = client.get("/sprite/25/front_default")
        assert response.status_code == 404


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
