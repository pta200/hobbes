import logging
import os
from pathlib import Path
import tomli
from contextlib import asynccontextmanager

from fastapi import FastAPI
from hobbes.apis_v1 import stat_router
from hobbes.db_manager import sessionmanager

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan funciton to execute steps before app starts and when it shuts downs.
    In this case init SQLAlchemy engine and create tables

    Args:
        app (FastAPI): FastAPI app
    """
    sessionmanager.init(DATABASE_URL)
    await sessionmanager.init_db()
    yield
    await sessionmanager.close()


# get project version from pyproject.toml
version = "0.0.1"
with open(Path(__file__).parent.parent / "pyproject.toml", "rb") as f:
    toml_dict = tomli.load(f)
    version = toml_dict["project"]["version"]


# init application
app = FastAPI(
    title="Hobbes Lab",
    description="lab testing work",
    version=version,
    lifespan=lifespan,
)

# add api endpoint
app.include_router(stat_router)


@app.get("/health")
async def health_check():
    """health check endpoint
    Returns:
        json: status ok
    """
    return {"status": "ok"}
