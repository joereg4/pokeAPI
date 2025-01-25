import requests
from requests.exceptions import HTTPError
import os
import redis
from .utils import Config

# Initialize Redis connection for API call tracking
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def increment_api_counter():
    """Increment the API call counter for the current hour and day"""
    import time

    now = int(time.time())
    hour_key = f"api_calls:hour:{now // 3600}"
    day_key = f"api_calls:day:{now // 86400}"

    pipe = redis_client.pipeline()
    pipe.incr(hour_key)
    pipe.expire(hour_key, 3600)  # Expire after 1 hour
    pipe.incr(day_key)
    pipe.expire(day_key, 86400)  # Expire after 1 day
    results = pipe.execute()
    return results[0], results[2]  # Return hourly and daily counts


class APIResource:
    @staticmethod
    def fetch_data(endpoint, id_or_name):
        """Fetch data from the PokeAPI"""
        try:
            # Track the API call
            increment_api_counter()

            # Make the API request
            url = f"{Config.BASE_URL}/{endpoint}/{str(id_or_name).lower()}"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"{endpoint.title()} '{id_or_name}' not found")
            raise
