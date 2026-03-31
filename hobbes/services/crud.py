import logging
import re
import uuid
from datetime import datetime

from sqlalchemy import types
from sqlalchemy.orm import class_mapper
from sqlmodel import and_, desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from hobbes.models.models import (
    Book,
    BookPayload,
    Hero,
    HeroPayload,
    PaginationResponse,
    Team,
    TeamPayload,
)

logger = logging.getLogger(__name__)


class BookNotFoundException(Exception):
    """Raised when a bank account has insufficient funds for a transaction."""

    pass


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


async def add_book(payload: BookPayload, session: AsyncSession):
    """insert render stat row

    Args:
        payload (BookPayload): payload from endpoint
        session (AsyncSession): SQLModel async scoped session object
    """
    book = Book(
        title=payload.title,
        isbn=payload.isbn,
        genre=payload.genre,
        condition=payload.condition,
    )
    session.add(book)
    await session.commit()
    return book


async def edit_book(book_id: uuid, payload: BookPayload, session: AsyncSession):
    """update book by id

    Args:
        book_id (uuid): book uuid
        payload (BookPayload): book payload
        session (AsyncSession): SQLModel async scoped session object
    """
    result = await session.exec(select(Book).where(Book.book_id == book_id))

    book = result.one_or_none()
    if book:
        if book.title != payload.title:
            book.title = payload.title

        if book.condition != payload.condition:
            book.condition = payload.condition

        if book.isbn != payload.isbn:
            book.isbn = payload.isbn

        session.add(book)
        await session.commit()
        await session.refresh(book)

        return book
    else:
        raise BookNotFoundException(f"book id {book_id} not found")


async def all_books(
    session: AsyncSession, offset: int, limit: int
) -> PaginationResponse:
    """query for all render stats in the table

    Args:
        session (AsyncSession): SQLModel async scoped session object

    Returns:
        List[Book]: List of render stat objects
    """
    result = await session.exec(select(func.count()).select_from(Book))
    total = result.one()

    results = await session.exec(
        select(Book)
        .order_by(desc(Book.create_datetimestamp))
        .offset(offset)
        .limit(limit)
    )
    response = PaginationResponse(total=total, rows=results.all())
    return response


async def date_filter_books(date_param: datetime, compare: str, session: AsyncSession):
    """Filter render stats by date

    Args:
        date_param (datetime): Datetime object to filter by
        compare (str): comparisson string 'gt' or 'lt'
        session (AsyncSession): SQLModel async scoped session object

    Returns:
        List[Book]: List of render stat objects
    """
    if compare == "gt":
        results = await session.exec(
            select(Book)
            .where(Book.create_datetimestamp > date_param)
            .order_by(desc(Book.create_datetimestamp))
        )
    else:
        results = await session.exec(
            select(Book)
            .where(Book.create_datetimestamp < date_param)
            .order_by(desc(Book.create_datetimestamp))
        )
    return results.all()


async def filter_books(filter_param: str, session: AsyncSession):
    """Filter render stats by any and all fields

    Args:
        filter_param (str): _description_
        session (AsyncSession): _description_

    Returns:
        List[Book]: List of render stat objects
    """
    results = await session.exec(
        select(Book).filter(and_(*build_query(Book, filter_param)))
    )
    return results.all()


async def search_recent_team_member(session: AsyncSession):
    """
    https://medium.com/@umair.qau586/sqlalchemy-seriespart-3-mastering-sqlalchemy-queries-and-aggregation-597befb46b09

    Args:
        session (AsyncSession): _description_

    Returns:
        _type_: _description_
    """

    sub = await session.scalars(
        select(
            Team.name,
            func.rank().over(
                order_by=desc(Hero.create_datetimestamp), partition_by=Team.name
            ),
        )
        .select_from(Team)
        .label("rank")
    ).subquery()

    result = await session.scalars(select(sub).filter(sub.c.rank == 1))
    resp = []
    logger.info(result)
    for hero, team in result:
        logger.info("Hero:", hero, "Team:", team)
        resp[team] = hero
    return resp


async def insert_team(payload: TeamPayload, session: AsyncSession) -> Team:
    """insert render stat row

    Args:
        payload (TeamPayload): payload from endpoint
        session (AsyncSession): SQLModel async scoped session object
    """
    team = Team(name=payload.name, headquarters=payload.headquarters)
    session.add(team)
    await session.commit()
    return Team


async def insert_hero(payload: HeroPayload, team: str, session: AsyncSession) -> Hero:
    """insert render stat row

    Args:
        payload (HeroPayload): payload from endpoint
        session (AsyncSession): SQLModel async scoped session object
    """
    resp = await session.scalars(select(Team).where(Team.name == team))
    tt = resp.one_or_none()
    hero = Hero(name=payload.name, secret_name=payload.secret_name, team_id=tt.tid)
    session.add(hero)
    await session.commit()
    return hero


async def insert_team_bundle(
    team_payload: TeamPayload, hero_payload: HeroPayload, session: AsyncSession
) -> tuple[Team, Hero]:
    """Insert a new hero into a new team

    Args:
        team_payload (TeamPayload): payload from endpoint
        hero_payload (HeroPayload):payload from endpoint
        session (AsyncSession): SQLModel async scoped session object
    """
    # handle bundle as a transaction
    team = Team(name=team_payload.name, headquarters=team_payload.headquarters)
    session.add(team)
    await session.flush()

    hero = Hero(
        name=hero_payload.name,
        secret_name=hero_payload.secret_name,
        team_id=team.tid,
        level=hero_payload.level,
    )
    session.add(hero)
    await session.commit()
    return team, hero
