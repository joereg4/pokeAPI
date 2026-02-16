# pokedex/species_resolver.py
# -*- coding: utf-8 -*-
"""Species ID resolution with Redis caching.

Official artwork sprites on GitHub are keyed by SPECIES (National Dex) ID,
not the Pokemon form ID.  Form variants (e.g., Deoxys-Attack = 10001) have
IDs >= 10000 and don't have official artwork at those IDs.

This module provides a cached resolver:  pokemon_id -> species_id.

Architecture:
    Redis key:  "species_id:<pokemon_id>" -> "<species_id>"
    TTL:        30 days (species-to-form mappings never change)

    For IDs < 10000, the pokemon_id IS the species_id (no lookup needed).
    For IDs >= 10000, we fetch the Pokemon resource, extract the species
    URL, and cache the mapping in Redis.

Design rationale:
    Previously, species ID resolution was scattered across three places:
      - routes/sprite.py:_resolve_artwork_id  (raw ID, no cache)
      - pokedex/services.py:_resolve_artwork_id  (from pokemon dict)
      - routes/pokemon.py:get_pokemon  (inline extraction)
    Each made redundant API calls and none cached the result.  This module
    unifies them behind a single, Redis-cached function.

Usage:
    from pokedex.species_resolver import resolve_species_id

    # From a raw ID (sprite routes, template helpers)
    artwork_id = resolve_species_id(10001)  # -> 386 (Deoxys)

    # From already-fetched data (services, routes)
    artwork_id = resolve_species_id_from_data(pokemon_dict)
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional, Union

from .redis_client import redis_client

logger = logging.getLogger(__name__)

# Form variants have pokemon IDs >= 10000; IDs below this are species IDs.
_FORM_ID_THRESHOLD: int = 10000

# Redis key prefix and TTL for species_id mappings.
_REDIS_KEY_PREFIX: str = "species_id:"
_REDIS_TTL: int = 30 * 24 * 60 * 60  # 30 days


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_species_id(pokemon_id: Union[int, str]) -> Union[int, str]:
    """Resolve a Pokemon ID to its species (National Dex) ID.

    - Names pass through unchanged (string input).
    - IDs < 10000 are already species IDs, returned as-is.
    - IDs >= 10000 (forms) are looked up in Redis first, then the API.

    Args:
        pokemon_id: Pokemon ID (int, numeric string, or name string).

    Returns:
        int species ID for numeric inputs, or the original string for names.
    """
    try:
        numeric_id = int(pokemon_id)
    except (ValueError, TypeError):
        return pokemon_id  # name-based lookup, pass through

    if numeric_id < _FORM_ID_THRESHOLD:
        return numeric_id

    # Check Redis cache
    cached = _read_cache(numeric_id)
    if cached is not None:
        return cached

    # Cache miss — fetch from API
    species_id = _fetch_species_id(numeric_id)

    if species_id is not None:
        _write_cache(numeric_id, species_id)
        return species_id

    # Could not resolve — return original ID as fallback
    return numeric_id


def resolve_species_id_from_data(pokemon_data: dict[str, Any]) -> Optional[int]:
    """Extract species ID from an already-fetched Pokemon dict.

    More efficient than resolve_species_id() when you already have the data.
    Also opportunistically caches the mapping for future lookups.

    Args:
        pokemon_data: dict from APIResource.fetch_data("pokemon", ...).

    Returns:
        int species ID, or the Pokemon's own ID as fallback.
    """
    from .common import get_species_id_from_url

    species = pokemon_data.get("species") or {}
    species_url = species.get("url") if isinstance(species, dict) else None

    if species_url:
        try:
            species_id = get_species_id_from_url(species_url)
            pokemon_id = pokemon_data.get("id")

            # Cache form mappings opportunistically
            if pokemon_id and int(pokemon_id) >= _FORM_ID_THRESHOLD:
                _write_cache(int(pokemon_id), species_id)

            return species_id
        except (ValueError, TypeError):
            pass

    return pokemon_data.get("id")


def warm_cache(form_ids: Iterable[int]) -> dict[int, int]:
    """Pre-warm the Redis cache for a list of form Pokemon IDs.

    Intended to be called by deployment scripts (Phase 4c).

    Args:
        form_ids: Iterable of Pokemon IDs (typically >= 10000) to resolve
                  and cache.

    Returns:
        Mapping of {pokemon_id: species_id} for all resolved mappings.
    """
    results: dict[int, int] = {}
    for pokemon_id in form_ids:
        species_id = resolve_species_id(pokemon_id)
        if species_id != pokemon_id:
            results[pokemon_id] = species_id
            logger.info(
                "Warmed cache: pokemon %d -> species %d", pokemon_id, species_id
            )
    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _read_cache(numeric_id: int) -> Optional[int]:
    """Read a cached species_id from Redis. Returns int or None."""
    redis_key = f"{_REDIS_KEY_PREFIX}{numeric_id}"
    try:
        cached = redis_client.get(redis_key)
        if cached is not None:
            logger.debug("Cache hit: pokemon %d -> species %s", numeric_id, cached)
            return int(cached)
    except Exception as e:
        logger.debug("Redis read failed for species_id lookup: %s", e)
    return None


def _write_cache(numeric_id: int, species_id: int) -> None:
    """Write a species_id mapping to Redis."""
    redis_key = f"{_REDIS_KEY_PREFIX}{numeric_id}"
    try:
        redis_client.set(redis_key, str(species_id), ex=_REDIS_TTL)
        logger.debug("Cached: pokemon %d -> species %d", numeric_id, species_id)
    except Exception as e:
        logger.debug("Redis write failed for species_id cache: %s", e)


def _fetch_species_id(pokemon_id: int) -> Optional[int]:
    """Fetch species ID from the API for a form Pokemon.

    Makes a single API call to get the Pokemon resource, then extracts
    the species URL to determine the species ID.

    Returns:
        int species_id, or None if resolution failed.
    """
    from .interface import APIResource
    from .common import get_species_id_from_url

    try:
        data = APIResource.fetch_data("pokemon", pokemon_id)
        species = data.get("species") or {}
        species_url = species.get("url") if isinstance(species, dict) else None
        if species_url:
            return get_species_id_from_url(species_url)
    except Exception as e:
        logger.warning("Could not resolve species ID for form %d: %s", pokemon_id, e)

    return None
