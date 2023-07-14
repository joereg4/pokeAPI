import os
from flask import g
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def get_db():
    if 'db' not in g:
        client = MongoClient(os.environ.get("MONGODB_URI"))
        g.db = client.get_default_database()
    return g.db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.client.close()