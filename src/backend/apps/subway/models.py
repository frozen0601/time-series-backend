from django.db import models, transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from typing import Tuple, Dict
import datetime
import logging

logger = logging.getLogger(__name__)
status_logger = logging.getLogger("subway.status_changes")


class SubwayStatus(models.TextChoices):
    NORMAL = "normal", _("Normal")
    DELAYED = "delayed", _("Delayed")


class StatusHistory(models.Model):
    line = models.ForeignKey("SubwayLine", on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=SubwayStatus.choices)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["line_id"]),
            models.Index(fields=["line", "status"]),
        ]

    @classmethod
    @transaction.atomic
    def compress_history(cls, line):
        """
        Compress status history records for a line by merging records with the same status.
        """
        status_duration_map = (
            cls.objects.filter(line=line)
            .values("status")
            .annotate(total_duration=models.Sum(models.F("end_time") - models.F("start_time")))
            .order_by("status")
        )

        new_records = []
        current_time = line.created_at

        for entry in status_duration_map:
            status = entry["status"]
            duration = entry["total_duration"]

            if duration and duration.total_seconds() > 0:
                new_record = cls(line=line, status=status, start_time=current_time, end_time=current_time + duration)
                new_records.append(new_record)
                current_time += duration

        if new_records:
            try:
                cls.objects.bulk_create(new_records)
                cls.objects.filter(line=line).delete()
                logger.info(f"Compressed status history for line {line.name}")
            except Exception as e:
                logger.error(f"Failed to compress status history for line {line.name}: {e}")

        else:
            logger.info(f"No status history to compress for line {line.name}")


class SubwayLine(models.Model):
    name = models.CharField(max_length=10, unique=True)
    status = models.CharField(
        max_length=10, choices=SubwayStatus.choices, default=SubwayStatus.NORMAL
    )  # Current status of the line
    status_since = models.DateTimeField(auto_now_add=True)  # Time when the current status started
    total_delay_duration = models.DurationField(default=datetime.timedelta(0))  # Total time spent in delayed status
    total_normal_duration = models.DurationField(default=datetime.timedelta(0))  # Total time spent in normal status
    last_update = models.DateTimeField(auto_now=True)  # Last time the status was updated
    created_at = models.DateTimeField(auto_now_add=True)  # Time when the line was created

    def __str__(self):
        return f"Line {self.name}"

    def to_dict(self):
        return {"line": self.name, "status": self.status}

    @property
    def uptime_ratio(self):
        """Calculate uptime ratio (0.0-1.0) dynamically. return -1 if there is no data."""
        total_tracked_duration = self.total_normal_duration + self.total_delay_duration
        if total_tracked_duration.total_seconds() == 0:
            # check if there is no related StatusHistory records. If so, return -1
            if StatusHistory.objects.filter(line=self).count() == 0:
                return -1.0
            return 1.0
        return self.total_normal_duration / total_tracked_duration

    @classmethod
    def update_statuses(cls) -> None:
        """Update statuses for all subway lines."""
        from .mta_data_fetcher import mta_client

        latest_statuses = mta_client.get_latest_line_status()
        now = timezone.now()

        with transaction.atomic():
            lines = cls.objects.all()
            for line in lines:
                cls._update_line_status(line=line, new_status=latest_statuses[line.name], now=now)
                line.save()

    @classmethod
    def _update_line_status(cls, line: "SubwayLine", new_status: str, now: datetime) -> None:
        """Update status for a single subway line."""

        # create a history record
        if cls._has_service_gap(line, now):
            cls._create_history_record(line, line.status_since, line.last_update)
        elif line.status != new_status:
            cls._create_history_record(line, line.status_since, now)
            line.status = new_status

        line.last_update = now

    @classmethod
    def _has_service_gap(cls, line: "SubwayLine", current_time: datetime) -> bool:
        """
        Check if there's a significant gap in service updates.
        This is used to detect downtime in our system/3rd party API.
        """
        MAX_ACCEPTABLE_GAP = datetime.timedelta(minutes=15)
        return current_time - line.last_update > MAX_ACCEPTABLE_GAP

    @classmethod
    def _create_history_record(cls, line: "SubwayLine", start_time: datetime, end_time: datetime) -> None:
        """Create a new StatusHistory record."""
        StatusHistory.objects.create(line=line, status=line.status, start_time=start_time, end_time=end_time)
        line.status_since = end_time

    # ------- Line duration calculation methods ------ #

    @classmethod
    def refresh_line_durations(cls):
        """Update total delay and normal durations for all subway lines."""
        current_time = timezone.now()
        lines = cls.objects.all()
        total_durations = cls._calculate_total_durations(lines)

        # Prepare updated lines
        updated_lines = []
        for line in lines:
            cls._prepare_duration_updates(line, total_durations, current_time)
            updated_lines.append(line)

        # Perform bulk update
        cls.objects.bulk_update(updated_lines, ["total_delay_duration", "total_normal_duration"])

    @classmethod
    def _calculate_total_durations(
        cls, lines
    ) -> Dict[Tuple[str, str], datetime.timedelta]:  # {(line name, line status): total_duration}
        """Get the total durations for each line and status combination."""
        lines_info = (
            StatusHistory.objects.filter(line__in=lines)
            .values("line", "status")
            .annotate(total_duration=models.Sum(models.F("end_time") - models.F("start_time")))
        )

        total_durations = {}
        for line_info in lines_info:
            total_durations[(line_info["line"], line_info["status"])] = line_info["total_duration"]

        return total_durations

    @classmethod
    def _prepare_duration_updates(cls, line: "SubwayLine", total_durations: dict, now: datetime) -> None:
        """Prepare total durations for a single subway line."""
        line.total_delay_duration = total_durations.get((line.id, SubwayStatus.DELAYED), datetime.timedelta(0))
        line.total_normal_duration = total_durations.get((line.id, SubwayStatus.NORMAL), datetime.timedelta(0))
        if line.status == SubwayStatus.DELAYED and line.status_since:
            line.total_delay_duration += now - line.status_since
        elif line.status == SubwayStatus.NORMAL and line.status_since:
            line.total_normal_duration += now - line.status_since


@receiver(pre_save, sender=SubwayLine)
def handle_subway_line_status_change(sender, instance, **kwargs):
    """Handle subway line status changes via signal."""
    if not instance.pk:  # New instance
        return
    try:
        old_instance = SubwayLine.objects.get(pk=instance.pk)
        if old_instance.status != instance.status:
            if instance.status == SubwayStatus.DELAYED:
                status_logger.info(f"Line {instance.name} is experiencing delays")
            elif instance.status == SubwayStatus.NORMAL:
                status_logger.info(f"Line {instance.name} is now recovered")
    except SubwayLine.DoesNotExist:
        pass
