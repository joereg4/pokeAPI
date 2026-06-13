"""Tests for GA4 dashboard analytics helper."""

from unittest.mock import MagicMock, patch

import pytest

import ga_analytics


def _metric_value(value):
    metric = MagicMock()
    metric.value = value
    return metric


def _dimension_value(value):
    dimension = MagicMock()
    dimension.value = value
    return dimension


def _row(dimension_values, metric_values):
    row = MagicMock()
    row.dimension_values = dimension_values
    row.metric_values = metric_values
    return row


def _response(rows):
    response = MagicMock()
    response.rows = rows
    return response


class TestParseActiveUsersByDateRange:
    def test_parses_one_row_per_date_range(self):
        response = _response([
            _row([_dimension_value("date_range_0")], [_metric_value("150")]),
            _row([_dimension_value("date_range_1")], [_metric_value("42")]),
        ])

        parsed = ga_analytics._parse_active_users_by_date_range(response)

        assert parsed == {"date_range_0": 150, "date_range_1": 42}

    def test_parses_implicit_date_range_in_second_dimension(self):
        response = _response([
            _row(
                [_dimension_value(""), _dimension_value("date_range_1")],
                [_metric_value("7")],
            ),
        ])

        parsed = ga_analytics._parse_active_users_by_date_range(response)

        assert parsed == {"date_range_1": 7}

    def test_skips_rows_without_metric_values(self):
        response = _response([
            _row([_dimension_value("date_range_0")], []),
            _row([_dimension_value("date_range_1")], [_metric_value("3")]),
        ])

        parsed = ga_analytics._parse_active_users_by_date_range(response)

        assert parsed == {"date_range_1": 3}


@patch("ga_analytics.BetaAnalyticsDataClient")
@patch("ga_analytics._GA_AVAILABLE", True)
class TestGetGaDashboardData:
    def test_returns_none_without_property_id(self, _mock_client_cls):
        assert ga_analytics.get_ga_dashboard_data(None) is None
        assert ga_analytics.get_ga_dashboard_data("   ") is None

    def test_returns_none_when_all_reports_fail(self, mock_client_cls):
        mock_client_cls.return_value.run_report.side_effect = RuntimeError("api down")

        assert ga_analytics.get_ga_dashboard_data("123456789") is None

    def test_maps_active_users_from_date_range_rows(self, mock_client_cls):
        client = mock_client_cls.return_value

        def run_report(request):
            metrics = [metric.name for metric in request.metrics]
            if metrics == ["activeUsers"]:
                return _response([
                    _row([_dimension_value("date_range_0")], [_metric_value("150")]),
                    _row([_dimension_value("date_range_1")], [_metric_value("42")]),
                ])
            if metrics == ["sessions", "engagedSessions", "averageSessionDuration", "bounceRate"]:
                return _response([
                    _row([], [
                        _metric_value("10"),
                        _metric_value("8"),
                        _metric_value("95.5"),
                        _metric_value("0.25"),
                    ]),
                ])
            return _response([])

        client.run_report.side_effect = run_report

        result = ga_analytics.get_ga_dashboard_data("123456789")

        assert result is not None
        assert result["active_users_7d"] == 150
        assert result["active_users_1d"] == 42
        assert result["sessions"] == 10
        assert result["bounce_rate"] == 25.0

    def test_returns_none_when_ga_library_unavailable(self, _mock_client_cls):
        with patch("ga_analytics._GA_AVAILABLE", False):
            assert ga_analytics.get_ga_dashboard_data("123456789") is None


@patch("ga_analytics.BetaAnalyticsDataClient", side_effect=RuntimeError("no creds"))
@patch("ga_analytics._GA_AVAILABLE", True)
def test_returns_none_when_client_creation_fails(_mock_client_cls):
    assert ga_analytics.get_ga_dashboard_data("123456789") is None
