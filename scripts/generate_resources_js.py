#!/usr/bin/env python3
"""
Generate static resources.js file for CSP compliance.
This script creates a static JavaScript file with all resources data.
"""

import os
import sys
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from pokedex.utils import load_resources, resources_dict

def generate_resources_js():
    """Generate the static resources.js file."""
    app = create_app()
    
    with app.app_context():
        # Use the same method as the context processor
        from routes.pokemon import inject_resources
        context_data = inject_resources()
        resources_json = context_data['resources_json']
        
        # Create the JavaScript content
        js_content = f"const resources = {resources_json};"
        
        # Write to static file
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'js')
        os.makedirs(static_dir, exist_ok=True)
        
        resources_file = os.path.join(static_dir, 'resources.js')
        with open(resources_file, 'w') as f:
            f.write(js_content)
        
        # Parse the JSON to get the count
        resources_data = json.loads(resources_json)
        print(f"Generated {resources_file} with {len(resources_data)} resources")
        return resources_file

if __name__ == "__main__":
    generate_resources_js()
