import csv
import os
import glob
from flask import current_app

resources_dict = []


def get_csv_file_paths():
    root_path = current_app.root_path
    # Find all CSV files in the static/resources directory
    csv_file_paths = glob.glob(os.path.join(root_path, 'static', 'resources', '*.csv'))
    return csv_file_paths


def load_resources():
    global resources_dict

    # Get all CSV file paths
    csv_file_paths = get_csv_file_paths()

    # Clear the existing dictionary to avoid residual data
    resources_dict.clear()

    for csv_file_path in csv_file_paths:
        try:
            with open(csv_file_path, mode='r') as file:
                reader = csv.reader(file)
                next(reader)  # Skip the header row

                # Populate the global resources_dict directly
                for row in reader:
                    resources_dict.append({"name": row[1], "type": row[0]})

        except FileNotFoundError:
            print(f"File not found: {csv_file_path}")
        except Exception as e:
            print(f"An error occurred while processing {csv_file_path}: {e}")

    if not resources_dict:
        resources_dict = []
