import logging
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from celery import current_task, Task
from gevent import getcurrent as gevent_getcurrent

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """Sync database engine and session managment class for use in Celery workers"""

    def celery_task_scopefunc(self):
        return (current_task.request.id, gevent_getcurrent())

    def __init__(self):
        if os.getenv("SYNC_DATABASE_URL"):
            self._engine = create_engine(os.getenv("SYNC_DATABASE_URL",""), echo=False, pool_size=5, max_overflow=10)
            self._session = scoped_session(
                    sessionmaker(
                        autocommit=False,
                        autoflush=False,
                        expire_on_commit=False,
                        bind=self._engine 
                    ),
                    scopefunc=self.celery_task_scopefunc
                )
            
    def get_session(self):
        return self._session()
    
    def remove_session(self):
        self._session.remove()

session_manager = DatabaseSessionManager()

class DBTaskCM(Task):
    """ Base celery task that includes context manager for SqlAlchemy scoped session"""

    @contextmanager
    def get_session(self):
        session = session_manager.get_session()
        try:
            yield session
        except Exception as error:
            session.rollback()
            logger.error(error)
            raise
        finally:
            session_manager.remove_session()


class DBTaskCll(Task):
    """ Base celery task with callable to include SqlAlchemy scoped session"""

    def __call__(self, *args, **kwargs):
        self.session = session_manager.get_session()
        try:
            return super().__call__(*args, **kwargs)
        except Exception as error:
            self.session.rollback()
            logger.error(error)
            raise
        finally:
            logger.info("closing the session")
            session_manager.remove_session()