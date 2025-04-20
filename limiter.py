import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pokedex.redis_client import REDIS_POOL

# Initialize limiter with updated configuration
limiter = Limiter(
    app=None,  # We'll initialize the app later
    key_func=get_remote_address,
    default_limits=["100 per minute"],  # Set global rate limit
    storage_uri="redis://localhost:6379/0",  # Specify Redis connection
    storage_options={
        "connection_pool": REDIS_POOL,
        "socket_connect_timeout": 30,
        "retry_on_timeout": True,
    },
    strategy="fixed-window",  # Use fixed window strategy
    headers_enabled=True,  # Enable rate limit headers
)

# Remove Pokemon list exemption since we want to rate limit it
# The Pokemon list endpoint will use the global rate limit of 100 per minute
