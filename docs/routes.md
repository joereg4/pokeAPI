# Route Blueprints

The Pokédex Web Application uses Flask blueprints to organize its routes. Each blueprint handles a specific category of data:

## Pokemon Blueprint (`routes/pokemon.py`)

Handles routes related to Pokémon data, including:
- Main index page
- Pokédex listings
- Individual Pokémon details
- Pokémon color information

## Locations and Regions Blueprint (`routes/locations_regions.py`)

Manages routes for location and region data:
- Location listings and details
- Region listings and details
- Nature information
- Pal Park areas

## Abilities, Moves, and Items Blueprint (`routes/abilities_moves_items.py`)

Handles routes for abilities, moves, and items:
- Ability listings and details
- Move listings and details
- Item listings and details
- Item attributes and categories

## Characteristics and Stats Blueprint (`routes/characteristics_stats.py`)

Manages routes for Pokémon characteristics and stats:
- Characteristic listings and details
- Pokéathlon stat information
- General stat information

## Evolution and Growth Blueprint (`routes/evolution_growth.py`)

Handles routes related to Pokémon evolution:
- Evolution chain information

## Berries and Contests Blueprint (`routes/berries_contests.py`)

Manages routes for berry and contest information:
- Berry listings and details

## Breeding Blueprint (`routes/breeding.py`)

Handles routes related to Pokémon breeding (implementation details not provided in the snippets).

## Utilities Blueprint (`routes/utilities.py`)

Provides utility routes and functions:
- Generic endpoint data retrieval
- Error handling for various endpoints

Each blueprint is designed to handle a specific aspect of the Pokémon data, allowing for a modular and organized approach to route management.