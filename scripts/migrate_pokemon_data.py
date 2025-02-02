import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from models.model import db, Resource
from app import create_app


def get_csv_files():
    """Get all CSV files from the static/resources directory."""
    resources_dir = os.path.join("static", "resources")
    return [f for f in os.listdir(resources_dir) if f.endswith(".csv")]


def load_csv_data(filename):
    """Load data from a CSV file in the static/resources directory."""
    csv_path = os.path.join("static", "resources", filename)
    df = pd.read_csv(csv_path)

    # Verify required columns exist
    required_columns = ["resource", "name", "summary"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns in {filename}: {missing_columns}")

    # Check for null values
    null_counts = df[required_columns].isnull().sum()
    if null_counts.any():
        print(f"Warning: Found null values in {filename}:")
        for col, count in null_counts.items():
            if count > 0:
                print(f"  - {col}: {count} null values")

    return df


def migrate_data(session, csv_filename):
    """Migrate data from CSV to database."""
    print(f"Migrating data from {csv_filename}...")
    df = load_csv_data(csv_filename)

    success_count = 0
    duplicate_count = 0
    max_summary_length = 0

    for _, row in df.iterrows():
        # Check summary length
        if len(str(row["summary"])) > max_summary_length:
            max_summary_length = len(str(row["summary"]))

        resource = Resource(
            resource=row["resource"], name=row["name"], summary=row["summary"]
        )
        try:
            session.add(resource)
            session.commit()
            success_count += 1
        except Exception as e:
            session.rollback()
            if "uix_resource_name" in str(e):
                duplicate_count += 1
            else:
                print(f"Error migrating record: {str(e)}")
                raise

    print(f"Successfully migrated {success_count} records from {csv_filename}")
    if duplicate_count > 0:
        print(f"Skipped {duplicate_count} duplicate records from {csv_filename}")
    print(f"Longest summary in {csv_filename}: {max_summary_length} characters")

    # Verify the data was stored correctly
    if success_count > 0:
        # Check a random record
        sample = df.sample(n=1).iloc[0]
        db_record = (
            session.query(Resource)
            .filter_by(resource=sample["resource"], name=sample["name"])
            .first()
        )
        if db_record and len(str(db_record.summary)) != len(str(sample["summary"])):
            print(f"Warning: Summary length mismatch in {csv_filename}")
            print(f"  CSV length: {len(str(sample['summary']))}")
            print(f"  DB length: {len(str(db_record.summary))}")


def main():
    """Main migration function."""
    load_dotenv()
    app = create_app()

    with app.app_context():
        # Create all tables
        db.create_all()

        try:
            # Get all CSV files from the directory
            csv_files = get_csv_files()
            print(
                f"Found {len(csv_files)} CSV files to process: {', '.join(csv_files)}"
            )

            for csv_file in csv_files:
                migrate_data(db.session, csv_file)

            print("Migration completed successfully!")

        except Exception as e:
            print(f"Error during migration: {str(e)}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    main()
