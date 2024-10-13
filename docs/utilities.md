# Utility Functions

The Pokédex Web Application includes several utility functions to support its operations. These are primarily located in `pokedex/utils.py`.

## Configuration

The `Config` class in `pokedex/utils.py` holds configuration values for the application:

```python
class Config:
    BASE_URL = get_env_variable('BASE_URL', 'https://pokeapi.co/api/v2')
    SPRITE_URL = get_env_variable('SPRITE_URL', 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites')
    POKEMON_PER_PAGE = int(get_env_variable('POKEMON_PER_PAGE', 60))
    ITEMS_PER_PAGE = int(get_env_variable('ITEMS_PER_PAGE', 50))
    WEBHOOK_SECRET = get_env_variable('WEBHOOK_SECRET')
    CACHE_TIMEOUT = int(get_env_variable('CACHE_TIMEOUT', 300))
```

These configuration values are used throughout the application to maintain consistency and allow for easy adjustments.

## Resource Loading

The `load_resources` function in `pokedex/utils.py` is responsible for loading resources from CSV files:

```python
def load_resources():
    global resources_dict
    resources_dict = {}
    resource_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'resources')
    
    for filename in os.listdir(resource_dir):
        if filename.endswith('.csv'):
            resource_name = os.path.splitext(filename)[0]
            file_path = os.path.join(resource_dir, filename)
            
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                resources_dict[resource_name] = list(reader)
    
    logger.info(f"Loaded {len(resources_dict)} resource files")
```

This function performs the following tasks:

1. Initializes a global dictionary `resources_dict` to store the loaded resources.
2. Defines the directory path where the CSV resource files are stored.
3. Iterates through all files in the resource directory.
4. For each CSV file:
   - Extracts the resource name from the filename.
   - Opens the file and reads its contents using `csv.DictReader`.
   - Stores the contents as a list of dictionaries in `resources_dict`, keyed by the resource name.
5. Logs the number of resource files loaded.

### Usage

The `load_resources` function is typically called during application initialization to ensure all necessary data is available for the application to use. Once loaded, the resources can be accessed through the global `resources_dict`.

Example of accessing loaded resources:

```python
def get_pokemon_description(pokemon_name):
    for entry in resources_dict.get('pokemon_descriptions', []):
        if entry['name'].lower() == pokemon_name.lower():
            return entry['description']
    return "No description available."
```

### Note

- Ensure that the CSV files are properly formatted and located in the correct directory.
- The function assumes UTF-8 encoding for the CSV files.
- Consider implementing error handling for cases where files might be missing or improperly formatted.

## Helper Functions

In `pokedex/helper.py`, there are several utility functions:

- `get_path`: Retrieves file paths for resources
- `get_summary`: Fetches summaries from CSV files
- `TYPE_COLORS`: A dictionary mapping Pokémon types to their corresponding colors

These utility functions and configurations play a crucial role in supporting the main functionality of the application, providing necessary data and settings for various operations.