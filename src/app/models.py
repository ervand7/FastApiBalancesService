import logging
import typing
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy.schema import Index
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship

from app.enums import TransactionType

logger = logging.getLogger(__name__)

METADATA: typing.Final = sa.MetaData()


class Base(DeclarativeBase):
    metadata = METADATA


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)
    balance: Mapped[Decimal] = mapped_column(sa.Numeric(precision=12, scale=2), default=0, server_default="0")

    transactions = relationship("Transaction", back_populates="user", lazy="selectin")
    snapshots = relationship("BalancesSnapshots", back_populates="user", lazy="selectin")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index('ix_transactions_user_id', 'user_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(sa.Numeric(precision=12, scale=2), nullable=False)
    type: Mapped[TransactionType] = mapped_column(sa.Enum(TransactionType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")


class BalancesSnapshots(Base):
    __tablename__ = "balances_snapshots"
    __table_args__ = (
        Index('ix_balances_snapshots_user_id_created_at_desc', 'user_id', sa.desc('created_at')),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False)
    balance: Mapped[Decimal] = mapped_column(sa.Numeric(precision=12, scale=2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="snapshots")
