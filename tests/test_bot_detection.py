"""
Tests for the bot detection module.

These tests verify:
1. IP anonymization produces consistent, non-reversible hashes
2. User-Agent classification correctly identifies bots and browsers
3. Bot signature patterns match expected User-Agents
4. Privacy guarantees are maintained (no raw IP storage)
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

# Import the module under test
from bot_detection import (
    anonymize_ip,
    classify_user_agent,
    parse_user_agent_details,
    get_client_ip,
    is_likely_bot,
    get_request_classification,
    BOT_SIGNATURES,
    BROWSER_SIGNATURES,
)


class TestIPAnonymization:
    """Tests for IP address anonymization functionality."""

    def test_anonymize_ip_produces_consistent_hash(self):
        """Same IP should produce same hash on same day."""
        ip = "192.168.1.1"
        hash1 = anonymize_ip(ip)
        hash2 = anonymize_ip(ip)
        assert hash1 == hash2, "Same IP should produce consistent hash"

    def test_anonymize_ip_different_ips_produce_different_hashes(self):
        """Different IPs should produce different hashes."""
        ip1 = "192.168.1.1"
        ip2 = "192.168.1.2"
        hash1 = anonymize_ip(ip1)
        hash2 = anonymize_ip(ip2)
        assert hash1 != hash2, "Different IPs should produce different hashes"

    def test_anonymize_ip_returns_12_char_string(self):
        """Hash should be exactly 12 characters."""
        ip = "10.0.0.1"
        hash_result = anonymize_ip(ip)
        assert len(hash_result) == 12, "Hash should be 12 characters"

    def test_anonymize_ip_handles_empty_string(self):
        """Empty IP should return 'unknown'."""
        result = anonymize_ip("")
        assert result == "unknown"

    def test_anonymize_ip_handles_none(self):
        """None IP should return 'unknown'."""
        result = anonymize_ip(None)
        assert result == "unknown"

    def test_anonymize_ip_handles_ipv6(self):
        """IPv6 addresses should be handled."""
        ip = "2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        hash_result = anonymize_ip(ip)
        assert len(hash_result) == 12
        assert hash_result != "unknown"

    def test_anonymize_ip_is_not_reversible(self):
        """Hash must not equal the raw IP; output is a hex hash, not the input."""
        ip = "192.168.1.100"
        hash_result = anonymize_ip(ip)
        # Irreversibility: hashed value must not equal or reveal the original IP
        assert hash_result != ip
        assert len(hash_result) == 12
        # Hash is hex; original IP string must not appear verbatim in the result
        assert ip not in hash_result


class TestUserAgentClassification:
    """Tests for User-Agent string classification."""

    # Bot User-Agents
    BOT_USER_AGENTS = [
        ("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "bot", "googlebot"),
        ("Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)", "bot", "bingbot"),
        ("facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)", "bot", "facebookbot"),
        ("Twitterbot/1.0", "bot", "twitterbot"),
        ("python-requests/2.28.0", "bot", "python_requests"),
        ("curl/7.68.0", "bot", "curl"),
        ("Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)", "bot", "slackbot"),
        ("GPTBot/1.0 (+https://openai.com/gptbot)", "bot", "chatgpt"),
        ("CCBot/2.0 (https://commoncrawl.org/faq/)", "bot", "generic_bot"),
        ("Scrapy/2.5.0 (+https://scrapy.org)", "bot", "scrapy"),
    ]

    # Browser User-Agents
    BROWSER_USER_AGENTS = [
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "browser", "chrome"),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15", "browser", "safari"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0", "browser", "firefox"),
        ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0", "browser", "edge"),
    ]

    # Suspicious User-Agents
    SUSPICIOUS_USER_AGENTS = [
        ("", "suspicious", "empty_ua"),
        ("-", "suspicious", "suspicious_pattern"),
    ]

    @pytest.mark.parametrize("ua,expected_category,expected_type", BOT_USER_AGENTS)
    def test_classify_bot_user_agents(self, ua, expected_category, expected_type):
        """Bot User-Agents should be classified correctly."""
        category, ua_type = classify_user_agent(ua)
        assert category == expected_category, f"Expected category '{expected_category}' for UA: {ua}"
        assert ua_type == expected_type, f"Expected type '{expected_type}' for UA: {ua}"

    @pytest.mark.parametrize("ua,expected_category,expected_type", BROWSER_USER_AGENTS)
    def test_classify_browser_user_agents(self, ua, expected_category, expected_type):
        """Browser User-Agents should be classified correctly."""
        category, ua_type = classify_user_agent(ua)
        assert category == expected_category, f"Expected category '{expected_category}' for UA: {ua}"
        assert ua_type == expected_type, f"Expected type '{expected_type}' for UA: {ua}"

    @pytest.mark.parametrize("ua,expected_category,expected_type", SUSPICIOUS_USER_AGENTS)
    def test_classify_suspicious_user_agents(self, ua, expected_category, expected_type):
        """Suspicious User-Agents should be flagged."""
        category, ua_type = classify_user_agent(ua)
        assert category == expected_category, f"Expected category '{expected_category}' for UA: {ua}"

    def test_classify_unknown_user_agent(self):
        """Unknown User-Agents should be classified as unknown."""
        ua = "SomeRandomApp/1.0"
        category, ua_type = classify_user_agent(ua)
        assert category == "unknown"

    def test_classify_none_user_agent(self):
        """None User-Agent should be classified as suspicious."""
        category, ua_type = classify_user_agent(None)
        assert category == "suspicious"
        assert ua_type == "empty_ua"


class TestUserAgentDetailsParsing:
    """Tests for parsing User-Agent details (OS, device type)."""

    def test_parse_windows_desktop(self):
        """Windows desktop should be detected."""
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        details = parse_user_agent_details(ua)
        assert details["os"] == "windows"
        assert details["device_type"] == "desktop"

    def test_parse_macos_desktop(self):
        """macOS desktop should be detected."""
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        details = parse_user_agent_details(ua)
        assert details["os"] == "macos"
        assert details["device_type"] == "desktop"

    def test_parse_linux_desktop(self):
        """Linux desktop should be detected."""
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        details = parse_user_agent_details(ua)
        assert details["os"] == "linux"
        assert details["device_type"] == "desktop"

    def test_parse_android_mobile(self):
        """Android mobile should be detected."""
        ua = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Mobile"
        details = parse_user_agent_details(ua)
        assert details["os"] == "android"
        assert details["device_type"] == "mobile"

    def test_parse_iphone_mobile(self):
        """iPhone should be detected as iOS mobile."""
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        details = parse_user_agent_details(ua)
        assert details["os"] == "ios"
        assert details["device_type"] == "mobile"

    def test_parse_ipad_tablet(self):
        """iPad should be detected as iOS tablet."""
        ua = "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
        details = parse_user_agent_details(ua)
        assert details["os"] == "ios"
        assert details["device_type"] == "tablet"

    def test_parse_empty_user_agent(self):
        """Empty User-Agent should return unknown for both."""
        details = parse_user_agent_details("")
        assert details["os"] == "unknown"
        assert details["device_type"] == "unknown"


class TestGetClientIP:
    """Tests for extracting client IP from request."""

    def test_get_client_ip_direct(self):
        """Direct connection should use remote_addr."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        mock_request.remote_addr = "192.168.1.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_proxied(self):
        """Proxied request should use X-Forwarded-For."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "10.0.0.1, 192.168.1.1"
        mock_request.remote_addr = "127.0.0.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "10.0.0.1"  # First IP in chain

    def test_get_client_ip_single_proxy(self):
        """Single proxy should use the forwarded IP."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "203.0.113.50"
        mock_request.remote_addr = "127.0.0.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.50"

    def test_get_client_ip_missing(self):
        """Missing IP should return 'unknown'."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        mock_request.remote_addr = None
        
        ip = get_client_ip(mock_request)
        assert ip == "unknown"


class TestBotDetectionHelpers:
    """Tests for helper functions."""

    def test_is_likely_bot_with_bot_ua(self):
        """Bot User-Agent should return True."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Googlebot/2.1"
        
        result = is_likely_bot(mock_request)
        assert result is True

    def test_is_likely_bot_with_browser_ua(self):
        """Browser User-Agent should return False."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        
        result = is_likely_bot(mock_request)
        assert result is False

    def test_is_likely_bot_with_suspicious_ua(self):
        """Suspicious User-Agent should return True."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        
        result = is_likely_bot(mock_request)
        assert result is True

    def test_get_request_classification(self):
        """Should return full classification info."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
        
        result = get_request_classification(mock_request)
        assert "category" in result
        assert "type" in result
        assert "is_bot" in result
        assert "os" in result
        assert "device" in result
        assert result["is_bot"] is False


class TestBotSignatures:
    """Tests for bot signature patterns."""

    def test_all_bot_signatures_are_valid_regex(self):
        """All bot signatures should be valid regex patterns."""
        import re
        for name, pattern in BOT_SIGNATURES.items():
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"Invalid regex for {name}: {pattern} - {e}")

    def test_all_browser_signatures_are_valid_regex(self):
        """All browser signatures should be valid regex patterns."""
        import re
        for name, pattern in BROWSER_SIGNATURES.items():
            try:
                re.compile(pattern)
            except re.error as e:
                pytest.fail(f"Invalid regex for {name}: {pattern} - {e}")


class TestPrivacyGuarantees:
    """Tests to verify privacy guarantees are maintained."""

    def test_anonymize_ip_no_raw_ip_stored(self):
        """Verify that raw IP is never in the hash output."""
        test_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "2001:0db8:85a3::8a2e:0370:7334",
        ]
        
        for ip in test_ips:
            hash_result = anonymize_ip(ip)
            # Ensure no part of the IP appears in the hash
            ip_parts = ip.replace(":", ".").split(".")
            for part in ip_parts:
                if len(part) > 2:  # Only check meaningful parts
                    assert part not in hash_result, f"IP part '{part}' found in hash for {ip}"

    def test_hash_length_limits_uniqueness_exposure(self):
        """12-char hash provides sufficient but limited uniqueness."""
        hash_result = anonymize_ip("192.168.1.1")
        # 12 hex characters = 48 bits = enough for pattern detection
        # but not enough to be a unique global identifier
        assert len(hash_result) == 12
        assert all(c in "0123456789abcdef" for c in hash_result)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_long_user_agent(self):
        """Very long User-Agent should be handled."""
        long_ua = "Mozilla/5.0 " + "x" * 10000
        category, ua_type = classify_user_agent(long_ua)
        # Should not raise an exception
        assert category in ["bot", "browser", "suspicious", "unknown"]

    def test_user_agent_with_special_characters(self):
        """User-Agent with special characters should be handled."""
        ua = "Bot/1.0 (compatible; +http://example.com?a=1&b=2)"
        category, ua_type = classify_user_agent(ua)
        assert category == "bot"

    def test_case_insensitive_matching(self):
        """Bot detection should be case-insensitive."""
        ua1 = "GOOGLEBOT/2.1"
        ua2 = "googlebot/2.1"
        ua3 = "GoOgLeBoT/2.1"
        
        for ua in [ua1, ua2, ua3]:
            category, ua_type = classify_user_agent(ua)
            assert category == "bot"
            assert ua_type == "googlebot"
