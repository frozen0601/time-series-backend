from celery import shared_task
from .models import SubwayLine
from celery.utils.log import get_task_logger


logger = get_task_logger(__name__)


# @shared_task
# def update_subway_statuses():
#     """Update all subway line statuses."""
#     SubwayLine.update_statuses()
#     # logger.info("update_subway_statuses task completed")


# @shared_task
# def update_line_durations():
#     """Update all subway line durations."""
#     SubwayLine.refresh_line_durations()
#     # logger.info("update_line_durations task completed")
