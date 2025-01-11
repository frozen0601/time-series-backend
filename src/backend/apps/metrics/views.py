from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import F, Avg, Max, Min, Value, CharField, FloatField, IntegerField
from django.db.models.functions import Cast
from .models import MetricType, Session, TimeSeriesData
from .serializers import SessionSerializer
from .filters import UserFilterBackend, TimeWindowFilterBackend, SeriesFilterBackend, SessionFilterBackend
import logging

# permission not required
from rest_framework.permissions import AllowAny

logger = logging.getLogger(__name__)


class SessionViewSet(viewsets.ModelViewSet):
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        print("aa")
        serializer = self.get_serializer(data=request.data)
        print("bb")
        if serializer.is_valid():
            try:
                print("cc")
                serializer.save()
                return Response({"message": "Data ingested successfully"}, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Ingest Error: {e}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TimeSeriesDataViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    WINDOW_CHOICES = {"week": "7 days", "month": "1 month"}
    AGG_FUNCTIONS = {"avg": Avg, "max": Max, "min": Min}
    filter_backends = [UserFilterBackend, SessionFilterBackend, SeriesFilterBackend]

    def get_queryset(self):
        queryset = TimeSeriesData.timescale.all()
        queryset = self.filter_queryset(queryset)

        window = self.request.query_params.get("window", "week")
        agg_func_name = self.request.query_params.get("agg_func", "avg")

        try:
            agg_func = self.AGG_FUNCTIONS[agg_func_name.lower()]
        except KeyError:
            return TimeSeriesData.timescale.none()

        # Get distinct series types
        series_types = queryset.values_list("series__series", "series__value_type").distinct()

        # Handle each series type separately
        results = []
        for series_name, value_type in series_types:
            series_qs = queryset.filter(series__series=series_name)

            if value_type in ["float", "int"]:
                # Cast and aggregate numeric values
                cast_type = FloatField if value_type == "float" else IntegerField
                annotations = {"value": agg_func(Cast("value", output_field=cast_type())), "series": Value(series_name)}
            else:
                # For non-numeric types, just take the first value
                annotations = {"value": F("value"), "series": Value(series_name)}

            series_data = series_qs.time_bucket(
                field="time", interval=self.WINDOW_CHOICES[window], annotations=annotations
            )
            results.extend(series_data)

        return results

    def list(self, request, *args, **kwargs):
        # queryset = self.get_queryset()
        # use filter
        queryset = self.get_queryset()
        data = [{"time": item["bucket"], "value": item["value"], "series": item["series"]} for item in queryset]

        return Response(
            {
                "data": data,
                "metadata": {
                    "count": len(data),
                    "window": request.query_params.get("window", "week"),
                    "agg_func": request.query_params.get("agg_func", "avg"),
                },
            }
        )
