
import logging
import uuid
from typing import Type

from pydantic import AwareDatetime
from sqlmodel import SQLModel, and_, desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from hobbes.routers.auth import TokenData
from hobbes.models.artifiacts_model import (
    ProfileCreatePayload,
    ProfileCreateVersionPayload,
    ProfileResponse,
    Profiles,
    ProfilesPaginationResponse,
    ProfilesSearchResponse,
    ProfileVersions,
)

logger = logging.getLogger(__name__)


class ProfileNotFoundException(Exception):
    """crud exception when profile not found"""


class IdNotFoundException(Exception):
    """Id not found"""


async def add_profile(session: AsyncSession, payload: ProfileCreatePayload, token: TokenData) -> ProfileResponse:
    """
    Insert all new profile or a new version for existing profile name

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (ProfileCreatePayload): new profile
        token (TokenData): oauth token data

    Returns:
        UUID: profile version uuid
    """
    # create new profile
    pf = Profiles(prf_name=payload.prf_name, description=payload.description, username=token.username)
    session.add(pf)
    await session.flush()

    # create version
    pf_version = ProfileVersions(ver_data=payload.data, prf_id=pf.prf_id, username=token.username)
    session.add(pf_version)
    await session.commit()

    return ProfileResponse(
        prf_name=pf.prf_name,
        prf_id=pf.prf_id,
        description=pf.description if pf.description else "",
        create_dts=pf_version.create_dts,
        username=pf_version.username,
        ver_id=pf_version.ver_id,
        ver_data=pf_version.ver_data,
    )


async def add_profile_version(
    session: AsyncSession, profile_name: str, payload: ProfileCreateVersionPayload, token: TokenData
) -> ProfileResponse:
    """
    Create new profile version

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (ProfileCreateVersionPayload): new profile version
        token (TokenData): oauth token data

    Raises:
        ProfileNotFoundException: fails to find existing profile

    Returns:
        UUID: profile version uuid
    """
    result = await session.exec(select(Profiles).where(Profiles.prf_name == profile_name))
    pf = result.one_or_none()
    if not pf:
        raise ProfileNotFoundException(f"profile {profile_name} not found")

    # create version
    pf_version = ProfileVersions(ver_data=payload.data, prf_id=pf.prf_id, username=token.username)
    session.add(pf_version)
    await session.commit()

    return ProfileResponse(
        prf_name=pf.prf_name,
        prf_id=pf.prf_id,
        description=pf.description if pf.description else "",
        create_dts=pf_version.create_dts,
        username=pf_version.username,
        ver_id=pf_version.ver_id,
        ver_data=pf_version.ver_data,
    )


async def fetch_profiles(session: AsyncSession, offset: int, limit: int) -> ProfilesPaginationResponse:
    """
    Get all profiles object using offset and limit. Does not include versions. This is for paginating.

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (ProfileSearchPayload): search payload

    Returns:
        ProfileResponse: response containing list of profiles or empty list
    """
    total_query = await session.exec(select(func.count()).select_from(Profiles))
    total = total_query.one()

    if total > 0:
        result = await session.exec(
            select(Profiles).order_by(Profiles.prf_name, desc(Profiles.create_dts)).offset(offset).limit(limit)
        )

        rows = list(result.all())
    else:
        rows = []

    return ProfilesPaginationResponse(total=total, profiles=rows)


async def fetch_profile_version(
    session: AsyncSession, profile_name: str, search_date: AwareDatetime
) -> ProfileVersions:
    """
    Get most recent version of a profile prior to search_date

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (ProfileSearchPayload): search payload

    Raises:
        ProfileNotFoundException: profile not found

    Returns:
        ProfileVersions: response containing most recent profile version
    """
    result = await session.scalars(
        select(ProfileVersions)
        .join(Profiles)
        .where(Profiles.prf_name == profile_name, ProfileVersions.create_dts <= search_date)
        .order_by(desc(ProfileVersions.create_dts))
        .limit(1)
    )
    version = result.one_or_none()
    if version:
        return version
    raise ProfileNotFoundException(f"profile {profile_name} not found")


async def fetch_profile_versions(session: AsyncSession, profile_name: str) -> list[ProfileVersions]:
    """
    Get all versions from a profile name

    Args:
        session (AsyncSession): SQLModel scoped async session object
        profile_name (str): profile name

    Raises:
        ProfileNotFoundException: failed to find profile

    Returns:
        list[ProfileVersions]: profile versions
    """
    result = await session.exec(
        select(ProfileVersions)
        .join(Profiles)
        .where(and_(Profiles.prf_name == profile_name, ProfileVersions.prf_id == Profiles.prf_id))
    )
    rows = list(result.all())
    if len(rows) > 0:
        return rows
    raise ProfileNotFoundException(f"no profile versions found for {profile_name}")


async def fetch_by_id(session: AsyncSession, model: Type[SQLModel], obj_id: uuid.UUID):
    """
    Generic get row by id query

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
    raise ProfileNotFoundException(f"id {obj_id} not found")


async def find_profile(
    session: AsyncSession, profile_name: str, search_date: AwareDatetime
) -> list[ProfilesSearchResponse]:
    """
    Search for most recent version of a profile using a case insensitive profile name fragment in like query

    Args:
        session (AsyncSession): SQLModel scoped async session object
        payload (ProfileSearchPayload): search payload

    Raises:
        ProfileNotFoundException: profile not found

    Returns:
        ProfileVersions: response containing most recent profile version
    """
    result = await session.exec(
        select(Profiles, ProfileVersions)
        .join(Profiles)
        .where(Profiles.prf_name.ilike(f"{profile_name}%"), ProfileVersions.create_dts <= search_date)  # type: ignore
        .order_by(desc(ProfileVersions.create_dts))
    )

    rows = result.fetchall()
    if len(rows) > 0:
        resp = []
        for prof, prof_version in rows:
            resp.append(ProfilesSearchResponse(prf_name=prof.prf_name, prf_id=prof.prf_id, version=prof_version))
        return resp

    raise ProfileNotFoundException(f"no profiles found")


async def remove_profile(session: AsyncSession, profile_id: uuid.UUID) -> bool:
    """
    Delete dependency

    Args:
        session (AsyncSession): SQLModel scoped async session object
        obj_id (uuid.UUID): model id

    Returns:
        bool: delete success
    """

    result = await session.exec(select(ProfileVersions).where(ProfileVersions.prf_id == profile_id))
    if result:
        for vers in result.all():
            logger.debug("delete profile version %s", vers.ver_id)
            await session.delete(vers)
    else:
        raise IdNotFoundException(f"profile id {profile_id} not found")

    result = await session.exec(select(Profiles).where(Profiles.prf_id == profile_id))
    profile = result.one_or_none()
    await session.delete(profile)
    await session.commit()
    return True
