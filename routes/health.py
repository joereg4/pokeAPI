from flask import Blueprint, jsonify, render_template, request
from utils import get_cache_stats, warm_common_endpoints
from cache import cache
from datetime import datetime

health_bp = Blueprint("health", __name__)


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

        # Return JSON if specifically requested
        if request.headers.get("Accept") == "application/json":
            return jsonify({"status": status, "cache": cache_status, "stats": stats}), (
                200 if status == "healthy" else 500
            )

        # Return HTML by default
        return render_template(
            "health.html",
            status=status,
            cache=cache_status,
            stats=stats,
            current_time=datetime.utcnow(),
        )

    except Exception as e:
        if request.headers.get("Accept") == "application/json":
            return jsonify({"status": "unhealthy", "cache": str(e)}), 500

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
                }
            ),
            500,
        )
