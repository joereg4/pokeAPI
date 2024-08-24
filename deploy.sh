#!/bin/bash

cd /var/www/pokeAPI
git pull origin main
source /var/www/pokeAPI/venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart gunicorn