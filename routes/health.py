from flask import Blueprint, jsonify, render_template, request, current_app
from utils import get_cache_stats, warm_common_endpoints
from cache import cache
from datetime import datetime
from app import limiter

health_bp = Blueprint("health", __name__)


def get_rate_limit_info():
    """Get rate limit information for the current IP"""
    limits = limiter.current_limit
    if not limits:
        return {"remaining": "unlimited", "reset": None, "limit": "unlimited"}

    return {
        "remaining": limiter.get_window_stats(*limits)[1],
        "reset": datetime.fromtimestamp(limiter.get_window_stats(*limits)[0]),
        "limit": str(limits[0]),
    }


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
            return jsonify(
                {
                    "status": status,
                    "cache": cache_status,
                    "stats": stats,
                    "rate_limits": rate_limits,
                }
            ), (200 if status == "healthy" else 500)

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
def check_cache_health_json():
    """Check if Redis cache is functioning properly (JSON response)"""
    try:
        # Pre-warm the cache
        warm_common_endpoints()

        # Try to set and get a test key
        test_key = "health_check"
        test_value = "ok"
        cache.set(test_key, test_value, timeout=10)
        result = cache.get(test_key)

        if result == test_value:
            return (
                jsonify(
                    {
                        "status": "healthy",
                        "cache": "operational",
                        "stats": get_cache_stats(),
                        "rate_limits": get_rate_limit_info(),
                    }
                ),
                200,
            )
        else:
            return (
                jsonify(
                    {
                        "status": "unhealthy",
                        "cache": "value mismatch",
                        "rate_limits": get_rate_limit_info(),
                    }
                ),
                500,
            )
    except Exception as e:
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
