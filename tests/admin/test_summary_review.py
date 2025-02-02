import pytest
from models.model import Resource, db


@pytest.fixture
def test_resources(app):
    with app.app_context():
        resources = [
            Resource(resource="pokemon", name="test1", summary="Summary 1"),
            Resource(resource="pokemon", name="test2", summary="Summary 2"),
            Resource(resource="pokemon", name="other", summary="Summary 3"),
        ]
        db.session.add_all(resources)
        db.session.commit()

        yield resources

        # Cleanup
        db.session.query(Resource).delete()
        db.session.commit()


def test_render_markdown_endpoint(auth_client):
    """Test the markdown rendering endpoint"""
    # Test valid markdown
    test_md = "**Bold** text"
    response = auth_client.post(
        "/render-markdown",
        json={"text": test_md},
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert b"<p><strong>Bold</strong> text</p>" in response.data


def test_summary_update_with_custom_instructions(auth_client, app):
    """Test summary update with custom instructions and token limit"""
    with app.app_context():
        # Create test resource using test db session
        resource = Resource(resource="pokemon", name="test", summary="Original summary")
        db.session.add(resource)
        db.session.commit()

        # Test update with custom settings
        response = auth_client.post(
            "/summary-review/pokemon/test",
            data={
                "max_tokens": 3000,
                "custom_instructions": "Make it more detailed",
            },
            query_string={"return_to": "/pokemon/test"},
        )
        assert response.status_code == 200

        # Test accepting edited summary
        response = auth_client.post(
            "/summary-review/pokemon/test",
            data={
                "action": "accept",
                "edited_summary": "Updated summary",
            },
            query_string={"return_to": "/pokemon/test"},
        )
        assert response.status_code == 302
        assert response.location == "/pokemon/test"

        # Verify database update
        updated = Resource.query.filter_by(resource="pokemon", name="test").first()
        assert updated.summary == "Updated summary"


def test_summary_review_search(auth_client, test_resources):
    """Test the summary review search functionality"""
    response = auth_client.get("/summary-review", query_string={"search": "test"})
    assert response.status_code == 200
    assert b"test1" in response.data
    assert b"test2" in response.data
    assert b"other" not in response.data


def test_summary_review_unauthorized(client):
    """Test unauthorized access to summary review"""
    response = client.get("/summary-review")
    assert response.status_code == 302
    assert "/auth/login" in response.location
