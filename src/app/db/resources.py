import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession as AsyncSessionType,
)
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.base import get_db
from app.repositories import PaymentRepository

logger = logging.getLogger(__name__)


def get_payment_repo(
        db: async_sessionmaker[AsyncSessionType] = Depends(get_db),
) -> PaymentRepository:
    return PaymentRepository(
        db_session_maker=db,
    )
