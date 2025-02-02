import pytest
from app import create_app
from utils import get_cache_stats, warm_common_endpoints
from models.model import db


@pytest.fixture
def client():
    test_config = {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
        "LOGIN_DISABLED": False,
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 300,
    }
    app = create_app(test_config)

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_ability_route(client):
    # Test with ID
    response = client.get("/ability/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/ability/stench")
    assert response.status_code == 200

    # Test non-existent ability
    response = client.get("/ability/nonexistent")
    assert response.status_code == 404


def test_item_route(client):
    # Test with ID
    response = client.get("/item/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/item/master-ball")
    assert response.status_code == 200

    # Test non-existent item
    response = client.get("/item/nonexistent")
    assert response.status_code == 404


def test_move_route(client):
    # Test with ID
    response = client.get("/move/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/move/pound")
    assert response.status_code == 200

    # Test non-existent move
    response = client.get("/move/nonexistent")
    assert response.status_code == 404


def test_machine_route(client):
    # Test with ID
    response = client.get("/machine/1")
    assert response.status_code == 200

    # Test non-existent machine
    response = client.get("/machine/9999")
    assert response.status_code == 404


def test_move_category_route(client):
    # Test with ID
    response = client.get("/move-category/1")
    assert response.status_code == 200

    # Test with name
    response = client.get("/move-category/damage")
    assert response.status_code == 200

    # Test non-existent category
    response = client.get("/move-category/nonexistent")
    assert response.status_code == 404


# ... continue with other routes
