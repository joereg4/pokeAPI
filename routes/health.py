from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    current_app,
    make_response,
)
from utils import get_cache_stats, warm_common_endpoints
from cache import cache
from datetime import datetime
from limiter import limiter
from flask_limiter.util import get_remote_address
from flask_login import login_required
import time
from pokedex.redis_client import redis_client

health_bp = Blueprint("health", __name__)


def get_rate_limit_info():
    """Get current rate limit information"""
    try:
        # Get the current limit for this endpoint
        current_limit = limiter.current_limit
        if not current_limit:
            return {}

        # Get rate limit info directly from the RequestLimit object
        result = {
            "limit": int(str(current_limit.limit).split()[0]),  # "500 per hour" -> 500
            "remaining": current_limit.remaining,
            "reset": current_limit.reset_at,
            "current": int(str(current_limit.limit).split()[0])
            - current_limit.remaining,
        }
        return result
    except Exception as e:
        return {}


def increment_api_counter():
    """Increment the API call counter for various metrics"""
    now = int(time.time())
    hour = now // 3600
    day = now // 86400
    week = now // (86400 * 7)
    month = now // (86400 * 30)

    # Get request details
    endpoint = (
        request.path.split("/")[1] if len(request.path.split("/")) > 1 else "root"
    )
    resource_type = (
        request.path.split("/")[2] if len(request.path.split("/")) > 2 else "none"
    )
    method = request.method
    is_success = True  # We'll update this based on response status
    is_cached = False  # We'll update this based on cache status

    # Create pipeline for atomic operations
    pipe = redis_client.pipeline()

    # Basic time-based counters
    pipe.incr(f"api_calls:hour:{hour}")
    pipe.incr(f"api_calls:day:{day}")
    pipe.incr(f"api_calls:week:{week}")
    pipe.incr(f"api_calls:month:{month}")

    # Endpoint tracking
    pipe.incr(f"api_calls:endpoint:{endpoint}:hour:{hour}")
    pipe.incr(f"api_calls:endpoint:{endpoint}:day:{day}")

    # Resource type tracking
    pipe.incr(f"api_calls:resource:{resource_type}:hour:{hour}")
    pipe.incr(f"api_calls:resource:{resource_type}:day:{day}")

    # Method tracking
    pipe.incr(f"api_calls:method:{method}:hour:{hour}")
    pipe.incr(f"api_calls:method:{method}:day:{day}")

    # Set expiration for all keys
    pipe.expire(f"api_calls:hour:{hour}", 3600)  # 1 hour
    pipe.expire(f"api_calls:day:{day}", 86400)  # 1 day
    pipe.expire(f"api_calls:week:{week}", 604800)  # 1 week
    pipe.expire(f"api_calls:month:{month}", 2592000)  # 30 days

    # Set expiration for endpoint keys
    pipe.expire(f"api_calls:endpoint:{endpoint}:hour:{hour}", 3600)
    pipe.expire(f"api_calls:endpoint:{endpoint}:day:{day}", 86400)

    # Set expiration for resource keys
    pipe.expire(f"api_calls:resource:{resource_type}:hour:{hour}", 3600)
    pipe.expire(f"api_calls:resource:{resource_type}:day:{day}", 86400)

    # Set expiration for method keys
    pipe.expire(f"api_calls:method:{method}:hour:{hour}", 3600)
    pipe.expire(f"api_calls:method:{method}:day:{day}", 86400)

    # Execute all commands
    results = pipe.execute()
    return results


def get_api_stats():
    """Get current API call statistics with rolling 7-day and 30-day windows."""
    now = int(time.time())
    hour = now // 3600
    day = now // 86400

    # Get all relevant keys
    keys = [
        f"api_calls:hour:{hour}",
        f"api_calls:day:{day}",
    ]

    # Get all values
    values = redis_client.mget(keys)

    # Convert to integers, defaulting to 0 if None
    hourly_calls = int(values[0]) if values[0] else 0
    daily_calls = int(values[1]) if values[1] else 0

    # Rolling 7-day and 30-day totals
    last_7_days = [f"api_calls:day:{day - i}" for i in range(7)]
    last_30_days = [f"api_calls:day:{day - i}" for i in range(30)]
    last_7_counts = redis_client.mget(last_7_days)
    last_30_counts = redis_client.mget(last_30_days)
    weekly_calls = sum(int(x) if x else 0 for x in last_7_counts)
    monthly_calls = sum(int(x) if x else 0 for x in last_30_counts)

    # Get endpoint stats
    endpoint_keys = redis_client.keys(f"api_calls:endpoint:*:hour:{hour}")
    endpoint_stats = {}
    if endpoint_keys:
        endpoint_values = redis_client.mget(endpoint_keys)
        for key, value in zip(endpoint_keys, endpoint_values):
            endpoint = key.decode("utf-8").split(":")[2]
            endpoint_stats[endpoint] = int(value) if value else 0

    # Get resource stats
    resource_keys = redis_client.keys(f"api_calls:resource:*:hour:{hour}")
    resource_stats = {}
    if resource_keys:
        resource_values = redis_client.mget(resource_keys)
        for key, value in zip(resource_keys, resource_values):
            resource = key.decode("utf-8").split(":")[2]
            resource_stats[resource] = int(value) if value else 0

    # Get method stats
    method_keys = redis_client.keys(f"api_calls:method:*:hour:{hour}")
    method_stats = {}
    if method_keys:
        method_values = redis_client.mget(method_keys)
        for key, value in zip(method_keys, method_values):
            method = key.decode("utf-8").split(":")[2]
            method_stats[method] = int(value) if value else 0

    return {
        "hourly_calls": hourly_calls,
        "daily_calls": daily_calls,
        "weekly_calls": weekly_calls,  # rolling 7-day
        "monthly_calls": monthly_calls,  # rolling 30-day
        "current_hour": datetime.fromtimestamp(hour * 3600).strftime(
            "%Y-%m-%d %H:00:00"
        ),
        "current_day": datetime.fromtimestamp(day * 86400).strftime("%Y-%m-%d"),
        "endpoint_stats": endpoint_stats,
        "resource_stats": resource_stats,
        "method_stats": method_stats,
    }


def get_traffic_stats():
    """Get detailed traffic statistics from Redis, with rolling 7-day and 30-day windows."""
    try:
        # Define valid API endpoints we want to track
        VALID_API_ENDPOINTS = {
            # Pokemon Core
            "pokemon",
            "pokemon-species",
            "pokemon-form",
            "pokemon-color",
            "pokemon-habitat",
            "pokemon-shape",
            "pokedex",
            # Moves & Abilities
            "move",
            "move-ailment",
            "move-battle-style",
            "move-category",
            "move-damage-class",
            "move-learn-method",
            "move-target",
            "ability",
            # Items
            "item",
            "item-attribute",
            "item-category",
            "item-fling-effect",
            "item-pocket",
            "machine",
            # Locations & Regions
            "location",
            "location-area",
            "pal-park-area",
            "region",
            # Characteristics & Stats
            "characteristic",
            "pokeathlon-stat",
            "stat",
            "type",
            # Breeding
            "egg-group",
            "gender",
            "growth-rate",
            # Evolution
            "evolution-chain",
            "evolution-trigger",
            "generation",
            # Berries & Contests
            "berry",
            "berry-firmness",
            "berry-flavor",
            "contest-effect",
            "contest-type",
            "super-contest-effect",
            # Nature
            "nature",
            # Artwork
            "artwork",
        }

        now = int(time.time())
        hour = now // 3600
        day = now // 86400

        pipe = redis_client.pipeline()

        # Get all keys for different metrics
        pipe.keys("api_calls:endpoint:*")
        pipe.keys("api_calls:resource:*")
        pipe.keys("api_calls:method:*")

        # Get current time period counts
        pipe.get(f"api_calls:hour:{hour}")
        pipe.get(f"api_calls:day:{day}")
        # Remove week/month from pipeline, will use rolling logic below

        # Execute pipeline
        (
            keys,
            resource_keys,
            method_keys,
            hourly,
            daily,
        ) = pipe.execute()

        # Rolling 7-day and 30-day totals
        last_7_days = [f"api_calls:day:{day - i}" for i in range(7)]
        last_30_days = [f"api_calls:day:{day - i}" for i in range(30)]
        last_7_counts = redis_client.mget(last_7_days)
        last_30_counts = redis_client.mget(last_30_days)
        weekly_calls = sum(int(x) if x else 0 for x in last_7_counts)
        monthly_calls = sum(int(x) if x else 0 for x in last_30_counts)

        # Process endpoint stats and organize resources by endpoint
        endpoint_stats = {}
        for key in keys:
            key_str = key.decode()
            parts = key_str.split(":")
            endpoint = parts[2]  # Get endpoint name from key structure

            # Skip non-API endpoints
            if endpoint not in VALID_API_ENDPOINTS:
                continue

            count = int(redis_client.get(key) or 0)
            endpoint_stats[endpoint] = {"total_calls": count, "resources": {}}

        # Process resource stats and associate them with endpoints
        for key in resource_keys:
            key_str = key.decode()
            parts = key_str.split(":")
            endpoint = parts[2]  # Get endpoint from key structure

            # Skip if endpoint is not in our valid list
            if endpoint not in VALID_API_ENDPOINTS:
                continue

            resource_id = parts[3]  # Get resource_id from key structure

            # Skip if the resource_id is a time period or invalid
            if resource_id in ["hour", "day", "week", "month"] or not resource_id:
                continue

            count = int(redis_client.get(key) or 0)

            # Skip if it's not a numeric ID and not a named resource
            if (
                not resource_id.isdigit()
                and resource_id != "none"
                and not resource_id.isalpha()
            ):
                continue

            # Get resource name from cache
            if resource_id != "none":
                resource_name = redis_client.get(
                    f"pokedex:{endpoint}:{resource_id}:name"
                )
                if resource_name:
                    resource_name = resource_name.decode()
                else:
                    resource_name = f"{endpoint.title()} #{resource_id}"
            else:
                resource_name = "Unknown Resource"

            # Add to the appropriate endpoint's resources
            if endpoint in endpoint_stats:
                endpoint_stats[endpoint]["resources"][resource_name] = count

        # Sort resources within each endpoint by count
        for endpoint in endpoint_stats:
            endpoint_stats[endpoint]["resources"] = dict(
                sorted(
                    endpoint_stats[endpoint]["resources"].items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )

        return {
            "endpoint_stats": endpoint_stats,  # Now contains hierarchical data
            "current_hour": datetime.fromtimestamp(hour * 3600).strftime(
                "%Y-%m-%d %H:00:00"
            ),
            "current_day": datetime.fromtimestamp(day * 86400).strftime("%Y-%m-%d"),
            "hourly_calls": int(hourly or 0),
            "daily_calls": int(daily or 0),
            "weekly_calls": weekly_calls,  # rolling 7-day
            "monthly_calls": monthly_calls,  # rolling 30-day
        }
    except Exception as e:
        print(f"ERROR in get_traffic_stats: {e}")
        raise


@health_bp.route("/health/cache")
@login_required
@limiter.limit("30 per minute")  # More reasonable limit for health checks
def check_cache_health():
    """Check if Redis cache is functioning properly"""
    try:
        # Try to set and get a test key
        test_key = "health_check"
        test_value = "ok"
        cache.set(test_key, test_value, timeout=10)
        result = cache.get(test_key)

        stats = get_cache_stats()
        status = "healthy" if result == test_value else "unhealthy"
        cache_status = "operational" if result == test_value else "value mismatch"

        # Get rate limit info
        rate_limits = get_rate_limit_info()

        # Get API stats
        api_stats = get_api_stats()

        # Get traffic stats
        traffic_stats = get_traffic_stats()

        # Return JSON if specifically requested
        if request.headers.get("Accept") == "application/json":
            response = make_response(
                jsonify(
                    {
                        "status": status,
                        "cache": cache_status,
                        "stats": stats,
                        "rate_limits": rate_limits,
                        "api_calls": api_stats,
                        "traffic_stats": traffic_stats,
                    }
                )
            )
            if rate_limits.get("limit"):
                response.headers.update(
                    {
                        "X-RateLimit-Limit": str(rate_limits["limit"]),
                        "X-RateLimit-Remaining": str(rate_limits["remaining"]),
                        "X-RateLimit-Reset": str(rate_limits["reset"]),
                    }
                )
            return response, (200 if status == "healthy" else 500)

        # Render HTML template
        return render_template(
            "health.html",
            status=status,
            cache=cache_status,
            stats=stats,
            rate_limits=rate_limits,
            api_stats=api_stats,
            traffic_stats=traffic_stats,
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    except Exception as e:
        error_msg = str(e)
        # Return JSON if specifically requested
        if request.headers.get("Accept") == "application/json":
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "cache": error_msg,
                        "rate_limits": get_rate_limit_info(),
                    }
                ),
                500,
            )

        # Return HTML error page for other requests
        error_stats = {
            "status": "disconnected",
            "hit_rate": 0,
            "used_memory_human": "N/A",
            "connected_clients": 0,
            "total_connections_received": 0,
            "uptime_in_seconds": 0,
            "error": error_msg,
        }
        return (
            render_template(
                "health.html",
                status="unhealthy",
                cache="error",
                stats=error_stats,
                rate_limits=get_rate_limit_info(),
                api_stats=get_api_stats(),
                traffic_stats=get_traffic_stats(),
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
            500,
        )


@health_bp.route("/health/cache/json")
@login_required
def health_cache_json():
    """Health check endpoint for cache status (JSON response)"""
    try:
        stats = get_cache_stats()
        if stats["status"] == "disconnected":
            response = make_response(
                jsonify(
                    {
                        "status": "unhealthy",
                        "cache": "Redis connection failed",
                        "rate_limits": get_rate_limit_info(),
                    }
                )
            )
            return response, 500

        # Get rate limit info
        rate_limits = get_rate_limit_info()

        # Get API stats
        api_stats = get_api_stats()

        # Get traffic stats
        traffic_stats = get_traffic_stats()

        response = make_response(
            jsonify(
                {
                    "status": "healthy",
                    "cache": stats,
                    "rate_limits": rate_limits,
                    "api_calls": api_stats,
                    "traffic_stats": traffic_stats,
                }
            )
        )

        # Add rate limit headers if we have the info
        if rate_limits.get("limit"):
            headers = {
                "X-RateLimit-Limit": str(rate_limits["limit"]),
                "X-RateLimit-Remaining": str(rate_limits["remaining"]),
            }
            if rate_limits.get("reset"):
                headers["X-RateLimit-Reset"] = str(rate_limits["reset"])
            response.headers.update(headers)

        return response
    except Exception as e:
        error_msg = str(e)
        response = make_response(
            jsonify(
                {
                    "status": "unhealthy",
                    "cache": error_msg,
                    "rate_limits": get_rate_limit_info(),
                    "api_calls": get_api_stats(),
                }
            )
        )
        return response, 500
