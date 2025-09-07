# Pokémon API Web Application UI Improvements

## Summary of Changes

### Item Display Enhancements
- Fixed sprite rendering in item_detail.html by adjusting image dimensions to 96px
- Improved container styling with proper shadows and padding
- Fixed alignment issues by removing the p-4 class and adding proper centering
- Reorganized item detail header to place name, sprite, and edit icon in a horizontal row

### Move Category Improvements
- Created a reusable formatter for category names to handle special characters
- Replaced custom styling with Bootstrap badges
- Added error handling for missing data
- Fixed description duplication issue

### New Move Damage Class Template
- Created move_damage_class_detail.html to display physical, special, and status moves
- Implemented proper descriptions from the API
- Used grid layout for move listings
- Maintained consistent styling with other pages

### Move Detail Enhancements
- Made damage class badges link to the move-damage-class route
- Removed duplicate damage class information
- Improved spacing in the header section

### Type Display Standardization
- Replaced type image nameplates with colored badges across:
  - type_detail.html
  - pokemon_detail.html

### Overall Improvements
- Maintained consistent color scheme for type badges
- Ensured proper formatting of text elements (like uppercase Roman numerals for generation names)

# Pokédex Web Application

## Overview

This Flask-based web application provides a comprehensive Pokédex, offering detailed information about Pokémon, their characteristics, locations, and more. It utilizes the PokéAPI as its primary data source and implements efficient caching mechanisms to improve performance.

---

## Table of Contents

1. [Features](#features)
2. [Technology Stack](#technology-stack)
3. [Setup](#setup)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
4. [Running the Application](#running-the-application)
5. [Project Structure](#project-structure)
6. [Caching System](#caching-system)
7. [Database Management](#database-management)
8. [Testing](#testing)
9. [Contributing](#contributing)
10. [License](#license)

---

## Features

- Detailed information on Pokémon, including stats, abilities, and evolutions
- Data on locations, items, berries, and more from the Pokémon universe
- Efficient two-level caching system for improved performance
- Modular design with Flask blueprints
- Comprehensive test suite

## Technology Stack

- Flask: Web framework
- Python 3.9+: Programming language
- PokéAPI: Primary data source
- Flask-Caching: High-level caching for route responses
- Shelve: Low-level caching for Pokédex-specific data
- Pandas: Data manipulation and analysis
- Markdown: Text-to-HTML conversion for summaries

## Setup

### Prerequisites

- Python 3.9+
- pip (Python package manager)
- Virtualenv (recommended)

### Installation

1. **Clone the Repository**
    ```bash
    git clone <repository_url>
    cd pokeAPI
    ```

2. **Set Up a Virtual Environment**
    ```bash
    python -m venv venv
    ```

3. **Activate the Virtual Environment**
    - macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    - Windows:
        ```bash
        .\venv\Scripts\activate
        ```

4. **Install Required Packages**
    ```bash
    pip install -r requirements.txt
    ```

5. **Configure Environment Variables**
    Create a `.env` file in the project root and add necessary environment variables (refer to `pokedex/utils.py` for required variables).

## Redis Setup

This application uses Redis for caching. To set up Redis:

1. Install Redis on your local machine
2. Start the Redis server:
   ```
   redis-server
   ```
3. Set the `REDIS_URL` environment variable or add it to your `.env` file:
   ```
   REDIS_URL=redis://localhost:6379/0
   ```

For production, ensure you have a Redis instance available and set the `REDIS_URL` environment variable accordingly.

## Running the Application

Execute the following command to start the Pokédex Web Application:

```bash
python app.py
```

## Database Management

The application includes comprehensive database management scripts for syncing data between local development and production environments.

### Available Scripts

- **`scripts/upload_pokemon_summaries.py`** - Upload specific resource types from local to production
- **`scripts/backup_db.py`** - Create full database backups and restore functionality
- **`scripts/interactive_summary_updater.py`** - Interactive tool for reviewing and updating summaries

### Key Features

- **Automatic Backups**: All upload operations create backups before making changes
- **Resource-Specific Uploads**: Upload only specific resource types (pokemon, ability, move, etc.)
- **Dry-Run Mode**: Preview changes before applying them
- **Rollback Capability**: Restore from any backup if needed
- **SSH Tunnel Support**: Secure connections to production database
- **Interactive Summary Updates**: Review and improve existing summaries with progress tracking

### Quick Start

1. **Install Dependencies**:
   ```bash
   pipenv install paramiko psycopg2-binary
   ```

2. **Establish SSH Tunnel**:
   ```bash
   ssh -L 5433:localhost:5432 root@149.28.243.132
   ```

3. **Upload Pokemon Summaries**:
   ```bash
   python3 scripts/upload_pokemon_summaries.py \
     --resource pokemon \
     --host localhost \
     --port 5433 \
     --database pokeapi \
     --user pokeapi \
     --password "your_password"
   ```

4. **Create Full Backup**:
   ```bash
   python3 scripts/backup_db.py \
     --host localhost \
     --port 5433 \
     --database pokeapi \
     --user pokeapi \
     --password "your_password"
   ```

5. **Update Summaries Interactively**:
   ```bash
   # Review and update pokemon summaries
   python3 scripts/interactive_summary_updater.py --resource pokemon
   
   # Update all remaining summaries automatically
   python3 scripts/interactive_summary_updater.py --resource pokemon --update-all
   ```

For detailed documentation, see [Database Management Guide](docs/database_management.md) and [Interactive Summary Updater Guide](docs/interactive_summary_updater.md).
