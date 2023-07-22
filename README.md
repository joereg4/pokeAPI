# Pokédex API

## Overview

This project provides a RESTful API to fetch Pokémon details, including species, evolution chain, and more.

---

## Table of Contents

1. [Setup](#setup)
    - [Prerequisites](#prerequisites)
    - [Installation](#installation)
2. [Running the API](#running-the-api)
3. [Features](#features)
4. [Directory Structure](#directory-structure)
5. [Contributing](#contributing)
6. [License](#license)

---

## Setup

### Prerequisites

- Python 3.9+
- Flask
- Virtualenv (recommended)

### Installation

1. **Clone the Repository**
    ```bash
    git clone <repository_url>
    ```

2. **Navigate to the Project Directory**
    ```bash
    cd pokeAPI
    ```

3. **(Recommended) Set Up a Virtual Environment**
    ```bash
    virtualenv venv
    ```

4. **Activate the Virtual Environment**
    - macOS/Linux:
        ```bash
        source venv/bin/activate
        ```
    - Windows:
        ```bash
        .\venv\Scripts\activate
        ```

5. **Install Required Packages**
    ```bash
    pip install -r requirements.txt
    ```

6. **Configure Logging**
    To use Python's native logging, ensure you have imported the `logging` module and initialized it as per your requirements.

---

## Running the API

Execute the following command to start the Pokédex API:
```bash
flask run
