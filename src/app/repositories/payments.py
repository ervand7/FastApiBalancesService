import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Type

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncSession as AsyncSessionType, AsyncSession,
)

from app.enums import TransactionType
from app.exceptions import UserExistsError, InsufficientFundsError, UserNotExistsError, TransactionAmountZeroError, \
    TransactionAlreadyExistsError, UnknownTransactionTypeError
from app.models import User, Transaction, BalancesSnapshots
from app.schemas import UserCreate, TransactionCreate


class PaymentRepository:
    def __init__(self, db_session_maker: async_sessionmaker[AsyncSessionType]):
        self.db_session_maker = db_session_maker

    async def create_user(self, data: UserCreate) -> User:
        async with self.db_session_maker() as session:
            existing_user = await session.get(User, data.id)
            if existing_user is not None:
                raise UserExistsError(f"User with ID {data.id} already exists")
            new_user = User(id=data.id, name=data.name)
            session.add(new_user)
            await session.commit()

            return new_user

    async def create_transaction(self, data: TransactionCreate) -> Transaction:
        async with self.db_session_maker() as sql_tx:
            async with sql_tx.begin():
                user = await sql_tx.get(User, data.user_id, with_for_update=True)
                await self._check_new_transaction_input_data(sql_tx, data, user)
                await self._update_user_balance(user, data.amount, data.type)
                await self._create_balances_snapshots(sql_tx, user)

                transaction = Transaction(
                    id=data.id,
                    user_id=data.user_id,
                    amount=data.amount,
                    type=data.type,
                )
                sql_tx.add(transaction)
                await sql_tx.commit()

                return transaction

    async def get_transaction(self, transaction_id: uuid.UUID) -> Optional[Transaction]:
        async with self.db_session_maker() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            transaction = result.scalar_one_or_none()

            return transaction

    async def get_user_balance(
            self,
            user_id: uuid.UUID,
            ts: datetime = None) -> Decimal:
        async with self.db_session_maker() as session:
            user = await session.get(User, user_id)
            if not user:
                raise UserNotExistsError(f"User with ID {user_id} does not exist")

            if ts is None:
                return user.balance or Decimal(0)
            else:
                query = (
                    sa.select(BalancesSnapshots.balance)
                    .where(BalancesSnapshots.user_id == user_id)
                    .where(BalancesSnapshots.created_at <= ts)
                    .order_by(BalancesSnapshots.created_at.desc())
                    .limit(1)
                )
                result = await session.execute(query)
                balance = result.scalar()

                return balance or Decimal(0)

    @staticmethod
    async def _check_new_transaction_input_data(
            sql_tx: AsyncSession,
            data: TransactionCreate,
            user: Optional[Type[User]]) -> None:
        if not user:
            raise UserNotExistsError(f"User with ID {data.user_id} does not exist")

        if data.amount.is_zero():
            raise TransactionAmountZeroError("Zero transaction amount")

        existing_transaction = await sql_tx.get(Transaction, data.id)
        if existing_transaction is not None:
            raise TransactionAlreadyExistsError(f"Transaction with ID {data.id} already exists")

    @staticmethod
    async def _update_user_balance(
            user: Type[User],
            amount: Decimal,
            transaction_type: TransactionType) -> None:
        if transaction_type == TransactionType.WITHDRAW:
            if user.balance < amount:
                raise InsufficientFundsError("Insufficient funds")
            user.balance -= amount
        elif transaction_type == TransactionType.DEPOSIT:
            user.balance += amount
        else:
            raise UnknownTransactionTypeError(f"Unknown transaction type: {transaction_type}")

    @staticmethod
    async def _create_balances_snapshots(
            sql_tx: AsyncSession,
            user: Type[User]) -> None:
        snapshot = BalancesSnapshots(
            user_id=user.id,
            balance=user.balance,
        )
        sql_tx.add(snapshot)
