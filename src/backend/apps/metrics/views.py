from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import F, Count, Avg, Max, Min, Value, Window, FloatField, IntegerField
from django.db.models.functions import Cast, FirstValue
from rest_framework.permissions import AllowAny

from .models import MetricType, Session, TimeSeriesData
from .serializers import MetricTypeSerializer, SessionSerializer
from .filters import UserFilterBackend, TimeWindowFilterBackend, SeriesFilterBackend, SessionFilterBackend

# from .utils import PercentileCont

import logging


logger = logging.getLogger(__name__)


class MetricTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MetricType.objects.all()
    serializer_class = MetricTypeSerializer
    permission_classes = [AllowAny]


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({"message": "Data ingested successfully"}, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Ingest Error: {e}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)


class TimeSeriesDataViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    INTERVAL_CHOICES = {"min": "1 min", "week": "1 week", "month": "1 month"}
    AGG_FUNCTIONS = {
        "avg": Avg,
        "max": Max,
        "min": Min,
        "count": Count,
        # "median": lambda field: PercentileCont(field, percentile=0.5),
        # "p90": lambda field: PercentileCont(field, percentile=0.9),
        # "p99": lambda field: PercentileCont(field, percentile=0.99),
    }
    filter_backends = [UserFilterBackend, SessionFilterBackend, SeriesFilterBackend, TimeWindowFilterBackend]

    def get_queryset(self):
        return TimeSeriesData.timescale.all()

    def _aggregate_timeseries(self, queryset):
        interval = self.request.query_params.get("interval", "week")
        agg_func_name = self.request.query_params.get("agg_func", "avg")

        try:
            agg_func = self.AGG_FUNCTIONS[agg_func_name.lower()]
        except KeyError:
            return TimeSeriesData.timescale.none()

        series_types = queryset.values_list("series__series", "series__schema").distinct()
        results = []

        for series_name, schema in series_types:
            series_qs = queryset.filter(series__series=series_name)
            time_bucket_query = self._get_time_bucket_query(series_qs, interval)

            if self._is_numeric_schema(schema):
                annotations = self._get_numeric_annotations(series_name, agg_func)
                series_data = time_bucket_query.annotate(**annotations)
            elif self._is_rgb_schema(schema):
                annotations = self._get_rgb_annotations(series_name, agg_func)
                series_data = time_bucket_query.annotate(**annotations)
            else:
                time_bucket_query = time_bucket_query.values("bucket")
                annotations = self._get_default_annotations(series_name)
                series_data = time_bucket_query.annotate(**annotations)
                series_data = series_data.distinct(
                    "bucket"
                )  # NOTE: The entries aren't bucketed as expected. Further investigation needed.

            results.extend(series_data)

        return results

    def _is_rgb_schema(self, schema):
        """Check if schema is for RGB color"""
        properties = schema.get("properties", {})
        return all(key in properties for key in ["r", "g", "b"])

    def _is_numeric_schema(self, schema):
        """Check if schema is for numeric value"""
        properties = schema.get("properties", {})
        return "value" in properties and properties["value"].get("type") == "number"

    def _get_time_bucket_query(self, series_qs, interval):
        """Create base time bucket query"""
        return series_qs.time_bucket(field="time", interval=self.INTERVAL_CHOICES[interval])

    def _get_numeric_annotations(self, series_name, agg_func):
        """Get annotations for numeric type"""
        return {
            "series": Value(series_name),
            "value": agg_func(Cast("value__value", output_field=FloatField())),
        }

    def _get_rgb_annotations(self, series_name, agg_func):
        """Get annotations for RGB type"""
        return {
            "series": Value(series_name),
            "r": agg_func(Cast("value__r", output_field=IntegerField())),
            "g": agg_func(Cast("value__g", output_field=IntegerField())),
            "b": agg_func(Cast("value__b", output_field=IntegerField())),
        }

    def _get_default_annotations(self, series_name):
        """Get annotations for string type"""
        return {
            "series": Value(series_name),
            "value": Window(expression=FirstValue("value__value"), partition_by=["bucket"], order_by=F("time").asc()),
        }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        aggregated_data = self._aggregate_timeseries(queryset)

        response = {
            "metadata": {
                "count": len(aggregated_data),
                "interval": request.query_params.get("interval", "week"),
                "agg_func": request.query_params.get("agg_func", "avg"),
            },
            "results": aggregated_data,
        }

        return Response(response)
