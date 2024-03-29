from __future__ import absolute_import, unicode_literals

import os

from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'swstatisticsweb.settings')

app = Celery('swstatisticsweb', backend='redis://localhost',
             broker='redis://localhost')
# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.update(
    result_expires=1200,  # 1200 secs = 20 minutes
)

app.conf.broker_transport_options = {"visibility_timeout": 1200}  # 20min

app.conf.timezone = 'UTC'  # UTC server time

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
