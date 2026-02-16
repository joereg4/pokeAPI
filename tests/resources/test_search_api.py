"""
Tests for the /api/search endpoint (PostgreSQL-backed navbar search).

Verifies:
  - Empty / missing query returns []
  - Prefix matches rank before substring-only matches
  - Limit parameter is respected
  - Newly inserted resources appear immediately (no stale cache)
  - Endpoint returns valid JSON
"""
import pytest
from models.model import db, Resource


@pytest.fixture
def seeded_client(client):
    """Seed the DB with a handful of resources and return the test client."""
    resources = [
        Resource(resource="pokemon", name="pikachu"),
        Resource(resource="pokemon", name="pidgey"),
        Resource(resource="pokemon", name="charizard"),
        Resource(resource="berry", name="cheri"),
        Resource(resource="ability", name="static"),
        Resource(resource="pokemon", name="raichu"),
        Resource(resource="pokemon-species", name="pikachu"),
    ]
    for r in resources:
        db.session.add(r)
    db.session.commit()
    return client


# ------------------------------------------------------------------
# Basic behaviour
# ------------------------------------------------------------------

def test_empty_query_returns_empty(seeded_client):
    """No query param → empty list."""
    resp = seeded_client.get("/api/search")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_blank_query_returns_empty(seeded_client):
    """Whitespace-only query → empty list."""
    resp = seeded_client.get("/api/search?q=  ")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_no_match_returns_empty(seeded_client):
    """Query that matches nothing → empty list."""
    resp = seeded_client.get("/api/search?q=zzzznotfound")
    assert resp.status_code == 200
    assert resp.get_json() == []


# ------------------------------------------------------------------
# Matching & ranking
# ------------------------------------------------------------------

def test_prefix_match(seeded_client):
    """Typing 'pik' should return pikachu (prefix match)."""
    resp = seeded_client.get("/api/search?q=pik")
    data = resp.get_json()
    names = [r["name"] for r in data]
    assert "pikachu" in names


def test_substring_match(seeded_client):
    """Typing 'chu' should still find pikachu via substring."""
    resp = seeded_client.get("/api/search?q=chu")
    data = resp.get_json()
    names = [r["name"] for r in data]
    # pikachu contains 'chu' (substring), raichu also
    assert "pikachu" in names
    assert "raichu" in names


def test_prefix_ranked_before_substring(seeded_client):
    """Prefix matches should come before substring-only matches."""
    resp = seeded_client.get("/api/search?q=pi")
    data = resp.get_json()
    names = [r["name"] for r in data]
    # 'pikachu' and 'pidgey' start with 'pi' – they should appear before
    # anything that only *contains* 'pi' (if any).
    # At minimum, pikachu should be in the list.
    assert len(names) >= 1
    # All prefix matches should precede any non-prefix match
    prefix_section = True
    for n in names:
        if n.startswith("pi"):
            assert prefix_section, f"{n} is a prefix match but appeared after a non-prefix match"
        else:
            prefix_section = False


# ------------------------------------------------------------------
# Limit
# ------------------------------------------------------------------

def test_default_limit(seeded_client):
    """At most 10 results by default."""
    resp = seeded_client.get("/api/search?q=p")
    data = resp.get_json()
    assert len(data) <= 10


def test_custom_limit(seeded_client):
    """Honour the limit param."""
    resp = seeded_client.get("/api/search?q=pi&limit=1")
    data = resp.get_json()
    assert len(data) == 1


def test_limit_capped_at_50(seeded_client):
    """Limit is capped at 50 even if a higher value is requested."""
    resp = seeded_client.get("/api/search?q=p&limit=999")
    data = resp.get_json()
    assert len(data) <= 50


# ------------------------------------------------------------------
# Freshness – newly inserted resources appear
# ------------------------------------------------------------------

def test_new_resource_appears_in_search(client):
    """Resources added to the DB should appear in the next search."""
    # Initially no results
    resp = client.get("/api/search?q=bulba")
    assert resp.get_json() == []

    # Insert a new resource
    r = Resource(resource="pokemon", name="bulbasaur")
    db.session.add(r)
    db.session.commit()

    # Should now appear
    resp = client.get("/api/search?q=bulba")
    data = resp.get_json()
    assert any(r["name"] == "bulbasaur" for r in data)


# ------------------------------------------------------------------
# Response shape
# ------------------------------------------------------------------

def test_response_shape(seeded_client):
    """Each item should have 'name' and 'type' keys."""
    resp = seeded_client.get("/api/search?q=pikachu")
    data = resp.get_json()
    assert len(data) >= 1
    for item in data:
        assert "name" in item
        assert "type" in item


def test_type_field_matches_resource(seeded_client):
    """The 'type' field should reflect the resource column value."""
    resp = seeded_client.get("/api/search?q=cheri")
    data = resp.get_json()
    cheri = [r for r in data if r["name"] == "cheri"]
    assert len(cheri) == 1
    assert cheri[0]["type"] == "berry"
