import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from hobbes.crud import all_stats, date_filter_stats, filter_stats, insert_stat
from hobbes.db_manager import get_session
from hobbes.models import BookFilter, BookPayload
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)

stat_router = APIRouter(
    prefix="/v1/books",
    tags=["Book Inventory"],
    responses={404: {"description": "Not found"}},
)


@stat_router.post("/book", status_code=201)
async def insert_book(
    payload: BookPayload, session: AsyncSession = Depends(get_session)
):
    """endpoint to insert a book. Hands it off to a background task so the API can return immediately

    Args:
        payload (BookPayload): book json payload
        background_tasks (BackgroundTasks):
        session (AsyncSession, optional): _description_. Defaults to Depends(get_session).

    Returns:
        json: status ok
    """
    logger.debug("payload is %s", payload)
    await insert_stat(payload, session)
    return {"status": "ok"}


@stat_router.get("/all")
async def get_all_books(session: AsyncSession = Depends(get_session)):
    """get all Books

    Args:
        session (AsyncSession, optional): _description_. Defaults to Depends(get_session).

    Returns:
        List[Book]: list of Book objects
    """
    return await all_stats(session)


@stat_router.get("/getbydate")
async def get_books_by_date(
    date_param: datetime, compare: str, session: AsyncSession = Depends(get_session)
):
    """query Books by date filter.

    Args:
        date_param (datetime): format %Y-%m-%dT%H:%M:%SZ
        compare (str): gt or lt
        session (AsyncSession, optional): Dependency injection calling db_manager get_session

    Returns:
        List[Book]: list of Book objects
    """
    return await date_filter_stats(date_param, compare, session)


@stat_router.post("/search")
async def search_books(
    filter: BookFilter, session: AsyncSession = Depends(get_session)
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
        session (AsyncSession, optional): Dependency injection calling db_manager get_session

    Returns:
        List[Book]: list of Book objects
    """
    return await filter_stats(filter.model_dump(exclude_none=True), session)
