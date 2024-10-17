import uuid
from datetime import datetime
from decimal import Decimal

import pydantic
from pydantic import BaseModel
from app.enums import TransactionType


class Base(BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)


class User(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime


class Transaction(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    type: TransactionType
    created_at: datetime

    model_config = pydantic.ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    id: uuid.UUID
    name: str


class TransactionCreate(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    amount: Decimal
    type: TransactionType


class UserBalance(BaseModel):
    balance: Decimal
