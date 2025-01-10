import os
from celery import Celery
from django.conf import settings

# Celery Configuration
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.base")

app = Celery("subway")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


__all__ = ["app"]


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))
