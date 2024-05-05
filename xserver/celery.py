import os
from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xserver.settings")
os.environ['OMP_NUM_THREADS'] = '2'  # Limit the number of threads to 2

app: Celery = Celery("app")

app.config_from_object("django.conf:settings", namespace="CELERY")  # type: ignore
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)  # type: ignore