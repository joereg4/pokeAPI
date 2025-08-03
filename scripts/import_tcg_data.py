#!/usr/bin/env python3
"""
Import Pokemon TCG data from the pokemon-tcg-data GitHub repository.
This script populates the local database with card data to avoid API dependencies.
"""
import os
import sys
import json
import glob
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.model import db
from models.tcg_card import TcgCard
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def process_card_data(card_data, set_info=None):
    """Process a single card from the JSON data."""
    try:
        # Extract set information from the card or use provided set_info
        card_set = card_data.get("set", set_info or {})

        # Handle images
        images = card_data.get("images", {})

        # Create TcgCard instance
        card = TcgCard(
            id=card_data.get("id"),
            name=card_data.get("name"),
            supertype=card_data.get("supertype"),
            subtypes=card_data.get("subtypes"),
            level=card_data.get("level"),
            hp=card_data.get("hp"),
            types=card_data.get("types"),
            evolves_from=card_data.get("evolvesFrom"),
            evolves_to=card_data.get("evolvesTo"),
            abilities=card_data.get("abilities"),
            attacks=card_data.get("attacks"),
            weaknesses=card_data.get("weaknesses"),
            resistances=card_data.get("resistances"),
            retreat_cost=card_data.get("retreatCost"),
            converted_retreat_cost=card_data.get("convertedRetreatCost"),
            set_id=card_set.get("id"),
            set_name=card_set.get("name"),
            set_series=card_set.get("series"),
            number=card_data.get("number"),
            artist=card_data.get("artist"),
            rarity=card_data.get("rarity"),
            flavor_text=card_data.get("flavorText"),
            national_pokedex_numbers=card_data.get("nationalPokedexNumbers"),
            image_small=images.get("small"),
            image_large=images.get("large"),
            legalities=card_data.get("legalities"),
        )

        return card

    except Exception as e:
        logger.error(f"Error processing card {card_data.get('id', 'unknown')}: {e}")
        return None


def import_set_file(file_path):
    """Import cards from a single JSON set file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            cards_data = json.load(f)

        set_name = os.path.basename(file_path).replace(".json", "")
        logger.info(f"Importing set: {set_name} ({len(cards_data)} cards)")

        imported_count = 0
        skipped_count = 0

        for card_data in cards_data:
            try:
                # Check if card already exists
                existing_card = TcgCard.query.filter_by(id=card_data.get("id")).first()
                if existing_card:
                    skipped_count += 1
                    continue

                # Process and add new card
                card = process_card_data(card_data)
                if card:
                    db.session.add(card)
                    imported_count += 1

                    # Commit in batches to avoid memory issues
                    if imported_count % 100 == 0:
                        db.session.commit()
                        logger.info(f"Committed batch: {imported_count} cards imported")

            except Exception as e:
                logger.error(f"Error importing card from {set_name}: {e}")
                continue

        # Final commit for remaining cards
        db.session.commit()
        logger.info(
            f"Set {set_name} complete: {imported_count} imported, {skipped_count} skipped"
        )

        return imported_count, skipped_count

    except Exception as e:
        logger.error(f"Error importing file {file_path}: {e}")
        db.session.rollback()
        return 0, 0


def main():
    """Main import function."""
    # Create Flask app context
    app = create_app()

    with app.app_context():
        # Tables should already exist from migrations

        # Find the data directory
        data_dir = "temp_tcg_data/cards/en"
        if not os.path.exists(data_dir):
            logger.error(f"Data directory not found: {data_dir}")
            logger.info(
                "Please run: git clone https://github.com/PokemonTCG/pokemon-tcg-data.git temp_tcg_data"
            )
            return

        # Get all JSON files
        json_files = glob.glob(os.path.join(data_dir, "*.json"))
        if not json_files:
            logger.error("No JSON files found in data directory")
            return

        logger.info(f"Found {len(json_files)} set files to import")

        total_imported = 0
        total_skipped = 0

        # Import each set file
        for file_path in sorted(json_files):
            imported, skipped = import_set_file(file_path)
            total_imported += imported
            total_skipped += skipped

        logger.info(f"Import complete!")
        logger.info(f"Total cards imported: {total_imported}")
        logger.info(f"Total cards skipped (already existed): {total_skipped}")

        # Display some statistics
        total_cards = TcgCard.query.count()
        pokemon_cards = TcgCard.query.filter_by(supertype="Pokémon").count()
        unique_names = db.session.query(TcgCard.name).distinct().count()

        logger.info(f"Database statistics:")
        logger.info(f"  Total cards: {total_cards}")
        logger.info(f"  Pokémon cards: {pokemon_cards}")
        logger.info(f"  Unique card names: {unique_names}")


if __name__ == "__main__":
    main()
