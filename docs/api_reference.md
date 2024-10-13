# API Reference

The Pokédex Web Application interacts with the PokéAPI to fetch Pokémon data. This document provides an overview of the main API interaction points.

## Base URL

The base URL for the PokéAPI is defined in the `Config` class:

```python
BASE_URL = get_env_variable('BASE_URL', 'https://pokeapi.co/api/v2')
```

## Main API Endpoints

The application interacts with various endpoints of the PokéAPI, including:

- `/pokemon`: For Pokémon data
- `/location`: For location data
- `/ability`: For ability data
- `/item`: For item data
- `/move`: For move data
- `/type`: For type data
- `/berry`: For berry data

## API Resource Class

The `APIResource` class in `pokedex/interface.py` is the main interface for interacting with the API:

```python
class APIResource:
    def __init__(self, url):
        self.url = url

    def get(self):
        # Fetch data from the API
        response = http_get(self.url)
        return response.json()

    @classmethod
    def list(cls, endpoint):
        # Get a list of resources
        url = f"{BASE_URL}/{endpoint}"
        return cls(url).get()

    @classmethod
    def retrieve(cls, endpoint, id_or_name):
        # Retrieve a specific resource
        url = f"{BASE_URL}/{endpoint}/{id_or_name}"
        return cls(url).get()

    # Additional methods for specific API interactions
    @classmethod
    def get_pokemon(cls, id_or_name):
        return cls.retrieve('pokemon', id_or_name)

    @classmethod
    def get_location(cls, id_or_name):
        return cls.retrieve('location', id_or_name)
``` 

This class handles the fetching and caching of data from the API.

## API Functions

The `pokedex/api.py` file contains functions for making API calls:

```python
def http_get(url, params):
# ...
def call_api(endpoint, resource_id=None, subresource=None):
# ...
def get_data(endpoint, resource_id=None, subresource=None, kwargs):
# ...
```

These functions handle the actual HTTP requests to the API and manage caching of the responses.

## Sprite Handling

Sprite data is handled separately:

```python
def get_sprite_url(resource_id):
    """
    Generates the URL for a Pokémon's sprite image.

    Args:
        resource_id (int): The Pokémon's ID number.

    Returns:
        str: The URL of the sprite image.

    Note:
        This function constructs the URL based on the official PokéAPI sprite repository structure.
        It uses the 'official-artwork' sprites, which provide high-quality front-facing images of Pokémon.
    """
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{resource_id}.png"
```

This function is used to fetch sprite images from the PokéAPI sprite repository. It constructs the URL for a Pokémon's official artwork based on its ID number. 

Key points:
- The function takes a `resource_id` parameter, which is typically the Pokémon's National Pokédex number.
- It returns a string URL that points to the PNG image of the Pokémon's official artwork.
- This URL can be used directly in HTML `<img>` tags or for downloading the image.

Example usage:
```python
pokemon_id = 25  # Pikachu's ID
sprite_url = get_sprite_url(pokemon_id)
# sprite_url will be "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png"
```

Note that this function assumes the sprite is available in the repository. For very new Pokémon or special forms, you might need to implement fallback logic or error handling.

## Error Handling

API calls are wrapped in try-except blocks to handle potential errors, such as network issues or invalid responses. Errors are typically logged and may result in a 404 or 500 HTTP response depending on the nature of the error.

For detailed information on the PokéAPI endpoints and response formats, refer to the [official PokéAPI documentation](https://pokeapi.co/docs/v2).