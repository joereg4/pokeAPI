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
import time
import redis
import os

health_bp = Blueprint("health", __name__)

# Initialize Redis connection for API call tracking
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


def increment_api_counter():
    """Increment the API call counter for the current hour and day"""
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


def get_api_stats():
    """Get current API call statistics"""
    now = int(time.time())
    hour_key = f"api_calls:hour:{now // 3600}"
    day_key = f"api_calls:day:{now // 86400}"

    hourly_calls = redis_client.get(hour_key)
    daily_calls = redis_client.get(day_key)

    return {
        "hourly_calls": int(hourly_calls) if hourly_calls else 0,
        "daily_calls": int(daily_calls) if daily_calls else 0,
        "current_hour": datetime.fromtimestamp(now // 3600 * 3600).strftime(
            "%Y-%m-%d %H:00:00"
        ),
        "current_day": datetime.fromtimestamp(now // 86400 * 86400).strftime(
            "%Y-%m-%d"
        ),
    }


def get_rate_limit_info():
    """Get rate limit information for the current IP"""
    print("\n=== Rate Limit Info Debug ===")
    try:
        # Get the current limits
        current_limits = limiter.current_limits
        print(f"Current limit: {current_limits}")
        if not current_limits:
            print("No limits found")
            return {"remaining": None, "reset": None, "limit": None}

        # Get the first limit rule
        limit_rule = current_limits[0]
        print(f"Limit rule: {limit_rule}")

        # Get the current limit info from the limiter
        limit_info = limiter.get_window_stats(limit_rule.key_func())
        print(f"Limit info: {limit_info}")

        if limit_info:
            reset, current = limit_info
            remaining = max(0, limit_rule.amount - current)
        else:
            reset = None
            remaining = limit_rule.amount
            current = 0

        result = {
            "remaining": remaining,
            "reset": reset,
            "limit": str(limit_rule),
            "max_requests": limit_rule.amount,
            "current": current,
            "retry_after": reset - int(time.time()) if reset else None,
        }
        print(f"Final result: {result}")
        return result
    except Exception as e:
        print(f"Error getting rate limit info: {str(e)}")
        return {"remaining": None, "reset": None, "limit": None}


@health_bp.route("/health/cache")
def check_cache_health():
    """Check if Redis cache is functioning properly"""
    try:
        # Pre-warm the cache
        warm_common_endpoints()

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
                    }
                )
            )
            if rate_limits.get("max_requests"):
                response.headers.update(
                    {
                        "X-RateLimit-Limit": str(rate_limits["max_requests"]),
                        "X-RateLimit-Remaining": str(rate_limits["remaining"]),
                        "X-RateLimit-Reset": str(rate_limits["reset"]),
                    }
                )
            return response, (200 if status == "healthy" else 500)

        # Render HTML template
        return render_template(
            "health.html",
            cache_status=cache_status,
            stats=stats,
            rate_limits=rate_limits,
            api_stats=api_stats,
            current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    except Exception as e:
        return str(e), 500


@health_bp.route("/health/cache/json")
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

        # Initialize rate limit variables
        limit = None
        remaining = None
        reset = None
        current = 0
        retry_after = None

        # Get rate limit info from the current request
        current_limit = limiter.current_limit
        if current_limit:
            # Get the limit value
            limit = int(str(current_limit.limit).split()[0])
            remaining = current_limit.remaining
            reset = current_limit.reset_at
            current = limit - remaining

        rate_limits = {
            "limit": limit,
            "remaining": remaining,
            "reset": reset,
            "current": current,
            "retry_after": retry_after,
        }

        # Get API stats
        api_stats = get_api_stats()

        response = make_response(
            jsonify(
                {
                    "status": "healthy",
                    "cache": stats,
                    "rate_limits": rate_limits,
                    "api_calls": api_stats,
                }
            )
        )

        # Add rate limit headers if we have the info
        if limit is not None:
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
            }
            if reset:
                headers["X-RateLimit-Reset"] = str(reset)
            if retry_after:
                headers["Retry-After"] = str(retry_after)
            response.headers.update(headers)

        return response
    except Exception as e:
        response = make_response(
            jsonify(
                {
                    "status": "unhealthy",
                    "cache": str(e),
                    "rate_limits": get_rate_limit_info(),
                    "api_calls": get_api_stats(),
                }
            )
        )
        return response, 500
