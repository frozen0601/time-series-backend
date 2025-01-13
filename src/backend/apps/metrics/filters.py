from rest_framework.filters import BaseFilterBackend
from django.core.exceptions import ValidationError
from django.db.models import Q
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import re


class UserFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        user_id = request.query_params.get("user_id")
        if not user_id:
            raise ValidationError("user_id is required")
        return queryset.filter(session__user_id=user_id)


class TimeWindowFilterBackend(BaseFilterBackend):
    def _parse_datetime(self, date_str):
        """Parse datetime string and ensure timezone awareness"""
        if not date_str:
            return None

        # Try parsing as ISO format first
        dt = parse_datetime(date_str)

        # If parsing failed or got naive datetime, try parsing as date
        if not dt:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return None

        # Make timezone aware if naive
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)

        return dt

    def filter_queryset(self, request, queryset, view):
        start_time = self._parse_datetime(request.query_params.get("start_time"))
        end_time = self._parse_datetime(request.query_params.get("end_time")) or timezone.now()

        if start_time:
            queryset = queryset.filter(time__range=[start_time, end_time])

        return queryset


class SeriesFilterBackend(BaseFilterBackend):
    def _get_pattern_filter(self, series_pattern):
        """Convert wildcard pattern to regex filter"""
        if "*" in series_pattern:
            pattern = re.escape(series_pattern).replace("\\*", ".*")
            return Q(series__series__regex=pattern)
        return Q(series__series=series_pattern)

    def filter_queryset(self, request, queryset, view):
        series = request.query_params.get("series")
        if not series:
            return queryset

        # Split by comma and strip whitespace
        series_patterns = [s.strip() for s in series.split(",")]

        # Combine filters with OR
        series_filter = Q()
        for pattern in series_patterns:
            series_filter |= self._get_pattern_filter(pattern)

        return queryset.filter(series_filter)


class SessionFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        session_id = request.query_params.get("session_id")
        if session_id:
            return queryset.filter(session_id=session_id)
        return queryset
