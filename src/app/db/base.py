import logging
import typing

from sqlalchemy.ext import asyncio as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from app.settings import get_settings

logger = logging.getLogger(__name__)

engine: AsyncEngine = create_async_engine(get_settings().db_dsn)


async def create_session(_engine: sa.AsyncEngine) -> typing.AsyncIterator[sa.AsyncSession]:
    async with sa.AsyncSession(_engine, expire_on_commit=False, autoflush=False) as session:
        yield session


async def get_db():
    async for session in create_session(engine):
        yield session
