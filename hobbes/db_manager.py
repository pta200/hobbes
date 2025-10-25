import logging
from asyncio import current_task

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import SQLModel

logger = logging.getLogger(__name__)


class DatabaseAsyncSessionManager:
    """Async database engine and session managment class for use in FastAPI lifespan"""

    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._async_session: AsyncSession | None = None

    def init(self, database_url):
        self._engine = create_async_engine(
            database_url, echo=False, future=True, pool_size=5, max_overflow=10
        )
        # async scoped session using event current task
        self._async_session = async_scoped_session(
            async_sessionmaker(
                self._engine,
                expire_on_commit=False,
            ),
            scopefunc=current_task,
        )

    async def init_db(self):
        """create all tables"""
        async with self._engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def close(self):
        """shutdown datbase engine"""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._async_session = None
        else:
            logger.error("DatabaseSessionManager was never initialized")

    async def get_async_session(self):
        """return scoped AsyncSession object

        Returns:
            AsyncSession: SQLAlchemy session object
        """
        return self._async_session()

    async def remove_session(self):
        """removes async scope session
        https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#asyncio-scoped-session
        """
        await self._async_session.remove()


# manager instance
async_session_manager = DatabaseAsyncSessionManager()


async def get_async_session():
    """create async session used with FastAPI Dependency injection

    other way to handle it:
    async_session = async_sessionmaker(
        engine, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

    https://fastapi.tiangolo.com/es/tutorial/dependencies/dependencies-with-yield/#always-raise-in-dependencies-with-yield-and-except

    Yields:
        session (AsyncSession): Asyn SQLAlchemy session
    """

    # get scoped session
    session = await async_session_manager.get_async_session()
    try:
        yield session
    except Exception as error:
        await session.rollback()
        logger.error(error)
        raise
    finally:
        # remove session when task is complete
        await async_session_manager.remove_session()
