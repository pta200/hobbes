import logging
import os
from pathlib import Path
import tomllib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from hobbes.apis_v1 import book_router
from hobbes.teams import teams_router
from hobbes.db_manager import async_session_manager

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("ASYNC_DATABASE_URL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan funciton to execute steps before app starts and when it shuts downs.
    In this case init SQLAlchemy engine and create tables

    Args:
        app (FastAPI): FastAPI app
    """
    async_session_manager.init(DATABASE_URL)
    await async_session_manager.init_db()
    yield
    await async_session_manager.close()


# get project version from pyproject.toml
version = "0.0.1"
with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
    toml_dict = tomllib.load(f)
    version = toml_dict["project"]["version"]


# init application
app = FastAPI(
    title="Hobbes Lab",
    description="lab testing work",
    version=version,
    lifespan=lifespan,
)

# add api endpoint
app.include_router(book_router)
app.include_router(teams_router)


@app.get("/health")
async def health_check():
    """health check endpoint
    Returns:
        json: status ok
    """
    return {"status": "ok"}
