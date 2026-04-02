
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import JSON, Column, DateTime, Enum, Field, SQLModel


def gen_utcnow():
    return datetime.now(timezone.utc)


class Profiles(SQLModel, table=True):
    """Profile table schema"""

    prf_id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False, primary_key=True)
    prf_name: str = Field(min_length=1, unique=True, index=True)
    description: Optional[str] = Field(default=None)
    username: str = Field(nullable=False, description="user who created the profile")
    create_dts: datetime = Field(default_factory=gen_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))


class ProfileVersions(SQLModel, table=True):
    """Profile version table schema"""

    ver_id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False, primary_key=True)
    prf_id: uuid.UUID = Field(nullable=False, foreign_key="profiles.prf_id")
    username: str = Field(nullable=False, description="user who created the version")
    # use variant so we can use JSON for sqlite for pytests and JSONB for postgres for service
    ver_data: dict = Field(sa_column=Column(JSONB().with_variant(JSON, "sqlite")))
    create_dts: datetime = Field(
        default_factory=gen_utcnow, sa_column=Column(DateTime(timezone=True), index=True, nullable=False)
    )


class ProfileCreatePayload(SQLModel):
    """Profile inbound REST payload"""

    prf_name: str = Field(min_length=1, description="Profile name with no spaces")
    description: Optional[str] = Field(default=None, description="Brief profile description")
    data: dict = Field(description="Profile data")


class ProfileCreateVersionPayload(SQLModel):
    """Profile version inbound REST payload"""

    data: dict = Field(description="Profile data")


class ProfileResponse(SQLModel):
    """get all profiles response"""

    prf_name: str
    prf_id: uuid.UUID
    description: str
    create_dts: datetime
    username: str
    ver_id: uuid.UUID
    ver_data: dict


class ProfilesSearchResponse(SQLModel):
    """Add profile response"""

    prf_name: str
    prf_id: uuid.UUID
    version: ProfileVersions


class PackageTypes(str, enum.Enum):
    """Package types"""

    PYPI = "pypi"
    ARCHIVE = "archive"
    GIT = "git"


class RepositoryCreatePayload(SQLModel):
    """Repository API"""

    rep_name: str
    rep_type: PackageTypes
    url: str


class RepositoryEditPayload(SQLModel):
    """Repository API"""

    rep_name: str
    rep_type: PackageTypes
    url: str


class Repositories(SQLModel, table=True):
    """Repos table schema"""

    rep_id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False, primary_key=True)
    rep_name: str = Field(min_length=1, unique=True, index=True)
    rep_type: PackageTypes = Field(
        sa_column=Column(
            Enum(PackageTypes),
            nullable=False,
        )
    )
    url: str = Field(nullable=False)
    create_dts: datetime = Field(default_factory=gen_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))


class DependencyCreatePayload(SQLModel):
    """Dependency API payload"""

    dep_name: str
    version: str
    relative_url: Optional[str] = None
    detail: Optional[str] = None
    rep_id: uuid.UUID


class DependencyEditPayload(SQLModel):
    """Dependency API payload"""

    dep_name: str
    version: str
    relative_url: Optional[str] = None
    detail: Optional[str] = None
    rep_id: uuid.UUID


class Dependencies(SQLModel, table=True):
    """Dependency version table schema"""

    dep_id: uuid.UUID = Field(default_factory=uuid.uuid4, nullable=False, primary_key=True)
    dep_name: str = Field(nullable=False)
    version: str = Field(nullable=False)
    relative_url: Optional[str] = Field(default=None)
    detail: Optional[str] = Field(default=None)
    rep_id: uuid.UUID = Field(nullable=False, foreign_key="repositories.rep_id")
    create_dts: datetime = Field(default_factory=gen_utcnow, sa_column=Column(DateTime(timezone=True), nullable=False))

    __table_args__ = (UniqueConstraint("dep_name", "version", name="unique_name_version_constraint"),)


class ProfilesPaginationResponse(SQLModel):
    """Pagination API response"""

    total: int
    profiles: list[Profiles]


class ArtifactPaginationResponse(SQLModel):
    """Pagination API response"""

    total: int
    rows: list[Repositories | Dependencies]
