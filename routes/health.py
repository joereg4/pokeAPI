from flask import Blueprint, jsonify
from utils import get_cache_stats, warm_common_endpoints
from cache import cache

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
