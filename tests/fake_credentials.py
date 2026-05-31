"""
Fake credentials for pytest only (SQLite in-memory, no production DB).

These values must never be used outside tests. GitGuardian / secret scanners
should ignore the tests/ tree via .gitguardian.yml.
"""

TEST_SECRET_KEY = "pytest-only-not-a-real-flask-secret-key"
TEST_ADMIN_PASSWORD = "pytest-only-admin-password-not-real"
TEST_USER_PASSWORD = "pytest-only-user-password-not-real"
TEST_NEW_USER_PASSWORD = "pytest-only-new-user-password-not-real"
TEST_WRONG_PASSWORD = "pytest-only-wrong-password-for-negative-test"

TEST_ADMIN_USERNAME = "admin"
TEST_USER_USERNAME = "user"
