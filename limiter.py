import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
from pokedex.redis_client import REDIS_POOL

# Initialize limiter with updated configuration.
# The storage URI must come from the environment: in Docker, Redis lives at
# redis://redis:6379, not localhost. If this URI is unreachable, Flask-Limiter
# silently falls back to per-worker in-memory storage, which breaks the
# brute-force protection guarantees (limits multiply by worker count and
# reset on restart).
limiter = Limiter(
    app=None,  # We'll initialize the app later
    key_func=get_remote_address,
    default_limits=["100000 per minute"],  # Very high limit since API has no limits
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    storage_options={
        "connection_pool": REDIS_POOL,
        "socket_connect_timeout": 30,
        "retry_on_timeout": True,
    },
    strategy="fixed-window",  # Use fixed window strategy
    headers_enabled=True,  # Enable rate limit headers
)

# Flask-Limiter decorators will be applied in the route files
# For exempting routes, we'll configure them in the app.py file
# after initializing the limiter with the app

# The following routes should be exempt from rate limiting:
# - All /artwork/ routes (for sprite images)
# - /pokemon and /type routes (for Pokemon lists)
