import os
from dotenv import load_dotenv


def load_environment():
    load_dotenv(".env")
    load_dotenv(".flaskenv")


def get_env_variable(var_name, default=None):
    return os.environ.get(var_name, default)
