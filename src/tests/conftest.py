import os
import uuid

import dotenv
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models import Base
from app.repositories import PaymentRepository
from app.schemas import UserCreate

dotenv.load_dotenv()


@pytest.fixture(scope="function")
async def db_session():
    engine = create_async_engine(os.getenv("TEST_DATABASE_URL"), echo=True, future=True)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_session_maker

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def user(db_session) -> UserCreate:
    repo = PaymentRepository(db_session)
    user_data = UserCreate(id=uuid.uuid4(), name="Test User")
    await repo.create_user(user_data)

    return user_data