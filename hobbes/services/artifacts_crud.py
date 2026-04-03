import logging
import uuid
from typing import Type

from sqlmodel import SQLModel, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from hobbes.routers.auth import TokenData
from hobbes.models.artifact_models import (
    Dependencies,
    DependencyCreatePayload,
    DependencyEditPayload,
    ArtifactPaginationResponse,
    Repositories,
    RepositoryCreatePayload,
    RepositoryEditPayload,
)

logger = logging.getLogger(__name__)


class RepositoryNotFoundException(Exception):
    """crud exception when repository not found"""


class DependencyNotFoundException(Exception):
    """crud exception when dependency not found"""


class IdNotFoundException(Exception):
    """Id not found"""


async def add_repository(
    session: AsyncSession, payload: RepositoryCreatePayload, token: TokenData
) -> Repositories:
    """
    Insert new repository

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (RepositoryPayload): new profile
        token (TokenData): oauth token data

    Returns:
        Repositories: returns repository object
    """
    # create new repository
    rep = Repositories(
        rep_name=payload.rep_name, rep_type=payload.rep_type, url=payload.url
    )
    session.add(rep)
    await session.commit()

    return rep


async def edit_repository(
    session: AsyncSession,
    rep_id: uuid.UUID,
    payload: RepositoryEditPayload,
    token: TokenData,
) -> Repositories:
    """
    Edit existing repository

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (RepositoryPayload): new profile
        token (TokenData): oauth token data

    Returns:
        Repositories: edited repository
    """
    result = await session.exec(
        select(Repositories).where(Repositories.rep_id == rep_id)
    )
    rep = result.one_or_none()
    if rep:
        if rep.rep_name != payload.rep_name:
            rep.rep_name = payload.rep_name

        if rep.rep_type != payload.rep_type:
            rep.rep_type = payload.rep_type

        if rep.url != payload.url:
            rep.url = payload.url

        session.add(rep)
        await session.commit()
        await session.refresh(rep)

        return rep

    else:
        raise RepositoryNotFoundException(f"repository {payload.rep_name} not found")


async def add_dependency(
    session: AsyncSession, payload: DependencyCreatePayload, token: TokenData
) -> Dependencies:
    """
    Add new dependency object

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (DependencyPayload): dependency API payload
        token (TokenData): oauth token data

    Returns:
        Dependencies: dependency object
    """
    dep = Dependencies(
        dep_name=payload.dep_name,
        version=payload.version,
        relative_url=payload.relative_url,
        detail=payload.detail,
        rep_id=payload.rep_id,
    )
    session.add(dep)
    await session.commit()
    return dep


async def edit_dependency(
    session: AsyncSession,
    dep_id: uuid.UUID,
    payload: DependencyEditPayload,
    token: TokenData,
) -> Dependencies:
    """
    Edit existing dependency

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (DependencyEditPayload): dependency edit API payload
        token (TokenData): oauth token data

    Returns:
        Dependencies: dependency object
    """
    result = await session.exec(
        select(Dependencies).where(Dependencies.dep_id == dep_id)
    )
    dep = result.one_or_none()
    if dep:
        if dep.dep_name != payload.dep_name:
            dep.dep_name = payload.dep_name

        if dep.version != payload.version:
            dep.version = payload.version

        if dep.relative_url != payload.relative_url:
            dep.relative_url = payload.relative_url

        if dep.detail != payload.detail:
            dep.detail = payload.detail

        if dep.rep_id != payload.rep_id:
            dep.rep_id = payload.rep_id

        session.add(dep)
        await session.commit()
        await session.refresh(dep)

        return dep
    raise DependencyNotFoundException(f"dependency {payload.dep_name} not found")


async def fetch_items(
    session: AsyncSession, model: Type[SQLModel], offset: int, limit: int
) -> ArtifactPaginationResponse:
    """
    Fetch list of items based on model parameter.

    Args:
        session (AsyncSession): SQLModel scoped async session object
        offset (int): table offset
        limit (int): row limit

    Returns:
        ArtifactPaginationResponse: paginated model list of rows
    """
    total_query = await session.exec(select(func.count()).select_from(model))
    total = total_query.one()

    if model == Repositories:
        result = await session.exec(
            select(Repositories)
            .order_by(Repositories.rep_name)
            .offset(offset)
            .limit(limit)
        )
    else:
        result = await session.exec(
            select(Dependencies)
            .order_by(Dependencies.dep_name)
            .offset(offset)
            .limit(limit)
        )

    return ArtifactPaginationResponse(total=total, rows=list(result.all()))


async def fetch_by_id(session: AsyncSession, model: Type[SQLModel], obj_id: uuid.UUID):
    """
    Generic get by

    Args:
        session (AsyncSession): SQLModel scoped async session object
        model (Type[SQLMode]): SQLModel ORM objects
        obj_id (UUID): UUID for model being queried

    Raises:
        ProfileNotFoundException: model instance not found

    Returns:
        SQLModel: returns request SQLModel ORM object
    """
    result = await session.get(model, obj_id)
    if result:
        return result
    raise IdNotFoundException(f"{model} id {obj_id} not found")


async def delete_by_id(
    session: AsyncSession, model: Type[SQLModel], obj_id: uuid.UUID
) -> bool:
    """
    Delete dependency

    Args:
        session (AsyncSession): SQLModel scoped async session object
        obj_id (uuid.UUID): model id

    Returns:
        bool: delete success
    """
    if model == Repositories:
        result = await session.exec(select(model).where(Repositories.rep_id == obj_id))
    else:
        result = await session.exec(select(model).where(Dependencies.dep_id == obj_id))
    resp = result.one_or_none()
    if resp:
        await session.delete(resp)
        await session.commit()
        return True
    else:
        raise IdNotFoundException(f"{model} id {obj_id} not found")
