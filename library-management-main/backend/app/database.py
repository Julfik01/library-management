# backend/app/database.py
# SQLAlchemy 2.0 async data layer.
# CRITICAL: Never create a module-level shared AsyncSession — causes state corruption (CP-2).
# Always use async_sessionmaker with async with context manager per request.

from typing import AsyncGenerator, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,  # "postgresql+asyncpg://user:pass@host:5432/db"
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Per-request async DB session dependency. Always yields a fresh session."""
    async with AsyncSessionLocal() as session:
        yield session


# Convenience alias — use in route handler signatures:
# async def my_route(db: DbSession) -> ...:
DbSession = Annotated[AsyncSession, Depends(get_db)]
