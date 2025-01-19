import os
import sys
import pytest
from unittest.mock import patch

# Add the tests directory to the Python path
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    """Disable rate limiting for all tests."""
    with patch("flask_limiter.extension.Limiter.exempt", return_value=True):
        yield
