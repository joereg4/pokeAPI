"""
Central interface for all summary generators.
This module provides a unified way to access all summary generator functions.
"""

from .pokemon import generate_pokemon_summary
from .moves import generate_move_summary
from .abilities import generate_ability_summary
from .items import generate_item_summary
from .types import generate_type_summary


def generate_summary(
    resource_type,
    resource_name,
    base_summary="",
    custom_instructions="",
    max_tokens=2000,
):
    """
    Generate a summary for a resource based on its type.
    This function selects the appropriate generator based on the resource type.

    Args:
        resource_type (str): The type of resource ('pokemon', 'move', 'ability', 'item', 'type')
        resource_name (str): The name of the resource
        base_summary (str, optional): An existing summary to improve. Defaults to "".
        custom_instructions (str, optional): Custom instructions for the AI. Defaults to "".
        max_tokens (int, optional): Maximum tokens for the AI response. Defaults to 2000.

    Returns:
        str: The generated summary
    """
    # Map resource types to their respective generator functions
    generators = {
        "pokemon": generate_pokemon_summary,
        "move": generate_move_summary,
        "ability": generate_ability_summary,
        "item": generate_item_summary,
        "type": generate_type_summary,
    }

    # Select the appropriate generator based on resource type
    if resource_type in generators:
        return generators[resource_type](
            resource_name, base_summary, custom_instructions, max_tokens
        )
    else:
        # Generic template for unsupported resource types
        return f"Summary for {resource_name} ({resource_type}). This resource type doesn't have a specific template yet."
