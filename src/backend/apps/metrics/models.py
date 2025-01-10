from timescale.db.models.models import TimescaleModel
from django.db import models
import uuid
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class MetricType(models.Model):
    """Defines metadata about metric series"""

    series = models.CharField(max_length=255, unique=True)
    VALUE_TYPES = (("float", "Float"), ("int", "Integer"), ("rgb", "RGB Color"))
    value_type = models.CharField(max_length=10, choices=VALUE_TYPES)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.series

    class Meta:
        indexes = [
            models.Index(fields=["series"]),
        ]


class TimeSeriesData(TimescaleModel):
    """Main time series data model"""

    user_id = models.UUIDField(db_index=True, default=uuid.uuid4)
    session_id = models.UUIDField(null=True, db_index=True)
    series = models.ForeignKey(MetricType, on_delete=models.CASCADE, related_name="time_series_data")
    ts = models.DateTimeField(db_index=True)
    value = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["user", "series", "ts"]),
            models.Index(fields=["session_id", "series", "ts"]),
            models.Index(fields=["series", "ts"]),
        ]

    def clean(self):
        """Validates and converts the metric value based on series type."""

        try:
            metric_value = self.value.get("value")
            if not metric_value:
                raise ValueError("Value field is missing")

            value_type = self.series.value_type

            if value_type == "float":
                converted_value = float(metric_value)
            elif value_type == "int":
                converted_value = int(metric_value)
            elif value_type == "rgb":
                if not isinstance(metric_value, str) or not metric_value.startswith("#") or len(metric_value) != 7:
                    raise ValueError("Invalid RGB format")
                converted_value = metric_value
            else:
                raise ValueError(f"Unknown value type: {value_type}")

            self.value = {"type": value_type, "value": converted_value}

        except (ValueError, TypeError) as e:
            raise ValidationError({"value": str(e)})

    def save(self, *args, **kwargs):
        self.full_clean()  # Ensure validation before saving
        super().save(*args, **kwargs)
