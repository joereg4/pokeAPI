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

health_bp = Blueprint("health", __name__)


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

        # Return JSON if specifically requested
        if request.headers.get("Accept") == "application/json":
            response = make_response(
                jsonify(
                    {
                        "status": status,
                        "cache": cache_status,
                        "stats": stats,
                        "rate_limits": rate_limits,
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

        # Return HTML by default
        return render_template(
            "health.html",
            status=status,
            cache=cache_status,
            stats=stats,
            rate_limits=rate_limits,
            current_time=datetime.utcnow(),
        )

    except Exception as e:
        if request.headers.get("Accept") == "application/json":
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "cache": str(e),
                        "rate_limits": get_rate_limit_info(),
                    }
                ),
                500,
            )

        return render_template(
            "health.html",
            status="unhealthy",
            cache=str(e),
            stats={
                "hit_rate": 0,
                "used_memory_human": "N/A",
                "connected_clients": 0,
                "total_connections_received": 0,
                "uptime_in_seconds": 0,
            },
            rate_limits=get_rate_limit_info(),
            current_time=datetime.utcnow(),
        )


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

        response = make_response(
            jsonify(
                {
                    "status": "healthy",
                    "cache": stats,
                    "rate_limits": rate_limits,
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
                }
            )
        )
        return response, 500
