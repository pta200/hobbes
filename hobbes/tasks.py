import os
import logging
import celery
from celery import shared_task
from hobbes.models import BookPayload

logger = logging.getLogger(__name__)

# retry task
MAX_RETRIES = int(os.getenv("CELERY_MAX_RETRIES", "3"))
# count down retries
COUNTDOWN = int(os.getenv("CELERY_COUNTDOWN", "3"))


@shared_task
def add(x, y):
    """Adds two numbers and returns the sum."""
    return x + y

@shared_task
def send_email(recipient, subject, body):
    """Simulates sending an email."""
    logger.info(f"Sending email to {recipient} with subject '{subject}'")
    # In a real application, this would involve email sending logic
    return True


@shared_task(name="inventory_books", bind=True, max_retries=MAX_RETRIES, retry_backoff=True, pydantic=True)
def inventory_books(self, payload: BookPayload):
    try:
        logger.info(payload)
        return True
    except Exception as error:
        logger.exception(error)
        if self.request.retries >= self.max_retries:
            logger.error("failed all retries")
        raise self.retry(exc=error, countdown=COUNTDOWN)

def replay_task(task_id):    
    meta = celery.backend.get_task_meta(task_id)
    task = celery.tasks[meta['name']]
    task.apply_async(args=meta['args'], kwargs=meta['kwargs'])