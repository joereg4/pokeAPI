"""
Integration tests that hit the real PokéAPI.

These are NOT run in CI by default (deselected via -m "not integration"
in pytest.ini). Run them manually with:

    pytest tests/integration/ -m integration --timeout=30

Purpose:
  - Verify that the upstream PokéAPI contract hasn't changed
  - Validate that our URL building produces reachable endpoints
  - Smoke-test sprite resolution for standard and form Pokemon
"""

import pytest
import requests

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

POKEAPI_BASE = "https://pokeapi.co/api/v2"
SPRITE_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
TIMEOUT = 15  # seconds


def api_get(path):
    """GET a PokéAPI endpoint and return the response."""
    url = f"{POKEAPI_BASE}/{path}"
    return requests.get(url, timeout=TIMEOUT)


def sprite_get(path):
    """GET a sprite URL and return the response."""
    url = f"{SPRITE_BASE}/{path}"
    return requests.get(url, timeout=TIMEOUT)


# ---------------------------------------------------------------------------
# API endpoint contract tests
# ---------------------------------------------------------------------------

class TestPokeAPIEndpoints:
    """Verify that key PokéAPI endpoints return 200 with expected keys."""

    def test_pokemon_endpoint(self):
        resp = api_get("pokemon/1/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "bulbasaur"
        assert "sprites" in data
        assert "species" in data

    def test_pokemon_species_endpoint(self):
        resp = api_get("pokemon-species/1/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "bulbasaur"
        assert "evolution_chain" in data

    def test_ability_endpoint(self):
        resp = api_get("ability/1/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data

    def test_move_endpoint(self):
        resp = api_get("move/1/")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "type" in data

    def test_type_endpoint(self):
        resp = api_get("type/1/")
        assert resp.status_code == 200
        data = resp.json()
        assert "damage_relations" in data

    def test_berry_endpoint(self):
        resp = api_get("berry/1/")
        assert resp.status_code == 200

    def test_evolution_chain_endpoint(self):
        resp = api_get("evolution-chain/1/")
        assert resp.status_code == 200
        data = resp.json()
        assert "chain" in data

    def test_region_endpoint(self):
        resp = api_get("region/1/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "kanto"

    def test_item_endpoint(self):
        resp = api_get("item/1/")
        assert resp.status_code == 200

    def test_nonexistent_returns_404(self):
        resp = api_get("pokemon/this-does-not-exist-99999/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Sprite availability tests
# ---------------------------------------------------------------------------

class TestSpriteAvailability:
    """Verify that sprites are available upstream for common Pokemon."""

    def test_standard_front_sprite(self):
        """Pikachu's front sprite should exist."""
        resp = sprite_get("25.png")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/")

    def test_official_artwork(self):
        """Bulbasaur's official artwork should exist."""
        resp = sprite_get("other/official-artwork/1.png")
        assert resp.status_code == 200

    def test_shiny_sprite(self):
        resp = sprite_get("shiny/25.png")
        assert resp.status_code == 200

    def test_back_sprite(self):
        resp = sprite_get("back/25.png")
        assert resp.status_code == 200

    def test_form_pokemon_artwork_by_species_id(self):
        """Form Pokemon should use species ID, not form ID, for artwork.

        Deoxys (id=386) is a standard species. Its forms have different IDs
        (10001, 10002, 10003) but artwork exists at species ID 386.
        """
        resp = sprite_get("other/official-artwork/386.png")
        assert resp.status_code == 200

    def test_high_id_pokemon_artwork(self):
        """Newer Pokemon (Gen 9) should have artwork."""
        resp = sprite_get("other/official-artwork/906.png")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# URL building integration
# ---------------------------------------------------------------------------

class TestURLBuilding:
    """Verify that our URL building functions produce reachable URLs."""

    def test_api_url_build_produces_reachable_url(self):
        from pokedex.common import api_url_build
        url = api_url_build("pokemon", 25)
        resp = requests.get(url, timeout=TIMEOUT)
        assert resp.status_code == 200

    def test_sprite_url_build_produces_reachable_url(self):
        from pokedex.common import sprite_url_build
        url = sprite_url_build("pokemon", 25)
        resp = requests.get(url, timeout=TIMEOUT)
        assert resp.status_code == 200

    def test_artwork_url_build_produces_reachable_url(self):
        from pokedex.common import sprite_url_build
        url = sprite_url_build("pokemon", 25, other=True, official_artwork=True)
        resp = requests.get(url, timeout=TIMEOUT)
        assert resp.status_code == 200
