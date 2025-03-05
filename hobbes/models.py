import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Column, DateTime, Field, SQLModel


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
