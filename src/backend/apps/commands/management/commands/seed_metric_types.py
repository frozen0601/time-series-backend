from django.core.management.base import BaseCommand
from metrics.models import MetricType
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed database with metrics"

    def handle(self, *args, **options):
        metrics = [
            {
                "series": "session.gut_health_score",
                "schema": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                    },
                    "required": ["value"],
                },
                "description": "float series representing a gut health score in the interval [0, 100]",
            },
            {
                "series": "session.urine.color",
                "schema": {
                    "type": "object",
                    "properties": {
                        "r": {"type": "number"},
                        "g": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["r", "g", "b"],
                },
                "description": "rgb series representing urine color over time for each session",
            },
            {
                "series": "session.urine.night_count",
                "schema": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "number"},
                    },
                    "required": ["value"],
                },
                "description": "int series of the number of nighttime urinations",
            },
        ]
        created_count = 0
        for metric in metrics:
            _, created = MetricType.objects.get_or_create(**metric)
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} metrics"))
