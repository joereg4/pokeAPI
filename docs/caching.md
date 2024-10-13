# Caching System

The Pokédex Web Application implements a two-level caching system to improve performance and reduce the number of API calls.

## High-Level Caching (Flask-Caching)

Located in `cache.py`, this system provides high-level caching for route responses.

This cache is initialized in the main application file (`app.py`) and is used to cache entire route responses. It's applied using decorators on route functions:

## Low-Level Caching (Shelve-based)

Located in `pokedex/cache.py`, this system implements low-level caching using Python's `shelve` module for Pokédex-specific data.

Key functions:

- `save`: Saves data to cache
- `load`: Loads data from cache
- `save_sprite` and `load_sprite`: Handle sprite caching

This caching system is used within the Pokédex module to cache individual pieces of data fetched from the PokéAPI.

Example usage:

```python
def get_data(endpoint, resource_id=None, subresource=None, **kwargs):
    force_lookup = kwargs.get("force_lookup", False)
if not force_lookup:
try:
return load(endpoint, resource_id, subresource)
except KeyError:
pass
data = call_api(endpoint, resource_id, subresource)
save(data, endpoint, resource_id, subresource)
return data
```