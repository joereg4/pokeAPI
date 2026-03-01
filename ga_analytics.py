"""
Google Analytics 4 Data API helper for the admin dashboard.

Fetches aggregated metrics (active users, top pages) for display in the
Visitor analytics card. Uses the service account in GOOGLE_APPLICATION_CREDENTIALS
and the GA4 Property ID. Callers should cache the result (e.g. 15 minutes).
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


def get_ga_dashboard_data(property_id: Optional[str]) -> Optional[dict[str, Any]]:
    """
    Fetch GA4 metrics for the admin dashboard.

    Args:
        property_id: GA4 Property ID (numeric string, e.g. "123456789").
                     Will be formatted as "properties/123456789".

    Returns:
        Dict with active_users_7d, active_users_1d, top_pages (list of {path, views}),
        or None if disabled, missing credentials, or API error.
    """
    if not _GA_AVAILABLE or not property_id or not str(property_id).strip():
        return None

    property_name = f"properties/{str(property_id).strip()}"
    end = datetime.utcnow().date()
    start_7 = end - timedelta(days=7)
    start_1 = end - timedelta(days=1)

    try:
        client = BetaAnalyticsDataClient()
    except Exception as e:
        logging.warning("GA Analytics: could not create client: %s", e)
        return None

    result = {
        "active_users_7d": 0,
        "active_users_1d": 0,
        "top_pages": [],
    }

    try:
        # Active users last 7 days and last 1 day
        request = RunReportRequest(
            property=property_name,
            dimensions=[],
            metrics=[
                Metric(name="activeUsers"),
            ],
            date_ranges=[
                DateRange(start_date=start_7.isoformat(), end_date=end.isoformat()),
                DateRange(start_date=start_1.isoformat(), end_date=end.isoformat()),
            ],
        )
        response = client.run_report(request)
        if response.rows and response.rows[0].metric_values:
            mv = response.rows[0].metric_values
            result["active_users_7d"] = int(mv[0].value or 0) if len(mv) > 0 else 0
            result["active_users_1d"] = int(mv[1].value or 0) if len(mv) > 1 else 0
    except Exception as e:
        logging.warning("GA Analytics: run_report (active users) failed: %s", e)
        return None

    try:
        # Top 10 pages by page views (last 7 days)
        request = RunReportRequest(
            property=property_name,
            dimensions=[Dimension(name="pagePath")],
            metrics=[Metric(name="screenPageViews")],
            date_ranges=[DateRange(start_date=start_7.isoformat(), end_date=end.isoformat())],
            limit=10,
        )
        response = client.run_report(request)
        for row in response.rows:
            path = row.dimension_values[0].value if row.dimension_values else ""
            views = int(row.metric_values[0].value or 0) if row.metric_values else 0
            result["top_pages"].append({"path": path or "(not set)", "views": views})
    except Exception as e:
        logging.warning("GA Analytics: run_report (top pages) failed: %s", e)

    return result
