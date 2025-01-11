from timescale.db.models.models import TimescaleModel
from timescale.db.models.fields import TimescaleDateTimeField
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


class Session(models.Model):
    """Represents a data collection session."""

    user_id = models.UUIDField(db_index=True, default=uuid.uuid4)
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    start_ts = models.DateTimeField(null=True, blank=True)  # Start time of the session

    def __str__(self):
        return str(self.session_id)

    class Meta:
        indexes = []


class TimeSeriesData(TimescaleModel):
    """Main time series data model"""

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="time_series_data")
    series = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    value = models.TextField()
    time = TimescaleDateTimeField(interval="1 week")  # the end time of the data point

    class Meta:
        indexes = [
            models.Index(fields=["session", "series", "time"]),
        ]

    def clean(self):
        """Validates and converts the metric value based on series type."""

        try:
            value_type = self.series.value_type
            if value_type == "float":
                float(self.value)
            elif value_type == "int":
                int(self.value)
            elif value_type == "rgb":
                if not isinstance(self.value, str) or not self.value.startswith("#") or len(self.value) != 7:
                    raise ValueError("Invalid RGB format")
            else:
                raise ValueError(f"Unmatch value type: {value_type} for series: {self.series.series}")

        except (ValueError, TypeError) as e:
            raise ValidationError({"value": str(e)})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
