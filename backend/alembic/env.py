# backend/alembic/env.py
# CRITICAL: Use async template (async_engine_from_config + asyncio.run).
# The sync template hangs with asyncpg driver (Pitfall 1).
# CRITICAL: Import ALL models before target_metadata assignment.
# Missing imports result in an empty migration — Base.metadata will be empty (Pitfall 2).

import asyncio
import os

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# CRITICAL: Import ALL four model modules to populate Base.metadata.
# Order matters: user.py first (defines Base), then dependent models.
from app.models.user import Base, User  # noqa: F401 — import required to populate metadata
from app.models.book import Book  # noqa: F401
from app.models.borrow_request import BorrowRequest  # noqa: F401
from app.models.loan import Loan  # noqa: F401

# this is the Alembic Config object, providing access to values within alembic.ini
config = context.config

# Read DB URL from environment (T-01-01: never hardcode credentials in alembic.ini)
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Run migrations using an async engine (required for asyncpg driver)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Required for migration context — no connection pooling
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online():
    """Called by Alembic to run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


run_migrations_online()
