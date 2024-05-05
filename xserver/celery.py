import os
from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xserver.settings")

app: Celery = Celery("app")

app.config_from_object("django.conf:settings", namespace="CELERY")  # type: ignore
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)  # type: ignore