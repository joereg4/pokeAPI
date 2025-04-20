import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pokedex.redis_client import REDIS_POOL

# Initialize limiter with updated configuration
limiter = Limiter(
    app=None,  # We'll initialize the app later
    key_func=get_remote_address,
    default_limits=[],  # Remove global limits
    storage_uri="redis://",
    storage_options={
        "connection_pool": REDIS_POOL,
        "socket_connect_timeout": 30,
        "retry_on_timeout": True,
    },
    strategy="fixed-window",  # Use fixed window strategy
    headers_enabled=True,  # Enable rate limit headers
)

# Add specific rate limits for sensitive endpoints
limiter.limit("100 per minute")(
    limiter.exempt
)  # Add exemption for Pokemon list endpoint
