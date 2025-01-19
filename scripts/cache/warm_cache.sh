#!/bin/bash

# Activate virtual environment
source /var/www/pokeAPI/venv/bin/activate

# Run Python script to warm cache
python3 << END
from pokedex.utils import warm_common_endpoints
warm_common_endpoints()
END 