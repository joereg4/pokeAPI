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

health_bp = Blueprint("health", __name__)


def get_rate_limit_info():
    """Get rate limit information for the current IP"""
    print("\n=== Rate Limit Info Debug ===")
    current_limits = limiter.current_limits
    print(f"Current limit: {current_limits}")
    if not current_limits:
        print("No limits found")
        return {"remaining": None, "reset": None, "limit": None}

    limit_rule = current_limits[0]  # Get the first limit rule
    print(f"Limit rule: {limit_rule}")

    try:
        hit_count = limiter.limiter.get_hit_count(limit_rule)
        print(f"Hit count: {hit_count}")
    except Exception as e:
        print(f"Error getting rate limit info: {str(e)}")
        return {"remaining": None, "reset": None, "limit": None}

    try:
        max_requests = limit_rule.amount
        remaining = max(0, max_requests - hit_count)
        print(f"Max requests: {max_requests}, Remaining: {remaining}")
    except Exception as e:
        print(f"Error calculating remaining requests: {str(e)}")
        return {"remaining": None, "reset": None, "limit": None}

    try:
        reset = limiter.limiter.get_window_expiry(limit_rule)
        print(f"Reset time: {reset}")
    except Exception as e:
        print(f"Error getting reset time: {str(e)}")
        return {"remaining": None, "reset": None, "limit": None}

    result = {
        "remaining": remaining,
        "reset": reset,
        "limit": str(limit_rule),
        "max_requests": max_requests,  # Add max_requests to the result
    }
    print(f"Final result: {result}")
    return result


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
    stats = get_cache_stats()
    rate_limits = get_rate_limit_info()

    response = make_response(
        jsonify(
            {
                "status": "healthy" if stats["status"] == "connected" else "unhealthy",
                "cache": stats,
                "rate_limits": rate_limits,
            }
        )
    )

    # Add rate limit headers
    if rate_limits.get("max_requests"):
        response.headers.update(
            {
                "X-RateLimit-Limit": str(rate_limits["max_requests"]),
                "X-RateLimit-Remaining": str(rate_limits["remaining"]),
                "X-RateLimit-Reset": str(rate_limits["reset"]),
            }
        )

    return response
