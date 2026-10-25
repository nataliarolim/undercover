"""The UnderCover backend."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from backend import claims, documents, runs
from backend.db import database_path
from backend.seed import seed


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Seed the database on the first start."""
    if not database_path().exists():
        seed()
    yield


api = APIRouter(prefix="/api")


@api.get("/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


api.include_router(claims.router)
api.include_router(documents.router)
api.include_router(runs.router)

app = FastAPI(title="UnderCover", lifespan=lifespan)
app.include_router(api)
