# Pokémon Data Migration Guide

This guide explains how to migrate Pokémon data from CSV files to PostgreSQL database.

## Prerequisites

1. Ensure you have PostgreSQL installed and running
2. Python 3.8 or higher
3. Required Python packages (listed in `requirements.txt`)
4. CSV data files in the `static/resources` directory

## Environment Setup

1. Create and activate a virtual environment:
   ```bash
   # On Mac/Linux
   python -m venv venv
   source venv/bin/activate

   # On Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   Create a `.env` file in the project root with the following variables:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/pokemon_db
   FLASK_APP=app.py
   FLASK_ENV=development
   ```

   Replace `username`, `password`, and `pokemon_db` with your PostgreSQL credentials.

## Running the Migration

1. Create the database:
   ```bash
   # On Mac/Linux
   createdb pokemon_db

   # On Windows (using psql)
   psql -U postgres
   CREATE DATABASE pokemon_db;
   \q
   ```

2. Run the migration script:
   ```bash
   python scripts/migrate_pokemon_data.py
   ```

   The script will:
   - Create all necessary tables
   - Import data from CSV files in the correct order
   - Verify data integrity
   - Report progress and any errors

## Verifying the Migration

1. Run the test suite:
   ```bash
   pytest tests/pokemon/test_migration.py -v
   ```

2. Check the database manually:
   ```bash
   psql pokemon_db
   
   # Some useful queries:
   SELECT count(*) FROM pokemon;
   SELECT count(*) FROM pokemon_species;
   SELECT count(*) FROM types;
   SELECT count(*) FROM abilities;
   SELECT count(*) FROM moves;
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Verify PostgreSQL is running
   - Check database credentials in `.env`
   - Ensure the database exists

2. **Missing CSV Files**
   - Verify all required CSV files are in `static/resources`
   - Check file permissions

3. **Data Integrity Errors**
   - The migration script follows a specific order to maintain referential integrity
   - If errors occur, the entire transaction will be rolled back
   - Check the error message for specific details

### Running on Ubuntu Server

1. Install system dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-venv python3-dev postgresql postgresql-contrib libpq-dev
   ```

2. Create PostgreSQL user and database:
   ```bash
   sudo -u postgres createuser --interactive
   sudo -u postgres createdb pokemon_db
   ```

3. Follow the same steps as above for environment setup and running the migration

## Support

If you encounter any issues:
1. Check the application logs
2. Review the PostgreSQL logs (`/var/log/postgresql/postgresql-*.log`)
3. Run the test suite with increased verbosity: `pytest -vv tests/pokemon/test_migration.py` 