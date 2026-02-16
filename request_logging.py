# request_logging.py
# -*- coding: utf-8 -*-
"""Structured request logging with unique request IDs.

Attaches a unique request_id to every Flask request so that all log
messages emitted during that request can be correlated.  The ID is
also returned in the X-Request-ID response header for client-side
correlation.

Design rationale:
  - Uses Flask's ``g`` object to store the request_id for the duration
    of the request.  A custom logging.Filter injects it into every
    LogRecord automatically.
  - Accepts an incoming X-Request-ID header (from load balancers /
    reverse proxies) or generates a new UUID if none is present.
  - The structured format makes logs grep-friendly and parseable by
    log aggregation tools (ELK, Datadog, etc.).

Usage:
    from request_logging import init_request_logging

    def create_app():
        app = Flask(__name__)
        init_request_logging(app)
        ...
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from flask import Flask, g, request


class RequestIdFilter(logging.Filter):
    """Inject the current request_id into every log record.

    If no request context is active (e.g. during startup or background
    tasks), falls back to ``-`` so the log format never breaks.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = getattr(g, "request_id", "-")  # type: ignore[attr-defined]
        except RuntimeError:
            # Outside Flask request context
            record.request_id = "-"  # type: ignore[attr-defined]
        return True


# The structured format includes timestamp, level, request_id, logger name,
# and the message.  Keep it single-line for easy grep / tail -f.
STRUCTURED_FORMAT = (
    "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s"
)


def init_request_logging(
    app: Flask,
    level: Optional[int] = None,
) -> None:
    """Wire up structured logging with request IDs to a Flask app.

    Call this once during ``create_app()``.  It:
      1. Adds a ``before_request`` hook that assigns a request_id.
      2. Adds an ``after_request`` hook that sets the X-Request-ID header.
      3. Installs a ``RequestIdFilter`` on the root logger so every
         logger in the process gets the request_id automatically.
      4. Sets a structured log format on the root handler.

    Args:
        app: The Flask application instance.
        level: Override the root log level. If None, keeps the existing level.
    """

    # --- Request hooks ----------------------------------------------------

    @app.before_request
    def _set_request_id() -> None:
        """Assign a unique ID to the current request."""
        # Honour upstream request IDs from load balancers / proxies.
        incoming_id = request.headers.get("X-Request-ID")
        g.request_id = incoming_id or uuid.uuid4().hex[:12]

    @app.after_request
    def _add_request_id_header(response):
        """Echo the request ID back in the response headers."""
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response

    # --- Logging setup ----------------------------------------------------

    request_filter = RequestIdFilter()

    root_logger = logging.getLogger()
    if level is not None:
        root_logger.setLevel(level)

    # Install the filter on each HANDLER (not the logger).  Python's
    # logging propagation bypasses parent-logger filters, but always
    # runs handler filters.  This ensures every log record -- whether
    # from the root logger or a child like "pokedex.api" -- gets the
    # request_id injected before formatting.
    formatter = logging.Formatter(STRUCTURED_FORMAT)
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.addFilter(request_filter)
            handler.setFormatter(formatter)
    else:
        handler = logging.StreamHandler()
        handler.addFilter(request_filter)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
