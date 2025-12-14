"""
Bot Detection Module

This module provides privacy-focused bot detection capabilities:
- User-Agent string tracking and parsing
- Anonymized IP address tracking (hashed, not stored raw)
- Bot detection based on known patterns
- Report generation for traffic analysis

Privacy Design Principles:
- No cookies or persistent client-side tracking
- IP addresses are hashed with SHA-256 before storage (irreversible)
- Only aggregated statistics are stored, not individual request logs
- Data expires automatically after 24 hours
"""

import hashlib
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pokedex.redis_client import redis_client


# ============================================================================
# Constants and Bot Signatures
# ============================================================================

# Known bot User-Agent patterns (regex patterns for identification)
# These are used to classify traffic, not to block it
BOT_SIGNATURES = {
    # Search Engine Bots
    "googlebot": r"googlebot|google-inspectiontool|adsbot-google|google-read-aloud",
    "bingbot": r"bingbot|bingpreview|msnbot",
    "yandexbot": r"yandex",
    "baidubot": r"baiduspider",
    "duckduckbot": r"duckduckbot",
    
    # Social Media Crawlers
    "facebookbot": r"facebookexternalhit|facebookcatalog",
    "twitterbot": r"twitterbot",
    "linkedinbot": r"linkedinbot",
    "discordbot": r"discordbot",
    "telegrambot": r"telegrambot",
    "slackbot": r"slackbot",
    
    # AI/LLM Agents
    "chatgpt": r"chatgpt|gptbot|openai",
    "anthropic": r"anthropic|claude",
    "perplexity": r"perplexity",
    "cohere": r"cohere",
    
    # Developer Tools & Libraries
    "python_requests": r"python-requests|aiohttp|httpx",
    "python_urllib": r"python-urllib",
    "curl": r"^curl/",
    "wget": r"^wget/",
    "httpie": r"^httpie/",
    "postman": r"postman",
    "insomnia": r"insomnia",
    
    # Monitoring & SEO Tools
    "uptimerobot": r"uptimerobot",
    "pingdom": r"pingdom",
    "datadog": r"datadog",
    "newrelic": r"newrelic",
    "semrush": r"semrush",
    "ahrefs": r"ahrefs",
    "moz": r"moz\.com|dotbot",
    
    # Scrapers & Crawlers (generic)
    "scrapy": r"scrapy",
    "selenium": r"selenium",
    "puppeteer": r"puppeteer|headlesschrome",
    "playwright": r"playwright",
    
    # Generic Bot Indicators
    "generic_bot": r"bot|crawler|spider|scraper|fetch|http|archive",
}

# Known browser User-Agent patterns
# Note: Order matters - more specific patterns should be checked first in classify_user_agent
BROWSER_SIGNATURES = {
    "edge": r"edg/[\d.]+",  # Edge uses "Edg/" in UA
    "chrome": r"chrome/[\d.]+",  # Chrome (will match after Edge check)
    "firefox": r"firefox/[\d.]+",
    "safari": r"version/[\d.]+ safari",  # Safari uses "Version/X Safari" format
    "opera": r"opera|opr/",
    "brave": r"brave",
    "vivaldi": r"vivaldi",
}

# Suspicious patterns that might indicate automated requests
SUSPICIOUS_PATTERNS = [
    r"^$",  # Empty User-Agent
    r"^-$",  # Single dash
    r"^mozilla/[\d.]+ \(compatible;\)$",  # Minimal compatible UA
]

# Redis key prefixes for bot detection data
REDIS_PREFIX = "bot_detection:"
KEY_EXPIRY = 86400  # 24 hours - data automatically expires


# ============================================================================
# IP Anonymization Functions
# ============================================================================

def anonymize_ip(ip_address: str) -> str:
    """
    Anonymize an IP address using SHA-256 hashing.
    
    This creates a consistent hash that allows us to detect patterns
    (e.g., many requests from same source) without storing the actual IP.
    
    The hash is truncated to 12 characters for storage efficiency while
    still providing sufficient uniqueness for pattern detection.
    
    Args:
        ip_address: The raw IP address to anonymize
        
    Returns:
        A 12-character hash string representing the anonymized IP
    """
    if not ip_address:
        return "unknown"
    
    # Add a daily salt to prevent rainbow table attacks
    # This rotates daily, providing additional privacy
    daily_salt = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Combine IP with salt and hash
    data_to_hash = f"{ip_address}:{daily_salt}:pokeapi_bot_detection"
    hash_digest = hashlib.sha256(data_to_hash.encode()).hexdigest()
    
    # Return first 12 characters (48 bits of entropy - sufficient for pattern detection)
    return hash_digest[:12]


def get_client_ip(request) -> str:
    """
    Extract the client IP address from a Flask request.
    
    Handles proxied requests by checking X-Forwarded-For header first.
    For privacy, we only use this to generate an anonymized hash.
    
    Args:
        request: Flask request object
        
    Returns:
        The client IP address string
    """
    # Check for forwarded IP (behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        ip = forwarded_for.split(",")[0].strip()
    else:
        ip = request.remote_addr or "unknown"
    
    return ip


# ============================================================================
# User-Agent Classification Functions
# ============================================================================

def classify_user_agent(user_agent: str) -> Tuple[str, str]:
    """
    Classify a User-Agent string into a category and specific type.
    
    Categories:
    - "bot": Known bots and crawlers
    - "browser": Standard web browsers
    - "suspicious": Likely automated but not matching known patterns
    - "unknown": Could not be classified
    
    Args:
        user_agent: The User-Agent string to classify
        
    Returns:
        Tuple of (category, specific_type)
        e.g., ("bot", "googlebot") or ("browser", "chrome")
    """
    if not user_agent:
        return ("suspicious", "empty_ua")
    
    ua_lower = user_agent.lower()
    
    # Check for suspicious patterns first
    for pattern in SUSPICIOUS_PATTERNS:
        if re.match(pattern, user_agent, re.IGNORECASE):
            return ("suspicious", "suspicious_pattern")
    
    # Check for known bots
    for bot_name, pattern in BOT_SIGNATURES.items():
        if re.search(pattern, ua_lower):
            return ("bot", bot_name)
    
    # Check for known browsers in priority order
    # Edge must be checked before Chrome (Edge UA contains "Chrome")
    # Safari must be checked carefully (Chrome UA contains "Safari")
    browser_check_order = ["edge", "opera", "vivaldi", "brave", "firefox", "chrome", "safari"]
    for browser_name in browser_check_order:
        if browser_name in BROWSER_SIGNATURES:
            pattern = BROWSER_SIGNATURES[browser_name]
            if re.search(pattern, ua_lower):
                return ("browser", browser_name)
    
    # If it contains common browser indicators but didn't match above
    if "mozilla" in ua_lower and ("windows" in ua_lower or "mac" in ua_lower or "linux" in ua_lower):
        return ("browser", "other_browser")
    
    return ("unknown", "unclassified")


def parse_user_agent_details(user_agent: str) -> Dict:
    """
    Extract additional details from a User-Agent string.
    
    This provides more granular information without storing
    the full User-Agent (for privacy).
    
    Args:
        user_agent: The User-Agent string to parse
        
    Returns:
        Dictionary with parsed details
    """
    if not user_agent:
        return {"os": "unknown", "device_type": "unknown"}
    
    ua_lower = user_agent.lower()
    
    # Detect OS - order matters! More specific checks first
    # Android UAs contain "Linux", so check Android before Linux
    # iOS UAs may contain "Mac OS", so check iOS devices before macOS
    os_type = "unknown"
    if "iphone" in ua_lower or "ipad" in ua_lower:
        os_type = "ios"
    elif "android" in ua_lower:
        os_type = "android"
    elif "windows" in ua_lower:
        os_type = "windows"
    elif "mac os" in ua_lower or "macos" in ua_lower:
        os_type = "macos"
    elif "linux" in ua_lower:
        os_type = "linux"
    
    # Detect device type - order matters! More specific checks first
    device_type = "unknown"
    if "ipad" in ua_lower:
        device_type = "tablet"
    elif "tablet" in ua_lower:
        device_type = "tablet"
    elif "mobile" in ua_lower or "iphone" in ua_lower:
        device_type = "mobile"
    elif "android" in ua_lower:
        # Android without "mobile" or "tablet" is often a phone
        device_type = "mobile"
    elif os_type in ["windows", "macos", "linux"]:
        device_type = "desktop"
    
    return {
        "os": os_type,
        "device_type": device_type,
    }


# ============================================================================
# Tracking Functions (Redis Storage)
# ============================================================================

def track_request(request) -> Dict:
    """
    Track a request for bot detection purposes.
    
    This is the main entry point called from the request tracking middleware.
    It extracts relevant information, anonymizes it, and stores aggregated
    statistics in Redis.
    
    Privacy guarantees:
    - IP addresses are hashed before any storage
    - Only aggregate counts are stored, not individual requests
    - All data expires after 24 hours
    - No cookies or client-side storage
    
    Args:
        request: Flask request object
        
    Returns:
        Dictionary with classification results (for logging only)
    """
    # Get current time periods for bucketing
    now = int(time.time())
    hour = now // 3600
    day = now // 86400
    
    # Extract and anonymize request information
    user_agent = request.headers.get("User-Agent", "")
    raw_ip = get_client_ip(request)
    anon_ip = anonymize_ip(raw_ip)
    
    # Classify the User-Agent
    category, specific_type = classify_user_agent(user_agent)
    ua_details = parse_user_agent_details(user_agent)
    
    # Create Redis pipeline for atomic operations
    pipe = redis_client.pipeline()
    
    # Track by category (bot, browser, suspicious, unknown)
    pipe.incr(f"{REDIS_PREFIX}category:{category}:hour:{hour}")
    pipe.incr(f"{REDIS_PREFIX}category:{category}:day:{day}")
    
    # Track by specific type (e.g., googlebot, chrome)
    pipe.incr(f"{REDIS_PREFIX}type:{specific_type}:hour:{hour}")
    pipe.incr(f"{REDIS_PREFIX}type:{specific_type}:day:{day}")
    
    # Track by anonymized IP (for detecting high-volume sources)
    pipe.incr(f"{REDIS_PREFIX}ip:{anon_ip}:hour:{hour}")
    pipe.incr(f"{REDIS_PREFIX}ip:{anon_ip}:day:{day}")
    
    # Track by OS and device type
    pipe.incr(f"{REDIS_PREFIX}os:{ua_details['os']}:day:{day}")
    pipe.incr(f"{REDIS_PREFIX}device:{ua_details['device_type']}:day:{day}")
    
    # Store the anonymized IP with its category for pattern detection
    pipe.hincrby(f"{REDIS_PREFIX}ip_category:{day}", f"{anon_ip}:{category}", 1)
    
    # Set expiration for all keys
    keys_to_expire = [
        f"{REDIS_PREFIX}category:{category}:hour:{hour}",
        f"{REDIS_PREFIX}category:{category}:day:{day}",
        f"{REDIS_PREFIX}type:{specific_type}:hour:{hour}",
        f"{REDIS_PREFIX}type:{specific_type}:day:{day}",
        f"{REDIS_PREFIX}ip:{anon_ip}:hour:{hour}",
        f"{REDIS_PREFIX}ip:{anon_ip}:day:{day}",
        f"{REDIS_PREFIX}os:{ua_details['os']}:day:{day}",
        f"{REDIS_PREFIX}device:{ua_details['device_type']}:day:{day}",
        f"{REDIS_PREFIX}ip_category:{day}",
    ]
    
    for key in keys_to_expire:
        pipe.expire(key, KEY_EXPIRY)
    
    # Execute all commands
    pipe.execute()
    
    # Return classification results (for logging/debugging only)
    return {
        "category": category,
        "type": specific_type,
        "os": ua_details["os"],
        "device": ua_details["device_type"],
        "anon_ip": anon_ip,
    }


# ============================================================================
# Report Generation Functions
# ============================================================================

def get_bot_detection_stats() -> Dict:
    """
    Get aggregated bot detection statistics.
    
    Returns comprehensive statistics about traffic patterns without
    exposing any individual user or request data.
    
    Returns:
        Dictionary with categorized traffic statistics
    """
    now = int(time.time())
    hour = now // 3600
    day = now // 86400
    
    stats = {
        "current_hour": datetime.fromtimestamp(hour * 3600).strftime("%Y-%m-%d %H:00:00"),
        "current_day": datetime.fromtimestamp(day * 86400).strftime("%Y-%m-%d"),
        "categories": {},
        "types": {},
        "os_breakdown": {},
        "device_breakdown": {},
        "high_volume_sources": [],
        "hourly_by_category": {},
        "daily_by_category": {},
    }
    
    # Get category stats
    categories = ["bot", "browser", "suspicious", "unknown"]
    for category in categories:
        hourly_key = f"{REDIS_PREFIX}category:{category}:hour:{hour}"
        daily_key = f"{REDIS_PREFIX}category:{category}:day:{day}"
        
        hourly_count = int(redis_client.get(hourly_key) or 0)
        daily_count = int(redis_client.get(daily_key) or 0)
        
        stats["categories"][category] = {
            "hourly": hourly_count,
            "daily": daily_count,
        }
        stats["hourly_by_category"][category] = hourly_count
        stats["daily_by_category"][category] = daily_count
    
    # Get type breakdown (specific bots and browsers)
    type_keys = redis_client.keys(f"{REDIS_PREFIX}type:*:day:{day}")
    for key in type_keys:
        # Handle both string and bytes keys
        key_str = key if isinstance(key, str) else key.decode("utf-8")
        parts = key_str.split(":")
        if len(parts) >= 3:
            type_name = parts[2]
            count = int(redis_client.get(key) or 0)
            if count > 0:
                stats["types"][type_name] = count
    
    # Sort types by count
    stats["types"] = dict(sorted(stats["types"].items(), key=lambda x: x[1], reverse=True))
    
    # Get OS breakdown
    os_keys = redis_client.keys(f"{REDIS_PREFIX}os:*:day:{day}")
    for key in os_keys:
        key_str = key if isinstance(key, str) else key.decode("utf-8")
        parts = key_str.split(":")
        if len(parts) >= 3:
            os_name = parts[2]
            count = int(redis_client.get(key) or 0)
            if count > 0:
                stats["os_breakdown"][os_name] = count
    
    # Get device breakdown
    device_keys = redis_client.keys(f"{REDIS_PREFIX}device:*:day:{day}")
    for key in device_keys:
        key_str = key if isinstance(key, str) else key.decode("utf-8")
        parts = key_str.split(":")
        if len(parts) >= 3:
            device_type = parts[2]
            count = int(redis_client.get(key) or 0)
            if count > 0:
                stats["device_breakdown"][device_type] = count
    
    # Find high-volume sources (anonymized IPs with many requests)
    ip_keys = redis_client.keys(f"{REDIS_PREFIX}ip:*:day:{day}")
    ip_counts = []
    for key in ip_keys:
        key_str = key if isinstance(key, str) else key.decode("utf-8")
        parts = key_str.split(":")
        if len(parts) >= 3:
            anon_ip = parts[2]
            count = int(redis_client.get(key) or 0)
            if count >= 100:  # Only show IPs with 100+ daily requests
                ip_counts.append({"anon_ip": anon_ip, "count": count})
    
    # Sort by count and take top 20
    ip_counts.sort(key=lambda x: x["count"], reverse=True)
    stats["high_volume_sources"] = ip_counts[:20]
    
    # Calculate totals and percentages
    total_hourly = sum(stats["hourly_by_category"].values())
    total_daily = sum(stats["daily_by_category"].values())
    
    stats["totals"] = {
        "hourly": total_hourly,
        "daily": total_daily,
    }
    
    # Calculate bot percentage
    if total_daily > 0:
        bot_daily = stats["categories"].get("bot", {}).get("daily", 0)
        stats["bot_percentage"] = round((bot_daily / total_daily) * 100, 2)
    else:
        stats["bot_percentage"] = 0
    
    return stats


def get_bot_detection_report() -> Dict:
    """
    Generate a comprehensive bot detection report.
    
    This provides a detailed breakdown suitable for display in an admin
    dashboard or export.
    
    Returns:
        Dictionary with full report data
    """
    stats = get_bot_detection_stats()
    
    # Add additional analysis
    report = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "summary": {
            "total_requests_today": stats["totals"]["daily"],
            "total_requests_this_hour": stats["totals"]["hourly"],
            "bot_traffic_percentage": stats["bot_percentage"],
            "human_traffic_percentage": round(100 - stats["bot_percentage"], 2),
        },
        "traffic_by_category": stats["categories"],
        "top_bot_types": _get_top_items(stats["types"], 10, is_bot=True),
        "top_browsers": _get_top_items(stats["types"], 10, is_bot=False),
        "os_breakdown": stats["os_breakdown"],
        "device_breakdown": stats["device_breakdown"],
        "high_volume_sources": stats["high_volume_sources"],
        "privacy_note": (
            "All IP addresses shown are anonymized using SHA-256 hashing. "
            "Original IP addresses are never stored. Data automatically expires after 24 hours."
        ),
    }
    
    return report


def _get_top_items(types_dict: Dict, limit: int, is_bot: bool) -> List[Dict]:
    """
    Helper to get top bot types or browser types from the types dictionary.
    
    Args:
        types_dict: Dictionary of type names to counts
        limit: Maximum number of items to return
        is_bot: If True, filter for bot types; if False, filter for browser types
        
    Returns:
        List of dictionaries with type name and count
    """
    bot_type_names = set(BOT_SIGNATURES.keys())
    browser_type_names = set(BROWSER_SIGNATURES.keys())
    browser_type_names.add("other_browser")
    
    filtered = []
    for type_name, count in types_dict.items():
        if is_bot and type_name in bot_type_names:
            filtered.append({"type": type_name, "count": count})
        elif not is_bot and type_name in browser_type_names:
            filtered.append({"type": type_name, "count": count})
    
    # Sort by count and limit
    filtered.sort(key=lambda x: x["count"], reverse=True)
    return filtered[:limit]


# ============================================================================
# Utility Functions
# ============================================================================

def is_likely_bot(request) -> bool:
    """
    Quick check if a request is likely from a bot.
    
    This can be used for lightweight checks without full tracking.
    
    Args:
        request: Flask request object
        
    Returns:
        True if the request appears to be from a bot
    """
    user_agent = request.headers.get("User-Agent", "")
    category, _ = classify_user_agent(user_agent)
    return category in ("bot", "suspicious")


def get_request_classification(request) -> Dict:
    """
    Get classification information for a request without tracking it.
    
    Useful for debugging or conditional logic.
    
    Args:
        request: Flask request object
        
    Returns:
        Dictionary with classification information
    """
    user_agent = request.headers.get("User-Agent", "")
    category, specific_type = classify_user_agent(user_agent)
    ua_details = parse_user_agent_details(user_agent)
    
    return {
        "category": category,
        "type": specific_type,
        "is_bot": category in ("bot", "suspicious"),
        "os": ua_details["os"],
        "device": ua_details["device_type"],
    }
