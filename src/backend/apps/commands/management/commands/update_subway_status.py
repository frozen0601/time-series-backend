from django.core.management.base import BaseCommand
from django.utils import timezone
from subway.models import SubwayLine
from exceptions import StatusUpdateError
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Updates subway line statuses from MTA API"

    def handle(self, *args, **options):
        try:
            SubwayLine.update_statuses()
            logger.info(f"Status update completed at {timezone.now()}")
        except StatusUpdateError as e:
            logger.error(f"Failed to update statuses: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during status update: {e}")
