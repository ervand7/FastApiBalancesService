import typing
import uuid
from datetime import datetime

import fastapi
from starlette import status

from app import schemas
from app.db.resources import get_payment_repo
from app.exceptions import (
    InsufficientFundsError,
    UserExistsError,
    UserNotExistsError,
    TransactionAmountZeroError,
    TransactionAlreadyExistsError, UnknownTransactionTypeError
)
from app.repositories import PaymentRepository

ROUTER: typing.Final = fastapi.APIRouter()


@ROUTER.post("/users/", response_model=schemas.User)
async def create_user(
        data: schemas.UserCreate,
        payment_repo: PaymentRepository = fastapi.Depends(get_payment_repo),
) -> schemas.User:
    try:
        user = await payment_repo.create_user(data)
    except UserExistsError as e:
        raise fastapi.HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    return typing.cast(schemas.User, user)


@ROUTER.post("/transactions/", response_model=schemas.Transaction)
async def create_transaction(
        data: schemas.TransactionCreate,
        payment_repo: PaymentRepository = fastapi.Depends(get_payment_repo),
) -> schemas.Transaction:
    try:
        transaction = await payment_repo.create_transaction(data)
    except (UserNotExistsError,
            TransactionAmountZeroError,
            TransactionAlreadyExistsError,
            UnknownTransactionTypeError) as e:
        raise fastapi.HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except InsufficientFundsError as e:
        raise fastapi.HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    return typing.cast(schemas.Transaction, transaction)


@ROUTER.get("/transactions/{transaction_id}")
async def get_transaction(
        transaction_id: uuid.UUID,
        payment_repo: PaymentRepository = fastapi.Depends(get_payment_repo),
) -> schemas.Transaction:
    transaction = await payment_repo.get_transaction(transaction_id)
    if transaction is None:
        raise fastapi.HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail="Transaction not found")
    return typing.cast(schemas.Transaction, transaction)


@ROUTER.get("/users/{user_id}/balance/", response_model=schemas.UserBalance)
async def get_user_balance(
        user_id: uuid.UUID,
        ts: datetime | None = None,
        payment_repo: PaymentRepository = fastapi.Depends(get_payment_repo),
) -> schemas.UserBalance:
    try:
        balance = await payment_repo.get_user_balance(user_id, ts=ts)
    except UserNotExistsError as e:
        raise fastapi.HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return typing.cast(schemas.UserBalance, {"balance": balance})
