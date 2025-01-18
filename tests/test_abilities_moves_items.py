import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


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
