import csv
import os
from flask import current_app

resources_dict = []


def get_csv_file_path():
    root_path = current_app.root_path
    csv_file_path = os.path.join(root_path, 'static', 'resources.csv')
    return csv_file_path


def load_resources():
    global resources_dict
    csv_file_path = get_csv_file_path()

    try:
        with open(csv_file_path, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row

            # Clear the existing dictionary to avoid residual data
            resources_dict.clear()

            # Populate the global resources_dict directly
            for row in reader:
                resources_dict.append({"name": row[1], "type": row[0]})

    except FileNotFoundError:
        print(f"File not found: {csv_file_path}")
        resources_dict = []
