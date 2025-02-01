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


@health_bp.route("/health/cache")
@login_required
@limiter.limit("500 per hour")
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
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    except Exception as e:
        error_msg = str(e)
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
