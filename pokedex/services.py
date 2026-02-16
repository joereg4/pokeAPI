# services.py
# -*- coding: utf-8 -*-
"""Pokemon list building service.

Consolidates the duplicate logic that existed in:
  - helper.py:create_pokemon_list()    (12 callers, simple but no species ID artwork)
  - lists.py:PokemonList               (2 callers, species ID artwork but class-based)

Design rationale:
  - Single source of truth for building Pokemon list data from any API shape.
  - Uses species ID for artwork URLs (prevents 404s for form/variant Pokemon).
  - Falls back to the default variety when a species name doesn't match a Pokemon.
  - All output is serialized via serialize_pokemon_list_entry for template safety.
  - Pure data logic; no Flask request context needed.

Usage:
    from pokedex.services import build_pokemon_list

    # From a list of entries
    pokemon_list = build_pokemon_list([{"name": "pikachu"}, {"name": "eevee"}])

    # From an API response dict
    pokemon_list = build_pokemon_list(data)  # auto-detects key

    # From species (shows all varieties/forms)
    pokemon_list = build_species_variety_list(["pikachu", "charizard"])
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional, Union

from .interface import APIResource
from .species_resolver import resolve_species_id_from_data
from .sprite import get_sprite_url
from .serializers import serialize_pokemon_list_entry

logger = logging.getLogger(__name__)

# Keys that may hold Pokemon entries in API response dicts, checked in order.
_ENTRY_KEYS: tuple[str, ...] = (
    "results",
    "pokemon",
    "pokemon_species",
    "pokemon_entries",
    "pokemon_encounters",
    "held_by_pokemon",
    "learned_by_pokemon",
    "varieties",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_pokemon_list(
    data: Optional[Union[list[dict[str, Any]], dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Build a serialized Pokemon list from flexible input.

    Accepts:
      - A list of entries: [{"name": "pikachu"}, ...]
      - A dict with a recognized key (see _ENTRY_KEYS)
      - An empty/None value (returns [])

    Each entry is fetched via the API, artwork is resolved using species ID,
    and the result is serialized and sorted by ID.
    """
    entries = _extract_entries(data)
    pokemon_list = []

    for entry in entries:
        result = _process_entry(entry)
        if result is not None:
            pokemon_list.append(result)

    return sorted(
        pokemon_list,
        key=lambda x: x.get("id") if x.get("id") is not None else float("inf"),
    )


def build_species_variety_list(
    species_names: Iterable[str],
) -> list[dict[str, Any]]:
    """Build a Pokemon list by expanding species into their varieties.

    For each species name, fetches species data, then creates entries for
    every variety (e.g. Pikachu, Pikachu-Cosplay, etc.).  Used by the
    species detail page where showing all forms is important.

    Args:
        species_names: Iterable of species name strings.

    Returns:
        Sorted, serialized list of Pokemon entries.
    """
    pokemon_list = []

    for species_name in species_names:
        try:
            species_data = APIResource.fetch_data("pokemon-species", species_name)
            if not species_data:
                continue

            entry_number = _get_entry_number(species_data)

            for variety in species_data.get("varieties", []):
                variety_name = (variety.get("pokemon") or {}).get("name")
                if not variety_name:
                    continue

                try:
                    pokemon = APIResource.fetch_data("pokemon", variety_name)
                    if not pokemon:
                        continue

                    entry = _build_entry(variety_name, pokemon)
                    entry["entry_number"] = entry_number
                    pokemon_list.append(entry)
                except Exception as e:
                    logger.warning(
                        "Failed to fetch variety '%s' for species '%s': %s",
                        variety_name, species_name, e,
                    )
        except Exception as e:
            logger.error("Error fetching species data for '%s': %s", species_name, e)

    return sorted(
        pokemon_list,
        key=lambda x: x.get("id") if x.get("id") is not None else float("inf"),
    )


# ---------------------------------------------------------------------------
# Entry extraction
# ---------------------------------------------------------------------------


def _extract_entries(
    data: Optional[Union[list[dict[str, Any]], dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Extract Pokemon entries from various input formats.

    Returns a flat list of dicts, each expected to have a 'name' key
    (or a nested 'pokemon.name').
    """
    if data is None:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        for key in _ENTRY_KEYS:
            if key in data:
                raw = data[key]
                if key == "pokemon_entries":
                    return [e.get("pokemon_species", e) for e in raw]
                return raw

    logger.warning("Could not extract entries from data type %s", type(data).__name__)
    return []


def _extract_pokemon_name(entry: Any) -> Optional[str]:
    """Pull the Pokemon name from an entry dict.

    Handles:
      - {"name": "pikachu"}
      - {"pokemon": {"name": "pikachu"}}
    """
    if not isinstance(entry, dict):
        logger.warning("Invalid entry (not a dict): %s", entry)
        return None

    name = entry.get("name")
    if name:
        return name

    pokemon = entry.get("pokemon")
    if isinstance(pokemon, dict):
        return pokemon.get("name")

    return None


# ---------------------------------------------------------------------------
# Pokemon fetching with fallback
# ---------------------------------------------------------------------------


def _fetch_with_variety_fallback(name: str) -> Optional[dict[str, Any]]:
    """Fetch Pokemon data by name, falling back to the default variety.

    When a species name (e.g. 'wormadam') does not match a Pokemon endpoint,
    we look up the species data and find the default variety (e.g.
    'wormadam-plant').
    """
    pokemon = None

    try:
        pokemon = APIResource.fetch_data("pokemon", name)
    except ValueError:
        pokemon = None

    # If fetch succeeded but ID is None, the data is partial
    if pokemon and pokemon.get("id") is None:
        variety = _get_default_variety(name)
        if variety:
            return variety

    if pokemon:
        return pokemon

    # Pokemon not found -- try the default variety
    variety = _get_default_variety(name)
    if variety:
        return variety

    logger.warning("No data found for '%s' (including default variety)", name)
    return None


def _get_default_variety(species_name: str) -> Optional[dict[str, Any]]:
    """Fetch the default variety for a species.

    Returns the Pokemon dict for the default variety, or None.
    """
    try:
        species_data = APIResource.fetch_data("pokemon-species", species_name)
        if not species_data:
            return None

        for variety in species_data.get("varieties", []):
            if variety.get("is_default", False):
                variety_name = (variety.get("pokemon") or {}).get("name")
                if variety_name:
                    try:
                        return APIResource.fetch_data("pokemon", variety_name)
                    except Exception as e:
                        logger.warning(
                            "Failed to fetch default variety '%s': %s",
                            variety_name, e,
                        )
        return None
    except Exception as e:
        logger.warning(
            "Error fetching species for variety fallback '%s': %s",
            species_name, e,
        )
        return None


# ---------------------------------------------------------------------------
# Artwork & entry building
# ---------------------------------------------------------------------------


def _resolve_artwork_id(pokemon: dict[str, Any]) -> Optional[int]:
    """Determine the correct artwork ID for a Pokemon.

    Delegates to the centralized species_resolver which caches results
    in Redis.  Falls back to the Pokemon's own ID if resolution fails.
    """
    return resolve_species_id_from_data(pokemon)


def _get_artwork_url(pokemon: dict[str, Any]) -> Optional[str]:
    """Generate the artwork URL for a Pokemon using species ID resolution."""
    artwork_id = _resolve_artwork_id(pokemon)
    if artwork_id:
        try:
            return get_sprite_url(artwork_id, is_artwork=True)
        except Exception as e:
            logger.warning("Error getting artwork URL (id=%s): %s", artwork_id, e)
    return None


def _build_entry(name: str, pokemon: dict[str, Any]) -> dict[str, Any]:
    """Build a single serialized Pokemon list entry.

    Combines the Pokemon name with fetched data to create a template-safe
    dict for _pokemon_list.html.
    """
    official_artwork = _get_artwork_url(pokemon)

    return serialize_pokemon_list_entry({
        "name": name,
        "official_artwork": official_artwork,
        "id": pokemon.get("id"),
        "types": pokemon.get("types", []),
        "sprites": pokemon.get("sprites", {}),
        "is_variety": pokemon.get("name") != name,
        "variety_name": (
            pokemon.get("name")
            if pokemon.get("name") != name
            else None
        ),
    })


def _get_entry_number(species_data: dict[str, Any]) -> Optional[int]:
    """Extract the first entry number from species pokedex_numbers."""
    for entry in species_data.get("pokedex_numbers", []):
        if "entry_number" in entry:
            return entry["entry_number"]
    return None


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------


def _process_entry(entry: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Process a single entry into a serialized Pokemon list item.

    Returns None if the entry cannot be processed.
    """
    name = _extract_pokemon_name(entry)
    if not name:
        return None

    pokemon = _fetch_with_variety_fallback(name)
    if not pokemon:
        return None

    return _build_entry(name, pokemon)
