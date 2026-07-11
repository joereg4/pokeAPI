from flask import Blueprint
import os
import importlib

# Initialize a list to store all blueprints
blueprints = []

# Get the directory of the current file (which is the `routes` folder)
current_directory = os.path.dirname(os.path.abspath(__file__))

# Loop through each Python file in the `routes` directory. The listing is
# sorted because os.listdir order is OS-dependent, and blueprint registration
# order affects URL routing; sorting keeps it deterministic across platforms.
for filename in sorted(os.listdir(current_directory)):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = f"routes.{filename[:-3]}"
        module = importlib.import_module(module_name)

        # Find and add any blueprint in the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, Blueprint) and attr not in blueprints:
                blueprints.append(attr)
