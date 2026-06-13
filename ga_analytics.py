"""
Google Analytics 4 Data API helper for the admin dashboard.

Fetches aggregated metrics (active users, engagement, traffic sources, devices,
geography, top pages, events) for display in the Visitor analytics card.
Uses the service account in GOOGLE_APPLICATION_CREDENTIALS and the GA4 Property ID.
Callers should cache the result (e.g. 15 minutes).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )
    _GA_AVAILABLE = True
except ImportError:
    _GA_AVAILABLE = False


def _int_val(metric_values, index: int) -> int:
    if index < len(metric_values):
        return int(metric_values[index].value or 0)
    return 0


def _float_val(metric_values, index: int) -> float:
    if index < len(metric_values):
        return float(metric_values[index].value or 0)
    return 0.0


def _order_by_metric(metric_name: str) -> "OrderBy":
    return OrderBy(
        metric=OrderBy.MetricOrderBy(metric_name=metric_name),
        desc=True,
    )


def _parse_active_users_by_date_range(response) -> dict[str, int]:
    """
    Parse activeUsers from a multi-date-range report.

    GA4 adds an implicit dateRange dimension and returns one row per range,
    each with a single metric value (date_range_0, date_range_1, ...).
    """
    users: dict[str, int] = {}
    for row in response.rows:
        if not row.metric_values:
            continue
        date_range_key = "date_range_0"
        if len(row.dimension_values) > 1:
            date_range_key = row.dimension_values[1].value or date_range_key
        elif row.dimension_values:
            value = row.dimension_values[0].value or ""
            if value.startswith("date_range_"):
                date_range_key = value
        users[date_range_key] = _int_val(row.metric_values, 0)
    return users


def get_ga_dashboard_data(property_id: Optional[str]) -> Optional[dict[str, Any]]:
    """
    Fetch GA4 metrics for the admin dashboard.

    Returns a flat dict of overview, acquisition, audience, content, and event
    metrics. Each report is fetched independently so one failure does not break
    others. Returns None when GA is unavailable or every report fails.
    """
    if not _GA_AVAILABLE or not property_id or not str(property_id).strip():
        return None

    property_name = f"properties/{str(property_id).strip()}"
    end = datetime.now(timezone.utc).date()
    start_7 = end - timedelta(days=6)
    date_range_7d = DateRange(start_date=start_7.isoformat(), end_date=end.isoformat())
    date_range_today = DateRange(start_date=end.isoformat(), end_date=end.isoformat())

    try:
        client = BetaAnalyticsDataClient()
    except Exception as e:
        logging.warning("GA Analytics: could not create client: %s", e)
        return None

    result: dict[str, Any] = {
        "active_users_7d": 0,
        "active_users_1d": 0,
        "sessions": 0,
        "engaged_sessions": 0,
        "average_session_duration_seconds": 0.0,
        "bounce_rate": 0.0,
        "traffic_sources": [],
        "devices": [],
        "countries": [],
        "top_pages": [],
        "top_events": [],
    }
    sections_ok = 0

    # -- Active users (7d and today) -----------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[],
            metrics=[Metric(name="activeUsers")],
            date_ranges=[date_range_7d, date_range_today],
        ))
        users_by_range = _parse_active_users_by_date_range(response)
        result["active_users_7d"] = users_by_range.get("date_range_0", 0)
        result["active_users_1d"] = users_by_range.get("date_range_1", 0)
        if users_by_range:
            sections_ok += 1
    except Exception as e:
        logging.warning("GA Analytics: active users report failed: %s", e)

    # -- Engagement overview -----------------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[],
            metrics=[
                Metric(name="sessions"),
                Metric(name="engagedSessions"),
                Metric(name="averageSessionDuration"),
                Metric(name="bounceRate"),
            ],
            date_ranges=[date_range_7d],
        ))
        if response.rows and response.rows[0].metric_values:
            mv = response.rows[0].metric_values
            result["sessions"] = _int_val(mv, 0)
            result["engaged_sessions"] = _int_val(mv, 1)
            result["average_session_duration_seconds"] = _float_val(mv, 2)
            result["bounce_rate"] = round(_float_val(mv, 3) * 100, 1)
            sections_ok += 1
    except Exception as e:
        logging.warning("GA Analytics: engagement report failed: %s", e)

    # -- Acquisition (traffic sources) -------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="firstUserDefaultChannelGroup")],
            metrics=[Metric(name="sessions"), Metric(name="newUsers")],
            date_ranges=[date_range_7d],
            order_bys=[_order_by_metric("sessions")],
            limit=10,
        ))
        for row in response.rows:
            channel = row.dimension_values[0].value if row.dimension_values else "(not set)"
            result["traffic_sources"].append({
                "channel": channel or "(not set)",
                "sessions": _int_val(row.metric_values, 0),
                "new_users": _int_val(row.metric_values, 1),
            })
        if response.rows:
            sections_ok += 1
    except Exception as e:
        logging.warning("GA Analytics: acquisition report failed: %s", e)

    # -- Audience: devices -------------------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="sessions")],
            date_ranges=[date_range_7d],
            order_bys=[_order_by_metric("sessions")],
            limit=5,
        ))
        for row in response.rows:
            device = row.dimension_values[0].value if row.dimension_values else "unknown"
            result["devices"].append({
                "device": (device or "unknown").title(),
                "sessions": _int_val(row.metric_values, 0),
            })
        if response.rows:
            sections_ok += 1
    except Exception as e:
        logging.warning("GA Analytics: devices report failed: %s", e)

    # -- Audience: countries -----------------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="sessions")],
            date_ranges=[date_range_7d],
            order_bys=[_order_by_metric("sessions")],
            limit=10,
        ))
        for row in response.rows:
            country = row.dimension_values[0].value if row.dimension_values else ""
            if country and country != "(not set)":
                result["countries"].append({
                    "country": country,
                    "sessions": _int_val(row.metric_values, 0),
                })
        if result["countries"]:
            sections_ok += 1
    except Exception as e:
        logging.warning("GA Analytics: countries report failed: %s", e)

    # -- Content: top pages with titles ------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="pagePath"), Dimension(name="pageTitle")],
            metrics=[Metric(name="screenPageViews")],
            date_ranges=[date_range_7d],
            order_bys=[_order_by_metric("screenPageViews")],
            limit=10,
        ))
        for row in response.rows:
            path = row.dimension_values[0].value if row.dimension_values else ""
            title = row.dimension_values[1].value if len(row.dimension_values) > 1 else ""
            if not title or title == "(not set)":
                title = path or "(not set)"
            result["top_pages"].append({
                "path": path or "(not set)",
                "title": title,
                "views": _int_val(row.metric_values, 0),
            })
        if response.rows:
            sections_ok += 1
    except Exception as e:
        logging.warning("GA Analytics: top pages report failed: %s", e)

    # -- Events (future-ready) ---------------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            date_ranges=[date_range_7d],
            order_bys=[_order_by_metric("eventCount")],
            limit=10,
        ))
        for row in response.rows:
            event_name = row.dimension_values[0].value if row.dimension_values else ""
            if event_name:
                result["top_events"].append({
                    "event_name": event_name,
                    "count": _int_val(row.metric_values, 0),
                })
        if result["top_events"]:
            sections_ok += 1
    except Exception as e:
        logging.warning("GA Analytics: events report failed: %s", e)

    if sections_ok == 0:
        return None

    return result
