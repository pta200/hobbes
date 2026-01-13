import uuid
import enum
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from sqlmodel import Column, DateTime, Field, SQLModel, JSON, Enum


def gen_utcnow():
    return datetime.now(timezone.utc)


class BookPayload(SQLModel):
    title: str = Field(min_length=1)
    isbn: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    condition: str = Field(min_length=1)


class Book(BookPayload, table=True):
    isbn: str = Field(index=True, nullable=False)
    book_id: uuid.UUID = Field(
        default_factory=uuid.uuid4, nullable=False, primary_key=True
    )
    create_datetimestamp: datetime = Field(
        default_factory=gen_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class BookFilter(SQLModel):
    title: Optional[str] = None
    isbn: Optional[str] = None
    genre: Optional[str] = None
    condition: Optional[str] = None
    create_datetimestamp: Optional[str] = None


class TaskResponse(BaseModel):
    task_id: str
    task_status: str
    task_result: str

class TeamPayload(SQLModel):
    name: str = Field(index=True)
    headquarters: str

class Team(TeamPayload, table=True):
    tid: uuid.UUID = Field(
        default_factory=uuid.uuid4, nullable=False, primary_key=True
    )
    create_datetimestamp: datetime = Field(
        default_factory=gen_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

class HeroPayload(SQLModel):
    name: str = Field(index=True)
    secret_name: str

class MutantClass(str, enum.Enum):
    """Mutant hero types"""

    PYPI = "pypi"
    ARCHIVE = "archive"
    GIT = "git"
    OMEGA = "omega"
    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "Gamma"
    DELTA = "delta"
    EPSILON = "epsilon"

class Hero(HeroPayload, table=True):
    hid: uuid.UUID = Field(
        default_factory=uuid.uuid4, nullable=False, primary_key=True
    )
    team_id: uuid.UUID = Field(nullable=False, foreign_key="team.tid")
    create_datetimestamp: datetime = Field(
        default_factory=gen_utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    level = MutantClass = Field(
        sa_column=Column(
            Enum(MutantClass),
            nullable=False,
        )
    )
    # variant for testing with sqlite
    powers: dict = Field(sa_column=Column(JSONB().with_variant(JSON, "sqlite")))
