#!/usr/bin/env python3
"""
Update Pokemon TCG data from GitHub repository.
This script can be run periodically to keep the database up to date.
"""
import os
import sys
import json
import glob
import logging
import subprocess
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.model import db
from models.tcg_card import TcgCard
from app import create_app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_repository():
    """Update the pokemon-tcg-data repository."""
    repo_path = 'temp_tcg_data'
    
    if os.path.exists(repo_path):
        logger.info("Updating existing repository...")
        try:
            subprocess.run(['git', '-C', repo_path, 'pull'], check=True)
            logger.info("Repository updated successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to update repository: {e}")
            return False
    else:
        logger.info("Cloning repository...")
        try:
            subprocess.run(['git', 'clone', 'https://github.com/PokemonTCG/pokemon-tcg-data.git', repo_path], check=True)
            logger.info("Repository cloned successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clone repository: {e}")
            return False

def get_new_cards():
    """Find new cards that aren't in the database."""
    data_dir = 'temp_tcg_data/cards/en'
    if not os.path.exists(data_dir):
        logger.error(f"Data directory not found: {data_dir}")
        return []
    
    new_cards = []
    json_files = glob.glob(os.path.join(data_dir, '*.json'))
    
    for file_path in sorted(json_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                cards_data = json.load(f)
            
            set_name = os.path.basename(file_path).replace('.json', '')
            logger.info(f"Checking set: {set_name} ({len(cards_data)} cards)")
            
            for card_data in cards_data:
                card_id = card_data.get('id')
                if card_id:
                    # Check if card exists in database
                    existing_card = TcgCard.query.filter_by(id=card_id).first()
                    if not existing_card:
                        new_cards.append((card_data, set_name))
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            continue
    
    return new_cards

def import_new_cards(new_cards):
    """Import only new cards to avoid duplicates."""
    if not new_cards:
        logger.info("No new cards to import")
        return 0
    
    logger.info(f"Importing {len(new_cards)} new cards...")
    
    imported_count = 0
    
    for card_data, set_name in new_cards:
        try:
            from scripts.import_tcg_data import process_card_data
            card = process_card_data(card_data)
            if card:
                db.session.add(card)
                imported_count += 1
                
                # Commit in batches
                if imported_count % 100 == 0:
                    db.session.commit()
                    logger.info(f"Committed batch: {imported_count} cards imported")
                    
        except Exception as e:
            logger.error(f"Error importing card {card_data.get('id', 'unknown')}: {e}")
            continue
    
    # Final commit
    db.session.commit()
    logger.info(f"Import complete: {imported_count} new cards imported")
    
    return imported_count

def main():
    """Main update function."""
    app = create_app()
    
    with app.app_context():
        logger.info("Starting TCG data update...")
        
        # Step 1: Update repository
        if not update_repository():
            logger.error("Failed to update repository")
            return
        
        # Step 2: Find new cards
        new_cards = get_new_cards()
        
        # Step 3: Import new cards
        imported_count = import_new_cards(new_cards)
        
        # Step 4: Display statistics
        total_cards = TcgCard.query.count()
        pokemon_cards = TcgCard.query.filter_by(supertype='Pokémon').count()
        
        logger.info(f"Update complete!")
        logger.info(f"New cards imported: {imported_count}")
        logger.info(f"Total cards in database: {total_cards}")
        logger.info(f"Pokémon cards: {pokemon_cards}")

if __name__ == '__main__':
    main() 