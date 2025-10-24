import os
import logging
import csv
import glob
from flask import current_app
from pokedex.env import load_environment, get_env_variable

resources_dict = []

# Load environment variables using env.py
load_environment()


class Config:
    BASE_URL = get_env_variable("BASE_URL", "https://pokeapi.co/api/v2")
    SPRITE_URL = get_env_variable(
        "SPRITE_URL", "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"
    )
    POKEMON_PER_PAGE = int(get_env_variable("POKEMON_PER_PAGE", 60))
    ITEMS_PER_PAGE = int(get_env_variable("ITEMS_PER_PAGE", 50))
    WEBHOOK_SECRET = get_env_variable("WEBHOOK_SECRET")
    CACHE_TIMEOUT = int(get_env_variable("CACHE_TIMEOUT", 3600))  # Default 1 hour cache
    REDIS_URL = get_env_variable("REDIS_URL", "redis://localhost:6379/0")
    SPRITE_EXT = "png"
    # Define the valid sprite names to filter
    VALID_SPRITES = [
        "front_default",
        "back_default",
        "front_female",
        "back_female",
        "front_shiny",
        "back_shiny",
        "front_shiny_female",
        "back_shiny_female",
    ]
    # Define colors for Types
    TYPE_COLORS = {
        "normal": "#A8A77A",
        "fire": "#EE8130",
        "water": "#6390F0",
        "electric": "#F7D02C",
        "grass": "#7AC74C",
        "ice": "#96D9D6",
        "fighting": "#C22E28",
        "poison": "#A33EA1",
        "ground": "#E2BF65",
        "flying": "#A98FF3",
        "psychic": "#F95587",
        "bug": "#A6B91A",
        "rock": "#B6A136",
        "ghost": "#735797",
        "dragon": "#6F35FC",
        "dark": "#705746",
        "steel": "#B7B7CE",
        "fairy": "#D685AD",
    }
    ENDPOINTS = [
        "ability",
        "berry",
        "berry-firmness",
        "berry-flavor",
        "characteristic",
        "contest-effect",
        "contest-type",
        "egg-group",
        "encounter-condition",
        "encounter-condition-value",
        "encounter-method",
        "evolution-chain",
        "evolution-trigger",
        "gender",
        "generation",
        "growth-rate",
        "item",
        "item-attribute",
        "item-category",
        "item-fling-effect",
        "item-pocket",
        "language",
        "location",
        "location-area",
        "machine",
        "move",
        "move-ailment",
        "move-battle-style",
        "move-category",
        "move-damage-class",
        "move-learn-method",
        "move-target",
        "nature",
        "pal-park-area",
        "pokeathlon-stat",
        "pokedex",
        "pokemon",
        "pokemon-color",
        "pokemon-form",
        "pokemon-habitat",
        "pokemon-shape",
        "pokemon-species",
        "region",
        "stat",
        "super-contest-effect",
        "type",
        "version",
        "version-group",
    ]
    # Set the timeout for the TCG API to 2 seconds by default
    TCG_API_TIMEOUT = int(get_env_variable("TCG_API_TIMEOUT", 2))


def get_csv_file_paths():
    root_path = current_app.root_path
    # Find all CSV files in the static/resources directory
    csv_file_paths = glob.glob(os.path.join(root_path, "static", "resources", "*.csv"))
    return csv_file_paths


def load_resources():
    """
    Load resources from PostgreSQL database with Redis caching.
    
    Cache timeout: 60 minutes (3600 seconds)
    
    This function queries the Resource table in PostgreSQL and caches the results
    in Redis to reduce database load. The cache is shared across all app workers.
    
    Cache invalidation: Automatic after 60 minutes, or manually via invalidate_resource_cache()
    """
    global resources_dict
    
    # Import here to avoid circular imports
    from cache import cache
    from models.model import Resource
    
    # Try to load from cache first
    cached_resources = cache.get('all_resources')
    if cached_resources:
        resources_dict = cached_resources
        logging.info(f"Loaded {len(resources_dict)} resources from Redis cache")
        return
    
    # Cache miss - query database
    try:
        logging.info("Cache miss - querying PostgreSQL for resources")
        all_resources = Resource.query.all()
        
        # Clear and populate the resources_dict
        resources_dict = [
            {"name": resource.name, "type": resource.resource}
            for resource in all_resources
        ]
        
        # Store in cache for 60 minutes (3600 seconds)
        cache.set('all_resources', resources_dict, timeout=3600)
        logging.info(f"Loaded {len(resources_dict)} resources from database and cached for 60 minutes")
        
    except Exception as e:
        logging.error(f"Error loading resources from database: {e}")
        resources_dict = []


def invalidate_resource_cache():
    """
    Manually invalidate the resource cache.
    
    Call this function after updating resources in the database to immediately
    reflect changes in the JavaScript search without waiting for the 60-minute timeout.
    
    Example usage:
        # After adding/updating resources
        from pokedex.utils import invalidate_resource_cache
        invalidate_resource_cache()
        load_resources()  # Reload from database
    
    Returns:
        bool: True if cache was deleted, False otherwise
    """
    from cache import cache
    
    try:
        result = cache.delete('all_resources')
        logging.info("Resource cache invalidated successfully")
        return result
    except Exception as e:
        logging.error(f"Error invalidating resource cache: {e}")
        return False
