import pytest
import os
import tempfile
from pokedex import cache

@pytest.fixture
def temp_sprite_cache(monkeypatch):
    """Fixture to set up a temporary sprite cache directory."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        monkeypatch.setattr(cache, 'SPRITE_CACHE', tmpdirname)
        yield tmpdirname

def test_sprite_cache_functionality(temp_sprite_cache):
    """Test that sprite data is cached and retrieved properly."""
    sprite_data = b"mock sprite data"
    sprite_path = os.path.join(temp_sprite_cache, "pokemon", "1.png")
    sprite_info = {"path": sprite_path, "img_data": sprite_data}

    # Save sprite to cache
    cache.save_sprite(sprite_info, "pokemon", 1)

    # Load sprite from cache and verify it's the same
    cached_sprite = cache.load_sprite("pokemon", 1)
    assert cached_sprite["img_data"] == sprite_data

    # Attempt to load non-existent sprite and verify it raises an exception
    with pytest.raises(FileNotFoundError):
        cache.load_sprite("pokemon", 9999)
