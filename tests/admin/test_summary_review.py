import pytest
from models.model import Resource, db
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import List, Optional, Dict


# Mock OpenAI response types
@dataclass
class ChatCompletionMessage:
    content: str
    role: str
    function_call: Optional[dict] = None
    tool_calls: Optional[List] = None


@dataclass
class CompletionChoice:
    message: ChatCompletionMessage
    finish_reason: str
    index: int
    logprobs: Optional[dict] = None


@dataclass
class ChatCompletion:
    id: str
    choices: List[CompletionChoice]
    created: int
    model: str
    object: str
    system_fingerprint: Optional[str] = None
    usage: Optional[Dict[str, int]] = None


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    message = ChatCompletionMessage(
        content="Updated by AI", role="assistant", function_call=None, tool_calls=None
    )
    choice = CompletionChoice(
        finish_reason="stop",
        index=0,
        message=message,
        logprobs=None,
    )
    return ChatCompletion(
        id="test",
        choices=[choice],
        created=1234567890,
        model="gpt-4",
        object="chat.completion",
        system_fingerprint=None,
        usage={"completion_tokens": 10, "prompt_tokens": 20, "total_tokens": 30},
    )


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


@patch("routes.summary_generators.pokemon.get_openai_client")
@patch("routes.summary_generators.utils.get_openai_client")
def test_summary_update_with_custom_instructions(
    mock_get_client_utils, mock_get_client_pokemon, auth_client, app, mock_openai_response
):
    """Test summary update with custom instructions and token limit"""
    # Set up mock OpenAI client
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_openai_response
    mock_get_client_utils.return_value = mock_client
    mock_get_client_pokemon.return_value = mock_client

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


def test_edit_summary(auth_client, app):
    """Test the edit summary functionality"""
    with app.app_context():
        # Create test resource
        resource = Resource(resource="pokemon", name="test", summary="Original summary")
        db.session.add(resource)
        db.session.commit()

        # Test accessing edit page
        response = auth_client.get(
            "/summary-review/pokemon/test/edit",
            query_string={"return_to": "/pokemon/test"},
        )
        assert response.status_code == 200
        assert b"Original summary" in response.data
        assert b"New Summary (Edit)" in response.data

        # Test accepting edited summary
        response = auth_client.post(
            "/summary-review/pokemon/test",
            data={
                "action": "accept",
                "edited_summary": "Edited summary",
            },
            query_string={"return_to": "/pokemon/test"},
        )
        assert response.status_code == 302
        assert response.location == "/pokemon/test"

        # Verify database update
        updated = Resource.query.filter_by(resource="pokemon", name="test").first()
        assert updated.summary == "Edited summary"
