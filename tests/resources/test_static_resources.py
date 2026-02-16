import pytest


def test_static_resources_integration(client):
    """Test that CSS and JS files are properly linked in the HTML."""
    response = client.get("/")  # or any other route that includes the base template

    # Assert that the response status is OK
    assert response.status_code == 200

    # Check for CSS file link
    assert b'<link rel="stylesheet" href="/static/css/styles.css">' in response.data

    # Check for JavaScript file link (search.js is loaded by search.html partial)
    assert b'<script src="/static/js/search.js"></script>' in response.data

    # Optionally, check for Bootstrap or other resources if needed
    assert b'<link rel="stylesheet" href="/static/css/bootstrap.css">' in response.data
    assert (
        b'<script src="/static/vendor/jquery/jquery-3.7.1.js"></script>'
        in response.data
    )


def test_no_static_resources_js_in_head(client):
    """Verify that base.html no longer loads the static resources.js file.

    Search is now powered by the /api/search endpoint, so the old static
    resources.js (which shipped the full resource list to the client) is
    no longer included in the <head>.
    """
    response = client.get("/")
    assert response.status_code == 200
    # The old static script tag should NOT be present
    assert b'js/resources.js"></script>' not in response.data
