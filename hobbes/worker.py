import functools
import logging
import os

from celery import Celery

logger = logging.getLogger(__name__)

# init and configure celery
celery_app = Celery(__name__)

# find tasks
celery_app.autodiscover_tasks(['hobbes'])

