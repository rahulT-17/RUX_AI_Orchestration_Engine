import os
import uuid
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy import delete
import sys
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Keep local pytest DB config deterministic even if shell env was previously
# set to CI credentials. TEST_DATABASE_URL can still override when needed.
_env_db_url = dotenv_values(ROOT / ".env").get("DATABASE_URL")
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")
elif _env_db_url:
    os.environ["DATABASE_URL"] = _env_db_url

from repositories.user_repository import UserRepository
from models import User

# Ensure a stable event loop across the whole test session.
# This avoids asyncpg/SQLAlchemy pools being created on one loop and used on another (Windows-specific issue).
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    from database import engine, Base
    # Ensures tables exist in the current DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def session():
    from database import AsyncSessionLocal
    async with AsyncSessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def test_user_id(session):
    uid = f"test_{uuid.uuid4().hex}"
    repo = UserRepository(session)
    await repo.create_user(uid)

    try:
        yield uid
    finally:
        # Cleanup: deleting the user should cascade to budgets/expenses (CASCADE on FKs)
        await session.execute(delete(User).where(User.user_id == uid))
        await session.commit()