# pokedex/types.py
# -*- coding: utf-8 -*-
"""TypedDict models for PokeAPI response structures.

These types document the shape of data flowing through the application --
from raw API responses through serializers to templates.  They are used
for static analysis (mypy/pyright) and IDE auto-completion, but impose
zero runtime cost because TypedDict is erased at runtime.

Design rationale:
  - TypedDict was chosen over Pydantic/dataclasses because the codebase
    already passes plain dicts everywhere.  Introducing dataclass instances
    would require changing every dict access (d["key"]) to attribute access
    (d.key) across 70+ templates and 16 route files.
  - TypedDict gives us type safety and documentation without changing
    any runtime behaviour -- a dict satisfying the TypedDict shape is
    still just a dict.

Usage:
    from pokedex.types import PokemonData, SpriteDataDict

    def serialize_pokemon(data: PokemonData) -> PokemonData: ...
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict

try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired


# ---------------------------------------------------------------------------
# Shared / nested structures
# ---------------------------------------------------------------------------


class NamedResource(TypedDict):
    """A minimal {name, url} reference used throughout the API."""

    name: str
    url: str


class PaginatedList(TypedDict):
    """Standard paginated list response from PokeAPI."""

    count: int
    next: Optional[str]
    previous: Optional[str]
    results: list[NamedResource]


# ---------------------------------------------------------------------------
# Sprite data (filesystem cache)
# ---------------------------------------------------------------------------


class SpriteDataDict(TypedDict):
    """Sprite image data as returned by api.get_sprite()."""

    img_data: bytes
    path: str


# ---------------------------------------------------------------------------
# Pokemon
# ---------------------------------------------------------------------------


class PokemonType(TypedDict):
    """A single type slot on a Pokemon."""

    slot: int
    type: NamedResource


class PokemonAbility(TypedDict):
    """A single ability slot on a Pokemon."""

    ability: NamedResource
    is_hidden: bool
    slot: int


class PokemonStat(TypedDict):
    """A single stat entry on a Pokemon."""

    base_stat: int
    effort: int
    stat: NamedResource


class PokemonMove(TypedDict):
    """A single move entry on a Pokemon (simplified)."""

    move: NamedResource


class PokemonData(TypedDict, total=False):
    """Pokemon resource (/api/v2/pokemon/{id}).

    All keys are technically optional in total=False mode so that partial
    dicts (e.g. from serializers) are still valid instances of this type.
    """

    id: int
    name: str
    species: NamedResource
    types: list[PokemonType]
    abilities: list[PokemonAbility]
    stats: list[PokemonStat]
    moves: list[PokemonMove]
    sprites: dict[str, Any]
    base_experience: Optional[int]
    height: Optional[int]
    weight: Optional[int]
    is_default: bool
    order: int
    held_items: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Pokemon Species
# ---------------------------------------------------------------------------


class PokemonSpeciesData(TypedDict, total=False):
    """Pokemon Species resource (/api/v2/pokemon-species/{id})."""

    id: int
    name: str
    base_happiness: Optional[int]
    capture_rate: int
    color: NamedResource
    egg_groups: list[NamedResource]
    gender_rate: int
    has_gender_differences: bool
    hatch_counter: int
    habitat: Optional[NamedResource]
    is_baby: bool
    is_legendary: bool
    is_mythical: bool
    shape: Optional[NamedResource]
    flavor_text_entries: list[dict[str, Any]]
    pokedex_numbers: list[dict[str, Any]]
    evolution_chain: dict[str, Any]
    varieties: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Move
# ---------------------------------------------------------------------------


class MoveData(TypedDict, total=False):
    """Move resource (/api/v2/move/{id})."""

    id: int
    name: str
    type: NamedResource
    power: Optional[int]
    accuracy: Optional[int]
    pp: int
    priority: int
    damage_class: NamedResource
    generation: NamedResource
    effect_entries: list[dict[str, Any]]
    flavor_text_entries: list[dict[str, Any]]
    meta: Optional[dict[str, Any]]


# ---------------------------------------------------------------------------
# Item
# ---------------------------------------------------------------------------


class ItemData(TypedDict, total=False):
    """Item resource (/api/v2/item/{id})."""

    id: int
    name: str
    cost: int
    attributes: list[NamedResource]
    sprites: dict[str, Any]
    category: Optional[NamedResource]
    effect_entries: list[dict[str, Any]]
    fling_effect: Optional[NamedResource]
    fling_power: Optional[int]
    flavor_text_entries: list[dict[str, Any]]
    game_indices: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Ability
# ---------------------------------------------------------------------------


class AbilityData(TypedDict, total=False):
    """Ability resource (/api/v2/ability/{id})."""

    id: int
    name: str
    effect_entries: list[dict[str, Any]]
    flavor_text_entries: list[dict[str, Any]]
    pokemon: list[dict[str, Any]]
    generation: NamedResource


# ---------------------------------------------------------------------------
# Pokemon list entry (serialized for templates)
# ---------------------------------------------------------------------------


class PokemonListEntry(TypedDict, total=False):
    """A single entry in a serialized Pokemon list for templates."""

    name: str
    id: Optional[int]
    types: list[PokemonType]
    official_artwork: Optional[str]
    entry_number: Optional[int]
    is_variety: bool
    variety_name: Optional[str]
    sprites: dict[str, Any]
