from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import engine
from app.models import *  # noqa: F401, F403
from app.core.database import Base
from app.routers import auth, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="FastAPI RBAC",
    description="User management API with Role-Based Access Control",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
