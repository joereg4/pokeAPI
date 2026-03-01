"""
Google Analytics 4 Data API helper for the admin dashboard.

Fetches aggregated metrics (active users, engagement, traffic sources, devices,
geography, top pages, events) for display in the Visitor analytics card.
Uses the service account in GOOGLE_APPLICATION_CREDENTIALS and the GA4 Property ID.
Callers should cache the result (e.g. 15 minutes).
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
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


def get_ga_dashboard_data(property_id: Optional[str]) -> Optional[dict[str, Any]]:
    """
    Fetch GA4 metrics for the admin dashboard.

    Returns a dict with sections: overview, acquisition, audience, content,
    and events. Each section is fetched independently so one failure does not
    break others.
    """
    if not _GA_AVAILABLE or not property_id or not str(property_id).strip():
        return None

    property_name = f"properties/{str(property_id).strip()}"
    end = datetime.utcnow().date()
    start_7 = end - timedelta(days=7)
    start_1 = end - timedelta(days=1)
    date_range_7d = DateRange(start_date=start_7.isoformat(), end_date=end.isoformat())
    date_range_1d = DateRange(start_date=start_1.isoformat(), end_date=end.isoformat())

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

    # -- Active users (7d and 1d) ------------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[],
            metrics=[Metric(name="activeUsers")],
            date_ranges=[date_range_7d, date_range_1d],
        ))
        if response.rows and response.rows[0].metric_values:
            mv = response.rows[0].metric_values
            result["active_users_7d"] = _int_val(mv, 0)
            result["active_users_1d"] = _int_val(mv, 1)
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
    except Exception as e:
        logging.warning("GA Analytics: engagement report failed: %s", e)

    # -- Acquisition (traffic sources) -------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="firstUserDefaultChannelGroup")],
            metrics=[Metric(name="sessions"), Metric(name="newUsers")],
            date_ranges=[date_range_7d],
            limit=10,
        ))
        for row in response.rows:
            channel = row.dimension_values[0].value if row.dimension_values else "(not set)"
            result["traffic_sources"].append({
                "channel": channel or "(not set)",
                "sessions": _int_val(row.metric_values, 0),
                "new_users": _int_val(row.metric_values, 1),
            })
    except Exception as e:
        logging.warning("GA Analytics: acquisition report failed: %s", e)

    # -- Audience: devices -------------------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="sessions")],
            date_ranges=[date_range_7d],
            limit=5,
        ))
        for row in response.rows:
            device = row.dimension_values[0].value if row.dimension_values else "unknown"
            result["devices"].append({
                "device": (device or "unknown").title(),
                "sessions": _int_val(row.metric_values, 0),
            })
    except Exception as e:
        logging.warning("GA Analytics: devices report failed: %s", e)

    # -- Audience: countries -----------------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="sessions")],
            date_ranges=[date_range_7d],
            limit=10,
        ))
        for row in response.rows:
            country = row.dimension_values[0].value if row.dimension_values else ""
            if country and country != "(not set)":
                result["countries"].append({
                    "country": country,
                    "sessions": _int_val(row.metric_values, 0),
                })
    except Exception as e:
        logging.warning("GA Analytics: countries report failed: %s", e)

    # -- Content: top pages with titles ------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="pagePath"), Dimension(name="pageTitle")],
            metrics=[Metric(name="screenPageViews")],
            date_ranges=[date_range_7d],
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
    except Exception as e:
        logging.warning("GA Analytics: top pages report failed: %s", e)

    # -- Events (future-ready) ---------------------------------------------
    try:
        response = client.run_report(RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            date_ranges=[date_range_7d],
            limit=10,
        ))
        for row in response.rows:
            event_name = row.dimension_values[0].value if row.dimension_values else ""
            if event_name:
                result["top_events"].append({
                    "event_name": event_name,
                    "count": _int_val(row.metric_values, 0),
                })
    except Exception as e:
        logging.warning("GA Analytics: events report failed: %s", e)

    return result
