from django.apps import AppConfig
import threading
import time
import logging

logger = logging.getLogger(__name__)


class MetricsConfig(AppConfig):
    name = "metrics"
