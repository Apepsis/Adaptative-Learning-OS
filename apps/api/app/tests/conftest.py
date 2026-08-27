import asyncio
import sys
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

# psycopg's async mode can't run on Windows' default ProactorEventLoop —
# it needs a selector-based loop (documented psycopg limitation, not
# specific to this project). Only affects local test runs on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from app.core.security import get_current_user
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.modules.identity.models import User
from app.modules.identity.repository import UserRepository
from app.modules.identity.service import get_or_create_local_user
from app.storage.client import get_storage_client

settings = get_settings()

# Note on Celery: tests assert that ingestion is *enqueued* (mocking
# `ingest_source_task.delay`) rather than relying on the task's real
# execution. Each test's DB session lives inside a rolled-back SAVEPOINT
# (see db_session below); a real task run opens its own connection and
# would never see that uncommitted data, so exercising the worker's actual
# DB update belongs in a separate, non-transactional worker test instead.
#
# Note on fixture scope: the async engine/connection below is created fresh
# per test (function-scoped), not shared at session scope. asyncpg/psycopg
# async connections are bound to the event loop they were created on, and a
# session-scoped async fixture can end up straddling a different loop than
# the per-test loop pytest-asyncio uses, raising "attached to a different
# loop" errors. Recreating the engine per test costs a little time but
# avoids that class of flakiness entirely.


@pytest_asyncio.fixture
async def _ensure_buckets() -> None:
    # Not autouse: only tests that go through `client` (and therefore may
    # upload/delete objects) need MinIO reachable. Pure-logic tests
    # (parsing, chunking, ranking) must be able to run with no
    # infrastructure at all.
    storage = get_storage_client()
    await storage.ensure_bucket(settings.s3_bucket_originals)
    await storage.ensure_bucket(settings.s3_bucket_previews)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """One test = one engine, one outer transaction, rolled back at teardown.

    App code calling session.commit() only commits a SAVEPOINT
    (join_transaction_mode="create_savepoint"), so every test starts from a
    clean, isolated database state without needing a separate test DB.
    """
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def primary_user(db_session: AsyncSession) -> User:
    return await get_or_create_local_user(db_session, "primary-test-user@example.com")


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    user = await UserRepository(db_session).create(email="other-test-user@example.com")
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, primary_user: User, _ensure_buckets: None
) -> AsyncGenerator[AsyncClient]:
    async def _get_db_override() -> AsyncGenerator[AsyncSession]:
        yield db_session

    async def _get_current_user_override() -> User:
        return primary_user

    app.dependency_overrides[get_db] = _get_db_override
    app.dependency_overrides[get_current_user] = _get_current_user_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
