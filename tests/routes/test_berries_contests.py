"""
Tests for the berries_contests blueprint routes.

All external API calls are mocked.
"""

import pytest


@pytest.fixture(autouse=True)
def setup_mocks(mock_api, mock_requests):
    """Register mock responses for berry and contest endpoints."""
    # Berry -- template needs: name, firmness.name, growth_time, max_harvest,
    #   size, smoothness, soil_dryness, natural_gift_power, natural_gift_type.name,
    #   item.name, flavors[].flavor.name, flavors[].potency
    mock_api.register("berry", 1, {
        "name": "cheri", "id": 1, "growth_time": 3, "max_harvest": 5,
        "size": 20, "smoothness": 25, "soil_dryness": 15,
        "natural_gift_power": 60,
        "natural_gift_type": {"name": "fire", "url": "https://pokeapi.co/api/v2/type/10/"},
        "item": {"name": "cheri-berry", "url": "https://pokeapi.co/api/v2/item/126/"},
        "firmness": {"name": "soft", "url": "https://pokeapi.co/api/v2/berry-firmness/2/"},
        "flavors": [{"potency": 10, "flavor": {"name": "spicy", "url": "https://pokeapi.co/api/v2/berry-flavor/1/"}}],
    })
    mock_api.register("berry", "cheri", mock_api.responses[("berry", "1")])

    # Berry firmness
    mock_api.register("berry-firmness", 1, {
        "name": "very-soft", "id": 1,
        "berries": [{"name": "pecha", "url": "https://pokeapi.co/api/v2/berry/3/"}],
    })
    mock_api.register("berry-firmness", "very-soft", mock_api.responses[("berry-firmness", "1")])

    # Berry flavor -- template needs: name, contest_type.name, berries[].berry.name
    mock_api.register("berry-flavor", 1, {
        "name": "spicy", "id": 1,
        "contest_type": {"name": "cool", "url": "https://pokeapi.co/api/v2/contest-type/1/"},
        "berries": [{"potency": 10, "berry": {"name": "cheri", "url": "https://pokeapi.co/api/v2/berry/1/"}}],
    })
    mock_api.register("berry-flavor", "spicy", mock_api.responses[("berry-flavor", "1")])

    # Contest type
    mock_api.register("contest-type", 1, {
        "name": "cool", "id": 1,
        "berry_flavor": {"name": "spicy"},
        "names": [{"name": "Cool", "color": "red", "language": {"name": "en"}}],
    })
    mock_api.register("contest-type", "cool", mock_api.responses[("contest-type", "1")])

    # Contest effect
    mock_api.register("contest-effect", 1, {
        "id": 1, "appeal": 4, "jam": 0,
        "effect_entries": [{"effect": "A highly appealing move.", "language": {"name": "en"}}],
        "flavor_text_entries": [{"flavor_text": "A highly appealing move.", "language": {"name": "en"}}],
    })

    # List endpoints
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.json.return_value = {
        "results": [{"name": "cheri"}], "count": 1, "next": None,
    }


class TestBerryRoutes:
    def test_berry_list(self, client):
        response = client.get("/berry/")
        assert response.status_code == 200

    def test_berry_detail_by_id(self, client):
        response = client.get("/berry/1")
        assert response.status_code == 200
        assert b"cheri" in response.data

    def test_berry_detail_by_name(self, client):
        response = client.get("/berry/cheri")
        assert response.status_code == 200

    def test_berry_not_found(self, client):
        response = client.get("/berry/nonexistent")
        assert response.status_code in (400, 404)


class TestBerryFirmnessRoutes:
    def test_firmness_detail_by_id(self, client):
        response = client.get("/berry-firmness/1")
        assert response.status_code == 200

    def test_firmness_not_found(self, client):
        response = client.get("/berry-firmness/nonexistent")
        assert response.status_code in (400, 404)


class TestBerryFlavorRoutes:
    def test_flavor_detail_by_id(self, client):
        response = client.get("/berry-flavor/1")
        assert response.status_code == 200

    def test_flavor_not_found(self, client):
        response = client.get("/berry-flavor/nonexistent")
        assert response.status_code in (400, 404)


class TestContestRoutes:
    def test_contest_type_by_id(self, client):
        response = client.get("/contest-type/1")
        assert response.status_code == 200

    def test_contest_effect_by_id(self, client):
        response = client.get("/contest-effect/1")
        assert response.status_code == 200
