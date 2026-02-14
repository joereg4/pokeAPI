# Utility Functions

The Pokédex Web Application includes several utility functions to support its operations. These are primarily located in `pokedex/utils.py`.

## Configuration

The `Config` class in `pokedex/utils.py` holds configuration values for the application:

```python
class Config:
    BASE_URL = get_env_variable('BASE_URL', 'https://pokeapi.co/api/v2')
    SPRITE_URL = get_env_variable('SPRITE_URL', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites')
    POKEMON_PER_PAGE = int(get_env_variable('POKEMON_PER_PAGE', 60))
    ITEMS_PER_PAGE = int(get_env_variable('ITEMS_PER_PAGE', 50))
    WEBHOOK_SECRET = get_env_variable('WEBHOOK_SECRET')
    CACHE_TIMEOUT = int(get_env_variable('CACHE_TIMEOUT', 300))
```

These configuration values are used throughout the application to maintain consistency and allow for easy adjustments.

## Search

The navbar autocomplete search is powered by the `/api/search` endpoint
(`routes/search.py`), which queries the PostgreSQL `resources` table directly.

- Results are ranked: prefix matches first, then substring matches.
- A short per-query cache (10 seconds) reduces DB load without hiding new data.
- A GIN trigram index (`pg_trgm`) on `resources.name` accelerates `ILIKE` queries.

No static file generation or in-memory resource list is required for search.

## Helper Functions

In `pokedex/helper.py`, there are several utility functions:

- `get_path`: Retrieves file paths for resources
- `get_summary`: Fetches summaries from CSV files
- `TYPE_COLORS`: A dictionary mapping Pokémon types to their corresponding colors

These utility functions and configurations play a crucial role in supporting the main functionality of the application, providing necessary data and settings for various operations.