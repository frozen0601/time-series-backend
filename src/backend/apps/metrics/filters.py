from rest_framework.filters import BaseFilterBackend
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import re


class UserFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        user_id = request.query_params.get("user_id")
        if not user_id:
            raise ValidationError("user_id is required")
        return queryset.filter(session__user_id=user_id)


class TimeWindowFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        start_time = request.query_params.get("start_time")
        end_time = request.query_params.get("end_time")

        # Default to last 7 days if not specified
        if not end_time:
            end_time = datetime.now()
        if not start_time:
            start_time = end_time - timedelta(days=7)

        return queryset.filter(time__range=[start_time, end_time])


class SeriesFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        series = request.query_params.get("series")
        if series:
            if "*" in series:
                pattern = re.escape(series).replace("\\*", ".*")
                return queryset.filter(series__series__regex=pattern)
            return queryset.filter(series__series=series)
        return queryset


class SessionFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        session_id = request.query_params.get("session_id")
        if session_id:
            return queryset.filter(session_id=session_id)
        return queryset
