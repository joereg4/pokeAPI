# Pokédex Module

The Pokédex module is the core of the application, providing the main functionality for interacting with the PokéAPI and processing Pokémon data.

## API Interface (`pokedex/interface.py`)

This file contains classes for interacting with the PokéAPI:

### `APIResource` Class

The core API class used for accessing the bulk of the data. It uses a modified `__getattr__` function to serve the appropriate data.

Key features:
- Lazy loading of data
- Automatic conversion of API responses into appropriate Python objects
- Class method `fetch_data` for direct data retrieval

### `APIResourceList` Class

Used to access data corresponding to a category, rather than an individual reference. It provides information about all items in a category, such as all berries or all moves.

### `APIMetadata` Class

A helper class for smaller references, emulating a dictionary but with attribute lookup via the `.` operator.

### `SpriteResource` Class

Handles Pokémon sprites, providing methods to load and access sprite data.

## API Functions (`pokedex/api.py`)

Contains functions for making API calls and handling data:

- `_http_get`: Makes HTTP GET requests
- `_call_api`: Calls the PokéAPI
- `get_data`: Retrieves data with caching support
- `_call_sprite_api`: Handles sprite data retrieval

## Helper Functions (`pokedex/helper.py`)

Provides utility functions for the application:

- `get_path`: Retrieves file paths
- `get_summary`: Fetches summaries from CSV files
- Defines color mappings for Pokémon types

These components work together to provide a robust interface for fetching, processing, and caching Pokémon data from the PokéAPI.