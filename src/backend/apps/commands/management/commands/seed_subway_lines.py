from django.core.management.base import BaseCommand
from subway.models import SubwayLine
from subway.mta_data_fetcher import mta_client
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seed database with subway lines"

    def handle(self, *args, **options):
        subway_lines = mta_client.get_subway_line_names()
        created_count = 0
        for line in subway_lines:
            _, created = SubwayLine.objects.get_or_create(name=line)
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} subway lines"))
