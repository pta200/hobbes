import logging
import re
from datetime import datetime

from hobbes.models import Book, BookPayload
from sqlalchemy import types
from sqlalchemy.orm import class_mapper
from sqlmodel import and_, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger(__name__)


def set_val_type(column, val):
    """determine column type and cast value accordingly

    Args:
        column (column): table column name
        val (str): column value separed from regex payload

    Returns:
        Obj: val as correct type
    """
    if type(column.type) is types.DateTime:
        return datetime.strptime(val, "%Y-%m-%dT%H:%M:%SZ")

    if type(column.type) is types.Integer:
        return int(val)

    # str
    return val


def generate_filter(column, v):
    """generated binary filter for column bases on regex from payload

    Args:
        column (column): table column name
        v (str): regex payload

    Returns:
        filter: binary filter on column
    """
    if re.match(r"^!", v):
        """__ne__"""
        val = re.sub(r"!", "", v)
        return column.__ne__(set_val_type(column, val))

    if re.match(r">(?!=)", v):
        """__gt__"""
        val = re.sub(r">(?!=)", "", v)
        logger.debug("match gt %s", val)
        return column.__gt__(set_val_type(column, val))

    if re.match(r"<(?!=)", v):
        """__lt__"""
        val = re.sub(r"<(?!=)", "", v)
        logger.debug("match lt %s", val)
        return column.__lt__(set_val_type(column, val))

    if re.match(r">=", v):
        """__ge__"""
        val = re.sub(r">=", "", v)
        return column.__ge__(set_val_type(column, val))

    if re.match(r"<=", v):
        """__le__"""
        val = re.sub(r"<=", "", v)
        return column.__le__(set_val_type(column, val))

    if re.match(r"(\w*),(\w*)", v):
        """between"""
        a, b = re.split(r",", v)
        return column.between((set_val_type(column, a)), (set_val_type(column, b)))

    if re.match(r"[A-Za-z0-9:-]*,[A-Za-z0-9:-]*", v):  # dates between
        """between"""
        a, b = re.split(r",", v)
        return column.between((set_val_type(column, a)), (set_val_type(column, b)))

    """ default __eq__ """
    return column.__eq__(set_val_type(column, v))


def build_query(table, filter_by):
    """build query with binary filter from fields included in payload search

    Args:
        table (SQLModel): SQLModel class
        filter_by (dict): Dictionary of columns and value to search on

    Returns:
        _type_: _description_
    """
    filters = []
    for k, v in filter_by.items():
        mapper = class_mapper(table)
        if not hasattr(mapper.columns, k):
            continue
        resp = generate_filter(mapper.columns[k], "{}".format(v))
        filters.append(resp)
    return filters


async def insert_stat(payload: BookPayload, session: AsyncSession):
    """insert render stat row

    Args:
        payload (BookPayload): payload from endpoint
        session (AsyncSession): SQLAlchemy scoped async session object
    """
    book = Book(
        title=payload.title,
        isbn=payload.isbn,
        genre=payload.genre,
        condition=payload.condition,
    )
    session.add(book)
    await session.commit()
    return


async def all_stats(session: AsyncSession):
    """query for all render stats in the table

    Args:
        session (AsyncSession): SQLAlchemy scoped async session object

    Returns:
        List[Book]: List of render stat objects
    """
    results = await session.scalars(
        select(Book).order_by(desc(Book.create_datetimestamp))
    )
    return results.all()


async def date_filter_stats(date_param: datetime, compare: str, session: AsyncSession):
    """Filter render stats by date

    Args:
        date_param (datetime): Datetime object to filter by
        compare (str): comparisson string 'gt' or 'lt'
        session (AsyncSession): SQLAlchemy scoped async session object

    Returns:
        List[Book]: List of render stat objects
    """
    if compare == "gt":
        results = await session.scalars(
            select(Book)
            .where(Book.create_datetimestamp > date_param)
            .order_by(desc(Book.create_datetimestamp))
        )
    else:
        results = await session.scalars(
            select(Book)
            .where(Book.create_datetimestamp < date_param)
            .order_by(desc(Book.create_datetimestamp))
        )
    return results.all()


async def filter_stats(filter_param: str, session: AsyncSession):
    """Filter render stats by any and all fields

    Args:
        filter_param (str): _description_
        session (AsyncSession): _description_

    Returns:
        List[Book]: List of render stat objects
    """
    results = await session.scalars(
        select(Book).filter(and_(*build_query(Book, filter_param)))
    )
    return results.all()
