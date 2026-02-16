# routes/decorators.py
# -*- coding: utf-8 -*-
"""Reusable decorators for route handlers.

Consolidates the repeated try/except error-handling pattern that appears
in nearly every route handler across 16+ blueprint files.

Design rationale:
  - Every detail route follows the same pattern: try to fetch data,
    catch ValueError/HTTPError/Exception, and abort with the right status.
  - Duplicating this logic creates inconsistency (some routes return tuples,
    some use abort(), some forget HTTPError handling entirely).
  - A decorator centralises this logic so route functions only contain
    the happy path, making them easier to read and maintain.

Usage:
    from routes.decorators import handle_api_errors

    @bp.route("/pokemon/<id_or_name>")
    @handle_api_errors("Pokemon")
    def get_pokemon(id_or_name):
        data = APIResource.fetch_data("pokemon", id_or_name)
        return render_template("pokemon_detail.html", data=data)
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable

from flask import abort
from requests.exceptions import HTTPError
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def handle_api_errors(resource_name: str) -> Callable[..., Any]:
    """Decorator that catches common API errors and returns HTTP responses.

    Handles three exception types consistently:

    1. **ValueError** - Raised by APIResource.fetch_data when a resource
       is not found or the input is invalid.
       - If the message contains "not found" -> 404
       - Otherwise -> 400 (bad request / invalid input)

    2. **HTTPError** (requests library) - Raised on upstream API failures.
       - If upstream returned 404 -> 404
       - Otherwise -> 500

    3. **Exception** (catch-all) - Unexpected errors.
       - Always -> 500

    werkzeug HTTPExceptions (from abort() calls inside the route) are
    re-raised without modification so Flask handles them normally.

    Args:
        resource_name: Human-readable name for error messages
                       (e.g. "Pokemon", "Move", "Ability").
    """
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            try:
                return f(*args, **kwargs)
            except HTTPException:
                # Re-raise Flask's own abort() calls untouched
                raise
            except ValueError as e:
                msg = str(e)
                if "not found" in msg.lower():
                    logger.debug("Not found: %s — %s", resource_name, msg)
                    abort(404, description=msg)
                logger.warning("Bad request for %s: %s", resource_name, msg)
                abort(400, description=msg)
            except HTTPError as e:
                status = getattr(e.response, "status_code", 500)
                if status == 404:
                    logger.debug("Upstream 404 for %s", resource_name)
                    abort(404, description=f"{resource_name} not found")
                logger.error("Upstream HTTP %d for %s: %s", status, resource_name, e)
                abort(500, description=f"Error fetching {resource_name}")
            except Exception as e:
                logger.exception("Unexpected error in %s handler: %s", resource_name, e)
                abort(500, description="An unexpected error occurred")
        return wrapped
    return decorator
