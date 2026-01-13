import logging
from datetime import datetime
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Security, status
from hobbes.iam import TokenData, validate_token
from hobbes.crud import all_books, date_filter_books, filter_books, add_book
from hobbes.db_manager import get_async_session
from hobbes.models import BookFilter, BookPayload, TaskResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from hobbes.tasks import replay_task, archive_book, search_inventory_cll

logger = logging.getLogger(__name__)

book_router = APIRouter(
    prefix="/v1/books",
    tags=["Book Inventory"],
    responses={404: {"description": "Not found"}},
)


@book_router.post("/archive_book", status_code=201)
async def archive(payload: BookPayload) -> TaskResponse:
    """archive

    Args:
        payload (BookPayload): book json payload

    Returns:
        TaskResponse: task info
    """
    logger.debug("payload is %s", payload)

    task = archive_book.delay(payload.model_dump())
    return TaskResponse(
        task_id=task.id, task_status=task.status, task_result=task.state
    )


@book_router.post("/inventory", status_code=201)
async def inventory(payload: BookPayload) -> TaskResponse:
    """archive

    Args:
        payload (BookPayload): book json payload

    Returns:
        TaskResponse: task info
    """
    logger.debug("payload is %s", payload)

    task = search_inventory_cll.delay(payload.model_dump())
    return TaskResponse(
        task_id=task.id, task_status=task.status, task_result=task.state
    )


@book_router.post("/book", status_code=status.HTTP_201_CREATED)
async def insert_book(
    payload: BookPayload,
    session: AsyncSession = Depends(get_async_session),
    token: Annotated[TokenData, Security(validate_token, scopes=["write"])]
):
    """endpoint to insert a book. Hands it off to a background task so the API can return immediately

    Args:
        payload (BookPayload): book json payload
        background_tasks (BackgroundTasks):
        session (AsyncSession, optional): _description_. Defaults to Depends(get_async_session).

    Returns:
        json: status ok
    """
    logger.debug("payload is %s %s", payload, token.username)
    await add_book(payload, session)
    return {"status": "ok"}


@book_router.get("/all")
async def get_all_books(session: AsyncSession = Depends(get_async_session)):
    """get all Books

    Args:
        session (AsyncSession, optional): _description_. Defaults to Depends(get_async_session).

    Returns:
        List[Book]: list of Book objects
    """
    return await all_books(session)


@book_router.get("/getbydate")
async def get_books_by_date(
    date_param: datetime,
    compare: str,
    session: AsyncSession = Depends(get_async_session),
):
    """query Books by date filter.

    Args:
        date_param (datetime): format %Y-%m-%dT%H:%M:%SZ
        compare (str): gt or lt
        session (AsyncSession, optional): Dependency injection calling db_manager get_async_session

    Returns:
        List[Book]: list of Book objects
    """
    return await date_filter_books(date_param, compare, session)


@book_router.post("/search")
async def search_books(
    filter: BookFilter, session: AsyncSession = Depends(get_async_session)
):
    """search Books by dynamic filter

    Add operators to the value being filtered. Example
        {
        "column1": "!1",  # not equal to
        "column2": "1",   # equal to
        "column3": "<1",  # less than
        "column4": ">1",  # greater than
        "column5": ">=1", # greatr than or equal to
        "column6": "<=1", # less than or equal to
        "column7": "a,b", # between
        }

    datetime stamp string uses %Y-%m-%dT%H:%M:%SZ format

    Args:
        filter (BookFilter): book filter model
        session (AsyncSession, optional): Dependency injection calling db_manager get_async_session

    Returns:
        List[Book]: list of Book objects
    """
    return await filter_books(filter.model_dump(exclude_none=True), session)


@book_router.get("/tasks/status/{task_id}")
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
    return TaskResponse(
        task_id=task.id, task_status=task.status, task_result=result.info
    )


@book_router.put("/tasks/retry/{task_id}")
async def replay_web_task(task_id) -> TaskResponse:
    """_summary_

    Args:
        task_id (str): task uuid string

    Returns:
        TaskResponse: model containing task id, status and result strings
    """
    task = replay_task(task_id)
    if task:
        return TaskResponse(
            task_id=task.id, task_status=task.status, task_result=task.result
        )
    raise HTTPException(
        status_code=404,
        detail=f"unable to retry task id {task_id} as either the results have expired or the id is invalid",
    )
