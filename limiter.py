import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)
