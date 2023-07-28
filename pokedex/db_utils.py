from flask import g
from pymongo import MongoClient
from pokedex.env import get_env_variable

def get_db():
    if 'db' not in g:
        mongodb_uri = get_env_variable("MONGODB_URI")
        client = MongoClient(mongodb_uri)
        g.db = client.get_default_database()
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.client.close()
