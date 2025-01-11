from rest_framework import serializers
from .models import Session, TimeSeriesData, MetricType
from django.utils import timezone
import jsonschema


class MetricTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricType
        fields = ["series", "schema", "description"]


class TimeSeriesDataSerializer(serializers.ModelSerializer):
    series = serializers.CharField()
    value = serializers.JSONField()

    class Meta:
        model = TimeSeriesData
        fields = ["series", "time", "value"]

    def validate_series(self, value):
        try:
            MetricType.objects.get(series=value)
            return value
        except MetricType.DoesNotExist:
            raise serializers.ValidationError("Invalid series name.")

    def validate(self, data):
        series_name = data.get("series")
        value = data.get("value")
        if series_name and value:
            try:
                metric_type = MetricType.objects.get(series=series_name)
                if metric_type.schema:
                    jsonschema.validate(value, metric_type.schema)
            except MetricType.DoesNotExist:
                pass
            except jsonschema.exceptions.ValidationError as e:
                raise serializers.ValidationError({"value": f"Value does not match schema: {str(e)}"})
        return data

    def create(self, validated_data):
        series_name = validated_data.pop("series")
        metric_type = MetricType.objects.get(series=series_name)
        return TimeSeriesData.objects.create(series=metric_type, **validated_data)


class SessionSerializer(serializers.ModelSerializer):
    data = TimeSeriesDataSerializer(many=True)

    class Meta:
        model = Session
        fields = ["user_id", "session_id", "start_ts", "data"]

    def create(self, validated_data):
        data_points = validated_data.pop("data")
        session = Session.objects.create(**validated_data)

        for point in data_points:
            series = point.pop("series")
            metric_type = MetricType.objects.get(series=series)
            TimeSeriesData.objects.create(session=session, series=metric_type, **point)
        return session
