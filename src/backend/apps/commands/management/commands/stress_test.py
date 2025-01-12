import random
import uuid
import time
from datetime import timedelta
from faker import Faker
from django.utils import timezone
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from metrics.models import MetricType, Session, TimeSeriesData
from django.db.models import Avg, FloatField
from django.db.models.functions import Cast
from django.test import Client
from urllib.parse import urlencode

fake = Faker()


class Command(BaseCommand):
    help = "Generate large dataset, test query performance, then revert DB."

    def __init__(self):
        super().__init__()
        self.client = Client()

    def add_arguments(self, parser):
        parser.add_argument("--sessions", type=int, default=25000)
        parser.add_argument("--points", type=int, default=10)

    def handle(self, *args, **options):
        self._store_original_state()

        # try:
        #     with transaction.atomic():
        #         self._generate_data(options["sessions"], options["points"])
        #         self._test_query_performance()
        #         self._test_api_performance()
        #         self._cleanup()
        #         # Rolling back everything so DB reverts to original state
        #         raise Exception("Rollback after performance test")
        # except Exception as e:
        #     if str(e) == "Rollback after performance test":
        #         self.stdout.write(self.style.SUCCESS("Test data rolled back successfully."))
        #     else:
        #         self.stderr.write(f"Error: {e}")

        # self._generate_data(options["sessions"], options["points"])
        self._test_query_performance()
        self._test_api_performance()
        self.stdout.write(self.style.SUCCESS("Test complete."))

    def _store_original_state(self):
        """Store IDs of existing data."""
        self.original_sessions = set(Session.objects.values_list("session_id", flat=True))
        self.original_timeseries = set(TimeSeriesData.objects.values_list("id", flat=True))

    def _generate_data(self, num_sessions, points_per_session):
        """Generate large dataset with increasing timestamps within a reasonable range."""
        BATCH_SIZE = 10000
        TRANSACTION_SIZE = 50000
        total_points = num_sessions * points_per_session

        self.stdout.write(f"Generating {num_sessions} sessions, each with {points_per_session} points.")
        metric_types = list(MetricType.objects.all())
        if not metric_types:
            raise Exception("No MetricTypes found. Please create some before testing.")

        base_time = timezone.now() - timedelta(weeks=96)
        session_time = base_time
        points_created = 0

        # Process in transaction-sized chunks
        for chunk_start in range(0, num_sessions, TRANSACTION_SIZE):
            chunk_end = min(chunk_start + TRANSACTION_SIZE, num_sessions)

            with transaction.atomic():
                data_points = []

                for _ in range(chunk_start, chunk_end):
                    session_time_limit = timezone.now() - timedelta(days=365 * 2)
                    session_time = max(session_time, session_time_limit)
                    session_time = session_time + timedelta(hours=random.randint(1, 12))

                    session = Session.objects.create(
                        user_id="d38834e0-fe46-4bf9-831d-1d5b125bdc9b", start_ts=session_time
                    )

                    for _ in range(points_per_session):
                        metric_type = random.choice(metric_types)
                        timestamp = session_time + timedelta(minutes=random.randint(1, 60))
                        value = self._generate_random_value(metric_type.series)
                        data_points.append(
                            TimeSeriesData(session=session, series=metric_type, value=value, time=timestamp)
                        )

                        # Bulk create when batch size reached
                        if len(data_points) >= BATCH_SIZE:
                            TimeSeriesData.objects.bulk_create(data_points)
                            points_created += len(data_points)
                            self.stdout.write(
                                f"Progress: {points_created}/{total_points} points "
                                f"({(points_created / total_points * 100):.1f}%)"
                            )
                            data_points = []

                # Create remaining points in this transaction
                if data_points:
                    TimeSeriesData.objects.bulk_create(data_points)
                    points_created += len(data_points)
                    self.stdout.write(
                        f"Progress: {points_created}/{total_points} points "
                        f"({(points_created / total_points * 100):.1f}%)"
                    )

            # Force garbage collection between transactions
            import gc

            gc.collect()

        self.stdout.write(self.style.SUCCESS(f"Created {points_created} total data points"))

    def _test_api_performance(self):
        """Test actual API endpoint performance"""
        self.stdout.write("Testing API endpoint performance...")

        # Test Case 1: Month-level aggregation
        params = {
            "user_id": "d38834e0-fe46-4bf9-831d-1d5b125bdc9b",
            "interval": "month",
            "series": "session.urine.*",
            "agg_func": "avg",
            "start_time": "2020-02-01",
        }
        start = time.time()
        response = self.client.get(f"/api/timeseries?{urlencode(params)}")
        elapsed = time.time() - start

        self.stdout.write(self.style.WARNING(f"Time: {elapsed:.3f}s"))

    def _test_query_performance(self):
        """Run a few queries that mimic what TimeSeriesDataViewSet does."""
        self.stdout.write("Testing query performance...")

        # 1) Example: day-level average across the entire dataset for 'score' series
        start_q1 = time.time()
        q1_results = (
            TimeSeriesData.timescale.all()
            .time_bucket(field="time", interval="1 day")
            .annotate(avg_value=Avg(Cast("value__value", output_field=FloatField())))
        )
        q1_list = list(q1_results)
        q1_elapsed = time.time() - start_q1
        self.stdout.write(
            self.style.WARNING(f"[Query 1] Found {len(q1_list)} buckets in {q1_elapsed:.3f}s (day-level, avg).")
        )

        # 2) Example: week-level average across the entire dataset for 'score' series
        start_q2 = time.time()
        q2_results = (
            TimeSeriesData.timescale.all()
            .time_bucket(field="time", interval="1 week")
            .annotate(avg_value=Avg(Cast("value__value", output_field=FloatField())))
        )
        q2_list = list(q2_results)
        q2_elapsed = time.time() - start_q2
        self.stdout.write(
            self.style.WARNING(f"[Query 2] Found {len(q2_list)} buckets in {q2_elapsed:.3f}s (week-level, avg).")
        )

        # 3) Example: month-level average across the entire dataset for 'score' series
        start_q3 = time.time()
        q3_results = (
            TimeSeriesData.timescale.all()
            .time_bucket(field="time", interval="1 month")
            .annotate(avg_value=Avg(Cast("value__value", output_field=FloatField())))
        )
        q3_list = list(q3_results)
        q3_elapsed = time.time() - start_q3
        self.stdout.write(
            self.style.WARNING(f"[Query 3] Found {len(q3_list)} buckets in {q3_elapsed:.3f}s (month-level, avg).")
        )

        # 4) month-level average for any 'session.urine.*' series after 2020-02-01
        start_date = timezone.make_aware(datetime(2020, 2, 1))
        start_q4 = time.time()
        q4_results = (
            TimeSeriesData.timescale.filter(series__series__regex=r"session\.urine\..*", time__gte=start_date)
            .time_bucket(field="time", interval="1 month")
            .annotate(avg_value=Avg(Cast("value__value", output_field=FloatField())))
        )
        q4_list = list(q4_results)
        q4_elapsed = time.time() - start_q4
        self.stdout.write(
            self.style.WARNING(
                f"[Query 4] Found {len(q4_list)} buckets in {q4_elapsed:.3f}s (month-level, avg, 'session.urine.*')."
            )
        )

    def _generate_random_value(self, series_name):
        """Generate a random value based on series type."""
        if "color" in series_name:
            return {"r": random.randint(0, 255), "g": random.randint(0, 255), "b": random.randint(0, 255)}
        elif "score" in series_name:
            return random.uniform(0, 100)
        elif "count" in series_name:
            return random.randint(0, 10)
        else:
            return fake.text()

    def _cleanup(self):
        """Remove any newly created data."""
        self.stdout.write("Cleaning new data within transaction...")

        new_timeseries = TimeSeriesData.objects.exclude(id__in=self.original_timeseries)
        new_sessions = Session.objects.exclude(session_id__in=self.original_sessions)

        new_timeseries.delete()
        new_sessions.delete()

        self.stdout.write(self.style.SUCCESS("Cleanup complete."))
