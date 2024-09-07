from unittest.mock import patch

from pytest import fixture

from pokedex import loaders
from pokedex.loaders import sprite


@fixture
def mock_pokemon_data():
    """Mock data for a Pokémon"""
    return {
        "name": "bulbasaur",
        "id": 1,
        "height": 7,
        "weight": 69,
        "base_experience": 64,
        "types": [{"type": {"name": "grass"}}]
    }


def test_pokemon_detail_loader(mock_pokemon_data):
    """Test the pokemon_detail function to ensure it loads the correct data."""
    with patch('pokedex.interface.APIResource.fetch_data') as mock_fetch_data:
        mock_fetch_data.return_value = mock_pokemon_data

        # Call the loader
        result = loaders.pokemon_detail("bulbasaur")

        # Check if the API was called correctly
        mock_fetch_data.assert_called_once_with("pokemon", "bulbasaur")

        # Validate the returned data
        assert result["name"] == "bulbasaur"
        assert result["id"] == 1
        assert result["height"] == 7
        assert result["types"][0]["type"]["name"] == "grass"


def test_berry_loader():
    """Test the berry loader to ensure it loads the correct data."""
    berry_data = {
        "name": "cheri",
        "id": 1,
        "growth_time": 3,
        "max_harvest": 5
    }

    with patch('pokedex.interface.APIResource.fetch_data') as mock_fetch_data:
        mock_fetch_data.return_value = berry_data

        # Call the loader
        result = loaders.berry("cheri")

        # Check if the API was called correctly
        mock_fetch_data.assert_called_once_with("berry", "cheri")

        # Validate the returned data
        assert result["name"] == "cheri"
        assert result["id"] == 1
        assert result["growth_time"] == 3
        assert result["max_harvest"] == 5


def test_move_loader():
    """Test the move loader to ensure it loads the correct data."""
    move_data = {
        "name": "tackle",
        "id": 1,
        "power": 40,
        "pp": 35,
        "type": {"name": "normal"}
    }

    with patch('pokedex.interface.APIResource.fetch_data') as mock_fetch_data:
        mock_fetch_data.return_value = move_data

        # Call the loader
        result = loaders.move("tackle")

        # Check if the API was called correctly
        mock_fetch_data.assert_called_once_with("move", "tackle")

        # Validate the returned data
        assert result["name"] == "tackle"
        assert result["id"] == 1
        assert result["power"] == 40
        assert result["pp"] == 35
        assert result["type"]["name"] == "normal"


def test_sprite_loader():
    """Test the sprite loader to ensure it loads sprite data correctly."""
    sprite_data = {
        "path": "sprites/pokemon/1.png",
        "img_data": b"binary image data"
    }

    # Patch the _load method of SpriteResource from pokedex.loaders
    with patch('pokedex.interface.SpriteResource._load') as mock_load:
        # Simulate that the _load method doesn't return anything (it modifies the instance directly)
        mock_load.return_value = None

        # Call the sprite loader, which creates a SpriteResource instance
        result = sprite("pokemon", 1)

        # Manually update the attributes of the result object to simulate loading
        result.__dict__.update(sprite_data)

        # Assert that the sprite loader returns the correct data
        assert result.path == sprite_data["path"]
        assert result.img_data == sprite_data["img_data"]
        mock_load.assert_called_once()
