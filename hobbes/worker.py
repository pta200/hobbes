import functools
import logging
import os

from celery import Celery

logger = logging.getLogger(__name__)

# init and configure celery
celery_app = Celery(__name__)
# broker URL
celery_app.conf.broker_url = os.getenv("CELERY_BROKER_URL", "")
# result backend
celery_app.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "")
# Enables extended task result attributes (name, args, kwargs, worker, retries, queue, delivery_info) to be written to backend
celery_app.conf.result_extended = eval(os.getenv("CELERY_RESULT_EXTENDED", "True"))
# Result expiration in seconds
celery_app.conf.result_expires = int(os.getenv("CELERY_RESULT_EXPIRES", "60"))
# task will be killed after 60 seconds
celery_app.conf.task_time_limit = int(os.getenv("CELERY_TASK_TIME_LIMIT", "60"))
# task will raise exception SoftTimeLimitExceeded after 50 seconds
celery_app.conf.task_soft_time_limit = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "50"))
# message prefetch for equitable distribution
celery_app.conf.worker_prefetch_multiplier = int(os.getenv("CELERY_PREFECTCH_MULTIPLIER", "1"))
# heartbeat
celery_app.conf.worker_heartbeat = int(os.getenv("CELERY_HEARTBEAT", "120"))
# max retries
MAX_RETRIES = int(os.getenv("CELERY_MAX_RETRIES", "3"))
# count down
COUNTDOWN = int(os.getenv("CELERY_COUNTDOWN", "3"))

def payload_sanitizer(*Args, **Kwargs):
    """generate pydantic model from serialized celery dictionary payload"""

    def _wrapper(func):
        @functools.wraps(func)
        def _execute(item, *args, **kwargs):
            fargs = []
            for i, arg in enumerate(list(args)):
                fargs.append(Args[i](**args[i]))

            for k, v in kwargs.items():
                kwargs[k] = Kwargs[k](**kwargs[k])

            return func(item, *fargs, **kwargs)

        return _execute

    return _wrapper


@celery_app.task(name="inventory_books", bind=True, max_retries=MAX_RETRIES, retry_backoff=True)
@payload_sanitizer(BookInventory)
def create_show_task(self, payload: BookInventory):
    try:
        return True
    except CreateShowEventHandlerException as error:
        logger.exception(error)
        if self.request.retries >= self.max_retries:
            logger.error("failed all retries")
        raise self.retry(exc=error, countdown=COUNTDOWN)


@celery_router.get("/tasks/status/{task_id}")
async def get_status(task_id) -> TaskResponse:
    """retrieve task status from result backend using task UUID

    Args:
        task_id (str): task uuid string

    Returns:
        TaskResponse:  model containing task id, status and result strings.
        AsyncResult.state returns PENDING in case of unknown task ids.
        https://docs.celeryq.dev/en/latest/userguide/tasks.html#pending
    """
    task = AsyncResult(task_id)
    if task.result:
        result = str(task.result)
    else:
        result = None
    return TaskResponse(task_id=task.id, task_status=task.status, task_result=result)


@celery_router.put("/tasks/retry/{task_id}")
async def replay_web_task(task_id) -> TaskResponse:
    """_summary_

    Args:
        task_id (str): task uuid string

    Returns:
        TaskResponse: model containing task id, status and result strings
    """
    task = replay_task(task_id)
    if task:
        return TaskResponse(task_id=task.id, task_status=task.status, task_result=task.result)
    raise HTTPException(
        status_code=404,
        detail=f"unable to retry task id {task_id} as either the results have expired or the id is invalid",
    )
