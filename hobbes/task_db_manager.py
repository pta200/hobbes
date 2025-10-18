import logging
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from celery import current_task, Task
from gevent import getcurrent as gevent_getcurrent

logger = logging.getLogger(__name__)

def celery_task_scopefunc():
    return (current_task.request.id, gevent_getcurrent())


# create db engine
engine = create_engine(os.getenv("DATABASE_URL",""), echo=False, pool_size=5, max_overflow=10)

# create scoped sessions for gevent tasks
Scoped_session = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=engine
    ),
    scopefunc=celery_task_scopefunc
)


class DBTask(Task):
    """ Base celery task that includes SqlAlchemy scoped session"""
    
    @contextmanager
    def get_session(self):
        session = Scoped_session()
        try:
            yield session
        except Exception as error:
            session.rollback()
            logger.error(error)
            raise
        finally:
            # session.close()
            Scoped_session.remove()