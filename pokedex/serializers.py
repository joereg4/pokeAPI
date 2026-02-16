# serializers.py
# -*- coding: utf-8 -*-
"""Serializers that transform raw PokéAPI dicts into template-safe structures.

Each serializer guarantees that every field accessed by its corresponding
Jinja template exists with a sensible default.  They are defensive wrappers,
not data transformers -- they pass through existing data and fill in blanks.

Design rationale:
  - Templates crash with Jinja2 UndefinedError when a field is missing.
    These serializers eliminate that class of bug by ensuring structural safety.
  - Each function documents which template it protects and which fields
    are required vs optional.
  - Serializers are pure functions (no side effects, no I/O).  They accept
    a raw dict and return a new dict.

Usage:
    from pokedex.serializers import serialize_pokemon, serialize_move

    data = client.fetch("pokemon", "pikachu")
    safe_data = serialize_pokemon(data)
    return render_template("pokemon_detail.html", data=safe_data, ...)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_nested(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts/lists.  Returns *default* if any key
    along the path is missing or the wrong type.

    >>> _safe_nested({"a": {"b": 1}}, "a", "b")
    1
    >>> _safe_nested({"a": {}}, "a", "b", default="?")
    '?'
    """
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    return current


def _ensure_list(data: dict[str, Any], key: str) -> list[Any]:
    """Return data[key] if it is a list, otherwise return []."""
    val = data.get(key)
    return val if isinstance(val, list) else []


# ---------------------------------------------------------------------------
# Pokemon  (pokemon_detail.html)
# ---------------------------------------------------------------------------

def serialize_pokemon(data: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Ensure pokemon data has every field that pokemon_detail.html accesses.

    Required (no template conditional):
      data.name, data.species.name, data.stats[].stat.name, data.stats[].base_stat,
      data.abilities[].slot, data.abilities[].ability.name/url, data.sprites,
      data.id, data.moves

    Optional (template guards with {% if %}):
      data.base_experience, data.height, data.weight, data.is_default,
      data.order, data.held_items
    """
    if not data or not isinstance(data, dict):
        logger.warning("serialize_pokemon received empty or non-dict data")
        data = {}

    return {
        # Pass through ALL original keys so nothing is lost
        **data,
        # Guarantee required fields
        "name": data.get("name", "Unknown"),
        "id": data.get("id"),
        "species": data.get("species") or {"name": "unknown", "url": ""},
        "stats": _ensure_list(data, "stats"),
        "abilities": _ensure_list(data, "abilities"),
        "sprites": data.get("sprites") or {},
        "moves": _ensure_list(data, "moves"),
        "types": _ensure_list(data, "types"),
        # Optional fields with safe defaults
        "base_experience": data.get("base_experience"),
        "height": data.get("height"),
        "weight": data.get("weight"),
        "is_default": data.get("is_default"),
        "order": data.get("order"),
        "held_items": _ensure_list(data, "held_items"),
    }


# ---------------------------------------------------------------------------
# Pokemon Species  (pokemon_detail.html, conditional section)
# ---------------------------------------------------------------------------

def serialize_pokemon_species(data: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Ensure species data has every field that the species section of
    pokemon_detail.html accesses.

    All species fields are guarded by {% if species_data %} in the template,
    but once inside that block these nested fields are accessed directly.
    """
    if not data or not isinstance(data, dict):
        return None

    return {
        **data,
        "base_happiness": data.get("base_happiness"),
        "capture_rate": data.get("capture_rate"),
        "color": data.get("color") or {"name": "unknown"},
        "egg_groups": _ensure_list(data, "egg_groups"),
        "gender_rate": data.get("gender_rate"),
        "has_gender_differences": data.get("has_gender_differences", False),
        "hatch_counter": data.get("hatch_counter"),
        "habitat": data.get("habitat") or {"name": "unknown"},
        "is_baby": data.get("is_baby", False),
        "is_legendary": data.get("is_legendary", False),
        "is_mythical": data.get("is_mythical", False),
        "shape": data.get("shape") or {"name": "unknown"},
        "flavor_text_entries": _ensure_list(data, "flavor_text_entries"),
        "pokedex_numbers": _ensure_list(data, "pokedex_numbers"),
        "evolution_chain": data.get("evolution_chain") or {},
        "varieties": _ensure_list(data, "varieties"),
    }


# ---------------------------------------------------------------------------
# Move  (move_detail.html)
# ---------------------------------------------------------------------------

def serialize_move(data: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Ensure move data has every field that move_detail.html accesses.

    Required (no template conditional):
      data.name, data.type.name, data.pp, data.priority,
      data.damage_class.name, data.generation.name

    Optional (template guards):
      data.power, data.accuracy, data.effect_entries, data.flavor_text_entries,
      data.meta (and all sub-fields)
    """
    if not data or not isinstance(data, dict):
        logger.warning("serialize_move received empty or non-dict data")
        data = {}

    # Build safe meta object -- template checks individual fields but
    # accesses them as data.meta.X once inside the block
    raw_meta = data.get("meta")
    if raw_meta and isinstance(raw_meta, dict):
        safe_meta = {
            "crit_rate": raw_meta.get("crit_rate", 0),
            "drain": raw_meta.get("drain", 0),
            "healing": raw_meta.get("healing", 0),
            "min_hits": raw_meta.get("min_hits"),
            "max_hits": raw_meta.get("max_hits"),
            "min_turns": raw_meta.get("min_turns"),
            "max_turns": raw_meta.get("max_turns"),
            "ailment": raw_meta.get("ailment") or {"name": "none"},
            "ailment_chance": raw_meta.get("ailment_chance", 0),
            "flinch_chance": raw_meta.get("flinch_chance", 0),
            "stat_chance": raw_meta.get("stat_chance", 0),
        }
    else:
        safe_meta = None

    return {
        **data,
        "name": data.get("name", "Unknown"),
        "type": data.get("type") or {"name": "unknown"},
        "power": data.get("power"),
        "accuracy": data.get("accuracy"),
        "pp": data.get("pp", 0),
        "priority": data.get("priority", 0),
        "damage_class": data.get("damage_class") or {"name": "unknown"},
        "generation": data.get("generation") or {"name": "unknown"},
        "effect_entries": _ensure_list(data, "effect_entries"),
        "flavor_text_entries": _ensure_list(data, "flavor_text_entries"),
        "meta": safe_meta,
    }


# ---------------------------------------------------------------------------
# Item  (item_detail.html)
# ---------------------------------------------------------------------------

def serialize_item(data: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Ensure item data has every field that item_detail.html accesses.

    Required: data.name, data.cost, data.attributes
    Optional: data.sprites.default, data.category, data.effect_entries,
              data.fling_effect, data.fling_power, data.flavor_text_entries,
              data.game_indices
    """
    if not data or not isinstance(data, dict):
        logger.warning("serialize_item received empty or non-dict data")
        data = {}

    sprites = data.get("sprites")
    if not isinstance(sprites, dict):
        sprites = {"default": None}

    return {
        **data,
        "name": data.get("name", "Unknown"),
        "cost": data.get("cost", 0),
        "attributes": _ensure_list(data, "attributes"),
        "sprites": sprites,
        "category": data.get("category"),
        "effect_entries": _ensure_list(data, "effect_entries"),
        "fling_effect": data.get("fling_effect"),
        "fling_power": data.get("fling_power"),
        "flavor_text_entries": _ensure_list(data, "flavor_text_entries"),
        "game_indices": _ensure_list(data, "game_indices"),
        "baby_trigger_for": data.get("baby_trigger_for"),
    }


# ---------------------------------------------------------------------------
# Ability  (ability_detail.html)
# ---------------------------------------------------------------------------

def serialize_ability(data: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Ensure ability data has every field that ability_detail.html accesses.

    Required (accessed without guards):
      data.name, data.effect_entries, data['flavor_text_entries']

    The template accesses flavor_text_entries via bracket notation, so the
    key must exist even if it is an empty list.
    """
    if not data or not isinstance(data, dict):
        logger.warning("serialize_ability received empty or non-dict data")
        data = {}

    return {
        **data,
        "name": data.get("name", "Unknown"),
        "effect_entries": _ensure_list(data, "effect_entries"),
        "flavor_text_entries": _ensure_list(data, "flavor_text_entries"),
        "pokemon": _ensure_list(data, "pokemon"),
        "generation": data.get("generation") or {"name": "unknown"},
    }


# ---------------------------------------------------------------------------
# Pokemon list entry  (_pokemon_list.html)
# ---------------------------------------------------------------------------

def serialize_pokemon_list_entry(entry: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Ensure a single pokemon list entry has every field that
    _pokemon_list.html accesses.

    Required: entry.name, entry.types
    Optional: entry.official_artwork, entry.id, entry.entry_number,
              entry.is_variety, entry.variety_name
    """
    if not entry or not isinstance(entry, dict):
        return {"name": "Unknown", "types": [], "official_artwork": None,
                "id": None, "entry_number": None, "is_variety": False,
                "variety_name": None}

    return {
        **entry,
        "name": entry.get("name", "Unknown"),
        "types": _ensure_list(entry, "types"),
        "official_artwork": entry.get("official_artwork"),
        "id": entry.get("id"),
        "entry_number": entry.get("entry_number"),
        "is_variety": entry.get("is_variety", False),
        "variety_name": entry.get("variety_name"),
    }


def serialize_pokemon_list(entries: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Serialize a list of pokemon entries for _pokemon_list.html."""
    if not entries or not isinstance(entries, list):
        return []
    return [serialize_pokemon_list_entry(e) for e in entries]
