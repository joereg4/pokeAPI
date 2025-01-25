import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize limiter with updated configuration
limiter = Limiter(
    app=None,  # We'll initialize the app later
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],  # Increased limits
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",  # Use fixed window strategy
    headers_enabled=True,  # Enable rate limit headers
)
