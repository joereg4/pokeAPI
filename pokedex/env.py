import os

from dotenv import load_dotenv


def load_environment():
    load_dotenv(override=True)
    load_dotenv(".flaskenv", override=True)

    if "FLASK_ENV" not in os.environ:
        os.environ["FLASK_ENV"] = "development"
    if "FLASK_APP" not in os.environ:
        os.environ["FLASK_APP"] = "app.py"
    if "FLASK_DEBUG" not in os.environ:
        os.environ["FLASK_DEBUG"] = "1"
    if "REDIS_URL" not in os.environ:
        os.environ["REDIS_URL"] = "redis://localhost:6379/0"


def get_env_variable(var_name, default=None):
    value = os.environ.get(var_name)
    if value is None:
        if default is not None:
            os.environ[var_name] = str(default)
            return default
    return value
