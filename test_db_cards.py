#!/usr/bin/env python3
"""
Test the database-powered get_pokemon_cards function
"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to the Python path
sys.path.append(".")


def test_database_cards():
    """Test getting Pokemon cards from the database"""
    from app import create_app
    from pokedex.helper import get_pokemon_cards

    # Create Flask app context
    app = create_app()

    with app.app_context():
        print("Testing database-powered get_pokemon_cards function...")

        # Test with different Pokemon
        test_names = [
            "pikachu",
            "charizard",
            "blastoise",
            "venusaur",
            "unknown_pokemon",
        ]

        for name in test_names:
            print(f"\n=== Testing with '{name}' ===")
            cards = get_pokemon_cards(name)
            print(f"Found {len(cards)} cards")

            if cards:
                print("First few cards:")
                for i, card in enumerate(cards[:3]):  # Show first 3 cards
                    print(
                        f"  {i+1}. {card['name']} ({card['id']}) - Set: {card['set_name']}"
                    )
            else:
                print("No cards found")


if __name__ == "__main__":
    test_database_cards()
