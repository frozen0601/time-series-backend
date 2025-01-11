from timescale.db.models.models import TimescaleModel
from timescale.db.models.fields import TimescaleDateTimeField
from django.db import models
from django.core.exceptions import ValidationError
import uuid
import jsonschema
import logging

logger = logging.getLogger(__name__)


class MetricType(models.Model):
    """Defines metadata about metric series"""

    series = models.CharField(max_length=255, unique=True)
    schema = models.JSONField(help_text="JSON Schema defining the structure and validation rules for the metric")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        """Validate the schema itself"""
        try:
            # Validate schema is valid JSON Schema
            jsonschema.Draft7Validator.check_schema(self.schema)
        except jsonschema.exceptions.SchemaError as e:
            raise ValidationError({"schema": f"Invalid JSON Schema: {str(e)}"})

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
        return str(f"{self.session_id} - {self.start_ts}")

    class Meta:
        ordering = ["-start_ts"]


class TimeSeriesData(TimescaleModel):
    """Main time series data model"""

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="time_series_data")
    series = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    value = models.JSONField()
    time = TimescaleDateTimeField(interval="1 week")  # the end time of the data point

    def __str__(self):
        return f"{self.session_id} - {self.series} - {self.value}"

    class Meta:
        indexes = [
            models.Index(fields=["session", "series", "time"]),
        ]

    def clean(self):
        """Validates the value against the series schema"""
        try:
            jsonschema.validate(instance=self.value, schema=self.series.schema)
        except jsonschema.exceptions.ValidationError as e:
            raise ValidationError({"value": f"Value does not match schema: {str(e)}"})
        except Exception as e:
            raise ValidationError({"value": str(e)})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
