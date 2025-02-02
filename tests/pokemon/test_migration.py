import pytest
from models.model import db, Resource
from scripts.migrate_pokemon_data import migrate_data


@pytest.fixture
def app_with_db(app):
    """Fixture to create tables and clean up after tests."""
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_migrate_pokemon(app_with_db):
    """Test migration of Pokemon data."""
    with app_with_db.app_context():
        migrate_data(db.session, "pokemon.csv")
        pokemon = Resource.query.filter_by(resource="pokemon").all()
        assert len(pokemon) > 0

        # Check for some well-known Pokemon
        pokemon_names = [p.name for p in pokemon]
        assert "bulbasaur" in pokemon_names
        assert "charmander" in pokemon_names
        assert "squirtle" in pokemon_names

        # Verify summary field
        bulbasaur = Resource.query.filter_by(
            resource="pokemon", name="bulbasaur"
        ).first()
        assert bulbasaur.summary is not None
        assert "starter" in bulbasaur.summary.lower()


def test_migrate_abilities(app_with_db):
    """Test migration of Pokemon abilities."""
    with app_with_db.app_context():
        migrate_data(db.session, "ability.csv")
        abilities = Resource.query.filter_by(resource="ability").all()
        assert len(abilities) > 0

        # Check for some common abilities
        ability_names = [a.name for a in abilities]
        assert "stench" in ability_names
        assert "drizzle" in ability_names

        # Verify summary field
        stench = Resource.query.filter_by(resource="ability", name="stench").first()
        assert stench.summary is not None
        assert "flinch" in stench.summary.lower()


def test_data_integrity(app_with_db):
    """Test data integrity across all resources."""
    with app_with_db.app_context():
        csv_files = [
            "pokemon.csv",
            "ability.csv",
            "move.csv",
            "type.csv",
            "region.csv",
            "version.csv",
            "version-group.csv",
        ]

        for csv_file in csv_files:
            migrate_data(db.session, csv_file)

        # Verify each resource type has data
        resources = Resource.query.all()
        assert len(resources) > 0

        # Check required fields
        for resource in resources:
            assert resource.resource is not None
            assert resource.name is not None
