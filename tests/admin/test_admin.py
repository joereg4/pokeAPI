import pytest
from flask import url_for
from models.model import User, db


def test_admin_dashboard_access(auth_client):
    """Test that admin can access dashboard."""
    response = auth_client.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data
    assert b"User Management" in response.data


def test_non_admin_dashboard_access(regular_auth_client):
    """Test that non-admin users cannot access dashboard."""
    response = regular_auth_client.get("/admin/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"You need admin privileges to access this page." in response.data


def test_add_user(auth_client):
    """Test adding a new user."""
    response = auth_client.post(
        "/admin/users/add",
        data={
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "password123",
            "is_admin": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"User added successfully" in response.data
    assert b"newuser" in response.data


def test_add_duplicate_username(auth_client, regular_user):
    """Test adding a user with existing username."""
    response = auth_client.post(
        "/admin/users/add",
        data={
            "username": "user",  # This username already exists
            "email": "another@test.com",
            "password": "password123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Username already exists" in response.data


def test_add_duplicate_email(auth_client, regular_user):
    """Test adding a user with existing email."""
    response = auth_client.post(
        "/admin/users/add",
        data={
            "username": "another",
            "email": "user@test.com",  # This email already exists
            "password": "password123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Email already exists" in response.data


def test_edit_user(auth_client, regular_user):
    """Test editing an existing user."""
    response = auth_client.post(
        f"/admin/users/{regular_user.id}/edit",
        data={
            "username": "updated_user",
            "email": "updated@test.com",
            "is_admin": "on",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"User updated successfully" in response.data
    assert b"updated_user" in response.data
    assert b"updated@test.com" in response.data


def test_delete_user(auth_client, regular_user):
    """Test deleting a user."""
    response = auth_client.post(
        f"/admin/users/{regular_user.id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"User deleted successfully" in response.data

    # Verify the user no longer exists in the database
    deleted_user = db.session.get(User, regular_user.id)
    assert deleted_user is None


def test_cannot_delete_self(auth_client, admin_user):
    """Test that admin cannot delete their own account."""
    response = auth_client.post(
        f"/admin/users/{admin_user.id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"You cannot delete your own account" in response.data


def test_edit_nonexistent_user(auth_client):
    """Test editing a non-existent user."""
    response = auth_client.post(
        "/admin/users/9999/edit",
        data={"username": "test", "email": "test@test.com"},
        follow_redirects=True,
    )
    assert response.status_code == 404


def test_delete_nonexistent_user(auth_client):
    """Test deleting a non-existent user."""
    response = auth_client.post("/admin/users/9999/delete", follow_redirects=True)
    assert response.status_code == 404
