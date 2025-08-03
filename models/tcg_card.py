# models/tcg_card.py
"""
Database model for Pokemon Trading Card Game cards.
Uses data from the pokemon-tcg-data GitHub repository.
"""
from sqlalchemy import Column, String, Text, Integer, JSON, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from models.model import db


class TcgCard(db.Model):
    """Model for Pokemon Trading Card Game cards."""

    __tablename__ = "tcg_cards"

    # Primary key
    id = Column(String(50), primary_key=True)  # e.g., "base1-1", "xy1-1"

    # Basic card information
    name = Column(String(100), nullable=False, index=True)
    supertype = Column(String(50))  # "Pokémon", "Trainer", "Energy"
    subtypes = Column(JSON)  # ["Basic"], ["Stage 2"], etc.
    level = Column(String(10))
    hp = Column(String(10))

    # Pokemon-specific fields
    types = Column(JSON)  # ["Lightning"], ["Fire", "Water"]
    evolves_from = Column(String(100))
    evolves_to = Column(JSON)  # ["Raichu"]

    # Card mechanics
    abilities = Column(JSON)  # Array of ability objects
    attacks = Column(JSON)  # Array of attack objects
    weaknesses = Column(JSON)  # Array of weakness objects
    resistances = Column(JSON)  # Array of resistance objects
    retreat_cost = Column(JSON)  # ["Colorless", "Colorless"]
    converted_retreat_cost = Column(Integer)

    # Set information
    set_id = Column(String(50))
    set_name = Column(String(100))
    set_series = Column(String(100))
    number = Column(String(20))

    # Metadata
    artist = Column(String(100))
    rarity = Column(String(50))
    flavor_text = Column(Text)
    national_pokedex_numbers = Column(JSON)  # [25] for Pikachu

    # Images
    image_small = Column(String(255))
    image_large = Column(String(255))

    # Legalities
    legalities = Column(JSON)  # {"unlimited": "Legal", "expanded": "Legal"}

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for common queries (avoid JSON column indexes in PostgreSQL)
    __table_args__ = (
        Index("idx_tcg_cards_name", "name"),
        Index("idx_tcg_cards_set", "set_id"),
    )

    def __repr__(self):
        return f"<TcgCard {self.id}: {self.name}>"

    def to_dict(self):
        """Convert card to dictionary format compatible with existing code."""
        return {
            "id": self.id,
            "name": self.name,
            "artist": self.artist or "Unknown",
            "large_image": self.image_large or "",
            "set_name": self.set_name or "Unknown Set",
        }

    @classmethod
    def find_by_name(cls, name):
        """Find cards by Pokemon name."""
        return cls.query.filter(cls.name.ilike(f"%{name}%")).all()

    @classmethod
    def find_by_pokedex_number(cls, number):
        """Find cards by national Pokedex number."""
        return cls.query.filter(cls.national_pokedex_numbers.contains([number])).all()

    @classmethod
    def find_by_type(cls, pokemon_type):
        """Find cards by Pokemon type."""
        return cls.query.filter(cls.types.contains([pokemon_type])).all()
