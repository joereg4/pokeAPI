import pytest
from limiter import limiter

from tests.fake_credentials import (
    TEST_ADMIN_PASSWORD,
    TEST_ADMIN_USERNAME,
    TEST_USER_PASSWORD,
    TEST_USER_USERNAME,
    TEST_WRONG_PASSWORD,
)


def test_login_page(client):
    """Test that login page loads correctly."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_successful_login(client, regular_user):
    """Test successful login with correct credentials."""
    response = client.post(
        "/auth/login",
        data={"username": TEST_USER_USERNAME, "password": TEST_USER_PASSWORD},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logged in successfully!" in response.data


def test_login_invalid_username(client):
    """Test login with non-existent username."""
    response = client.post(
        "/auth/login",
        data={"username": "nonexistent", "password": TEST_WRONG_PASSWORD},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_login_wrong_password(client, regular_user):
    """Test login with wrong password."""
    response = client.post(
        "/auth/login",
        data={"username": TEST_USER_USERNAME, "password": TEST_WRONG_PASSWORD},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_logout(auth_client):
    """Test logout functionality."""
    response = auth_client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out." in response.data


def test_login_required(client):
    """Test that protected routes require login."""
    # First get the response without following redirects
    response = client.get("/admin/dashboard")
    assert response.status_code == 302
    assert "/auth/login" in response.location

    # Now follow the redirect and check the flash message
    with client.session_transaction() as session:
        # Clear any existing flashed messages
        session.pop("_flashes", None)

    response = client.get("/admin/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"You must be logged in to access this page." in response.data


def test_already_logged_in(auth_client):
    """Test that logged-in users can still access the login page."""
    response = auth_client.get("/auth/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_remember_me_functionality(client, admin_user):
    """Test that login works without remember me functionality."""
    response = client.post(
        "/auth/login",
        data={"username": TEST_ADMIN_USERNAME, "password": TEST_ADMIN_PASSWORD},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Logged in successfully!" in response.data

    # Check that session exists
    with client.session_transaction() as session:
        assert "_user_id" in session
        assert session["_user_id"] == str(admin_user.id)

    # Test logout
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out." in response.data

    # Verify session is cleared
    with client.session_transaction() as session:
        assert "_user_id" not in session
