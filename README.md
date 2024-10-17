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
7. [Testing](#testing)
8. [Contributing](#contributing)
9. [License](#license)

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
