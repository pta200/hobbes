import logging
import os
from pathlib import Path
import tomllib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from hobbes.apis_v1 import book_router
from hobbes.teams import teams_router
from hobbes.db_manager import async_session_manager
from hobbes.iam import auth_router

logger = logging.getLogger(__name__)

DB_USERNAME = os.environ.get("DB_USERNAME")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")
DB_NAME = os.environ.get("DB_NAME")
DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5173",
]


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

# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# add api endpoint
app.include_router(book_router)
app.include_router(teams_router)
app.include_router(auth_router)


@app.get("/health")
async def health_check():
    """health check endpoint
    Returns:
        json: status ok
    """
    return {"status": "ok"}
