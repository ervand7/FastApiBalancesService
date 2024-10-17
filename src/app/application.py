import contextlib
import typing

import fastapi
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
    AsyncSession as AsyncSessionType,
    AsyncEngine,
)

from app.api.payments import ROUTER
from app.db.base import get_db
from app.models import Base
from app.settings import Settings


def include_routers(app: fastapi.FastAPI) -> None:
    app.include_router(ROUTER, prefix="/api")


class AppBuilder:
    _async_engine: AsyncEngine
    _session_maker: async_sessionmaker[AsyncSessionType]

    def __init__(self) -> None:
        self.settings = Settings()
        self.app: fastapi.FastAPI = fastapi.FastAPI(
            title=self.settings.service_name,
            debug=self.settings.debug,
            lifespan=self.lifespan_manager,
        )

        self.app.dependency_overrides[get_db] = self.get_async_session_maker
        include_routers(self.app)

    async def get_async_session_maker(self) -> AsyncSessionType:
        return self._session_maker

    async def init_async_resources(self) -> None:
        self._async_engine = create_async_engine(self.settings.db_dsn)
        self._session_maker = async_sessionmaker(bind=self._async_engine, expire_on_commit=False)

        async with self._async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def tear_down(self) -> None:
        await self._async_engine.dispose()

    @contextlib.asynccontextmanager
    async def lifespan_manager(self, _: fastapi.FastAPI) -> typing.AsyncIterator[dict[str, typing.Any]]:
        try:
            await self.init_async_resources()
            yield {}
        finally:
            await self.tear_down()


application = AppBuilder().app
