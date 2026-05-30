#!/usr/bin/env python3
"""Load static/resources/*.csv into resources when the table is empty."""

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from models.model import Resource, db
from scripts.migrate_pokemon_data import get_csv_files, migrate_data


def seed_resources_if_empty():
    app = create_app()
    with app.app_context():
        if db.session.query(Resource).count() > 0:
            print("Resources table already populated; skipping CSV seed.")
            return 0

        csv_files = get_csv_files()
        print(f"Seeding {len(csv_files)} CSV files from static/resources/ ...")
        for csv_file in csv_files:
            migrate_data(db.session, csv_file)
        print("CSV seed complete.")
        return 0


if __name__ == "__main__":
    raise SystemExit(seed_resources_if_empty())
