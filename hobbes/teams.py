import logging
from datetime import datetime
from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from hobbes.crud import insert_hero, insert_team, search_recent_team_member
from hobbes.db_manager import get_async_session
from hobbes.models import TeamPayload, HeroPayload
from sqlmodel.ext.asyncio.session import AsyncSession


logger = logging.getLogger(__name__)

teams_router = APIRouter(
    prefix="/v1/teams",
    tags=["Teams Inventory"],
    responses={404: {"description": "Not found"}},
)


@teams_router.post("/team", status_code=201)
async def add_team(
    payload: TeamPayload, session: AsyncSession = Depends(get_async_session)
):
    """add team

    Args:
        payload (TeamPayload): book json payload

    Returns:
        resp
    """
    logger.debug("payload is %s", payload)

    return await insert_team(payload, session)


@teams_router.post("/hero/{team}", status_code=201)
async def add_team(
    payload: HeroPayload, team: str, session: AsyncSession = Depends(get_async_session)
):
    """add hero

    Args:
        payload (HeroPayload): book json payload

    Returns:
        resp
    """
    logger.debug("payload is %s", payload)

    return await insert_hero(payload, team, session)


@teams_router.post("/recent_heroes", status_code=201)
async def add_team(session: AsyncSession = Depends(get_async_session)):
    """add hero

    Args:
        payload (HeroPayload): book json payload

    Returns:
        resp
    """

    return await search_recent_team_member(session)
