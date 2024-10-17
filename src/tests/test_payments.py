import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

import pytest
import sqlalchemy as sa

from app.enums import TransactionType
from app.exceptions import (
    TransactionAmountZeroError,
    UserExistsError,
    UserNotExistsError,
    TransactionAlreadyExistsError,
    InsufficientFundsError
)
from app.models import BalancesSnapshots, Transaction
from app.repositories.payments import PaymentRepository
from app.schemas import TransactionCreate, UserCreate


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_success(self, db_session):
        repo = PaymentRepository(db_session)

        name = "Test User"
        user_id = uuid.uuid4()
        user_data = UserCreate(id=user_id, name=name)

        user = await repo.create_user(user_data)
        assert user.id == user_id
        assert user.name == name

        with pytest.raises(UserExistsError):
            await repo.create_user(user_data)


class TestCreateTransaction:
    @pytest.mark.asynkio
    async def test_fail_uses_not_exists(self, db_session):
        repo = PaymentRepository(db_session)

        transaction = TransactionCreate(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            amount=Decimal(0),
            type=TransactionType.DEPOSIT
        )

        with pytest.raises(UserNotExistsError):
            await repo.create_transaction(transaction)

    @pytest.mark.asynkio
    async def test_fail_amount_is_zero(self, db_session, user):
        repo = PaymentRepository(db_session)

        transaction = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=Decimal(0),
            type=TransactionType.DEPOSIT
        )

        with pytest.raises(TransactionAmountZeroError):
            await repo.create_transaction(transaction)

    @pytest.mark.asynkio
    async def test_fail_transaction_already_exists(self, db_session, user):
        repo = PaymentRepository(db_session)

        amount = Decimal(1)
        transaction = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=amount,
            type=TransactionType.DEPOSIT
        )

        await repo.create_transaction(transaction)

        with pytest.raises(TransactionAlreadyExistsError):
            await repo.create_transaction(transaction)

        # Verify that the balance is correct and only increased once
        final_balance = await repo.get_user_balance(user.id)
        assert final_balance == amount

    @pytest.mark.asynkio
    async def test_fail_insufficient_funds(self, db_session, user):
        repo = PaymentRepository(db_session)

        transaction = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=Decimal(1),
            type=TransactionType.WITHDRAW
        )

        with pytest.raises(InsufficientFundsError):
            await repo.create_transaction(transaction)

    @pytest.mark.asyncio
    async def test_success_atomicity_concurrent_withdrawals(self, db_session, user):
        repo = PaymentRepository(db_session)

        initial_deposit = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=Decimal('100.00'),
            type=TransactionType.DEPOSIT
        )
        await repo.create_transaction(initial_deposit)

        # Define two withdrawal transactions that together exceed the balance
        withdrawal_amount = Decimal('60.00')
        withdrawal1 = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=withdrawal_amount,
            type=TransactionType.WITHDRAW
        )
        withdrawal2 = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=withdrawal_amount,
            type=TransactionType.WITHDRAW
        )

        # Function to perform a withdrawal
        async def perform_withdrawal(transaction):
            try:
                await repo.create_transaction(transaction)
                return True
            except InsufficientFundsError:
                return False

        # Run both withdrawals concurrently
        results = await asyncio.gather(
            perform_withdrawal(withdrawal1),
            perform_withdrawal(withdrawal2)
        )

        assert sum(results) == 1

        final_balance = await repo.get_user_balance(user.id)
        assert final_balance == Decimal('40.00')  # 100 - 60 = 40

    @pytest.mark.asyncio
    async def test_success_balance_and_snapshot_consistency(self, db_session, user):
        repo = PaymentRepository(db_session)

        deposit_amount = Decimal('75.00')
        deposit_transaction = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=deposit_amount,
            type=TransactionType.DEPOSIT
        )

        await repo.create_transaction(deposit_transaction)

        balance = await repo.get_user_balance(user.id)
        assert balance == deposit_amount

        async with db_session() as session:
            query = (
                sa.select(BalancesSnapshots)
                .where(BalancesSnapshots.user_id == user.id)
                .order_by(BalancesSnapshots.created_at.desc())
                .limit(1)
            )
            result = await session.execute(query)
            snapshot = result.scalar_one_or_none()

        assert snapshot is not None
        assert snapshot.balance == deposit_amount

    @pytest.mark.asyncio
    async def test_atomicity_concurrent_deposits(self, db_session, user):
        repo = PaymentRepository(db_session)

        deposit_amount = Decimal('30.00')
        deposit1 = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=deposit_amount,
            type=TransactionType.DEPOSIT
        )
        deposit2 = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=deposit_amount,
            type=TransactionType.DEPOSIT
        )

        async def perform_deposit(transaction):
            await repo.create_transaction(transaction)
            return True

        # Run both deposits concurrently
        results = await asyncio.gather(
            perform_deposit(deposit1),
            perform_deposit(deposit2)
        )

        # Both deposits should succeed
        assert all(results)

        # Check the final balance
        final_balance = await repo.get_user_balance(user.id)
        expected_balance = deposit_amount * 2  # $60.00
        assert final_balance == expected_balance

    @pytest.mark.asyncio
    async def test_success_get_balance_as_of_date(self, db_session, user):
        repo = PaymentRepository(db_session)

        # Initial deposit
        initial_deposit = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=Decimal('100.00'),
            type=TransactionType.DEPOSIT
        )
        await repo.create_transaction(initial_deposit)

        # Record the time after the initial deposit
        after_initial_deposit = datetime.utcnow()

        # Wait a bit and make another transaction
        await asyncio.sleep(1)

        # Second deposit
        second_deposit = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=Decimal('50.00'),
            type=TransactionType.DEPOSIT
        )
        await repo.create_transaction(second_deposit)

        # Retrieve balance as of time after initial deposit
        balance_as_of = await repo.get_user_balance(user.id, after_initial_deposit)

        # The balance should reflect only the initial deposit
        assert balance_as_of == Decimal('100.00')

        # Verify current balance includes both deposits
        current_balance = await repo.get_user_balance(user.id)
        assert current_balance == Decimal('150.00')

    @pytest.mark.asyncio
    async def test_transaction_failure_rolls_back_changes(self, db_session, user):
        repo = PaymentRepository(db_session)

        initial_deposit = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=Decimal('50.00'),
            type=TransactionType.DEPOSIT
        )
        await repo.create_transaction(initial_deposit)

        withdrawal = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=Decimal('100.00'),
            type=TransactionType.WITHDRAW
        )

        with pytest.raises(InsufficientFundsError):
            await repo.create_transaction(withdrawal)

        # Verify that balance remains unchanged
        final_balance = await repo.get_user_balance(user.id)
        assert final_balance == Decimal('50.00')

        # Verify that no withdrawal transaction was created
        transaction = await repo.get_transaction(withdrawal.id)
        assert transaction is None

    @pytest.mark.asyncio
    async def test_success_idempotency_with_retries(self, db_session, user):
        repo = PaymentRepository(db_session)

        deposit_amount = Decimal('25.00')
        transaction_id = uuid.uuid4()
        deposit_transaction = TransactionCreate(
            id=transaction_id,
            user_id=user.id,
            amount=deposit_amount,
            type=TransactionType.DEPOSIT
        )

        # Simulate retrying the same transaction due to network issues
        for _ in range(3):
            try:
                await repo.create_transaction(deposit_transaction)
            except TransactionAlreadyExistsError:
                pass  # Ignore the error on retries

        # Verify that the balance is only increased once
        final_balance = await repo.get_user_balance(user.id)
        assert final_balance == deposit_amount

        # Verify only one transaction exists with that ID
        async with db_session() as session:
            query = (
                sa.select(sa.func.count(Transaction.id))
                .where(Transaction.id == transaction_id)
            )
            result = await session.execute(query)
            count = result.scalar()
            assert count == 1


class TestGetTransaction:
    @pytest.mark.asyncio
    async def test_success_get_existing_transaction(self, db_session, user):
        repo = PaymentRepository(db_session)
        transaction = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=Decimal('100.00'),
            type=TransactionType.DEPOSIT
        )
        await repo.create_transaction(transaction)

        transaction = await repo.get_transaction(transaction.id)

        assert transaction is not None
        assert transaction.id == transaction.id
        assert transaction.user_id == user.id
        assert transaction.amount == transaction.amount
        assert transaction.type == transaction.type

    @pytest.mark.asyncio
    async def test_fail_get_nonexistent_transaction(self, db_session):
        repo = PaymentRepository(db_session)
        non_existent_id = str(uuid.uuid4())

        transaction = await repo.get_transaction(non_existent_id)

        assert transaction is None


class TestGetUserBalance:
    @pytest.mark.asyncio
    async def test_success_get_current_balance(self, db_session, user):
        repo = PaymentRepository(db_session)

        deposit_amount = Decimal('100.00')
        deposit = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=deposit_amount,
            type=TransactionType.DEPOSIT
        )
        await repo.create_transaction(deposit)

        withdrawal_amount = Decimal('30.00')
        withdrawal = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=withdrawal_amount,
            type=TransactionType.WITHDRAW
        )
        await repo.create_transaction(withdrawal)

        balance = await repo.get_user_balance(user.id)
        expected_balance = deposit_amount - withdrawal_amount
        assert balance == expected_balance

    @pytest.mark.asyncio
    async def test_fail_get_balance_user_not_exists(self, db_session):
        repo = PaymentRepository(db_session)
        non_existent_user_id = str(uuid.uuid4())

        with pytest.raises(UserNotExistsError):
            await repo.get_user_balance(non_existent_user_id)

    @pytest.mark.asyncio
    async def test_success_get_balance_with_ts_snapshots_exist(self, db_session, user):
        repo = PaymentRepository(db_session)

        deposit_amount = Decimal('100.00')
        deposit = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=deposit_amount,
            type=TransactionType.DEPOSIT
        )
        await repo.create_transaction(deposit)

        ts_after_deposit = datetime.utcnow()
        await asyncio.sleep(0.1)

        withdrawal_amount = Decimal('40.00')
        withdrawal = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=withdrawal_amount,
            type=TransactionType.WITHDRAW
        )
        await repo.create_transaction(withdrawal)

        balance = await repo.get_user_balance(user.id, ts_after_deposit)
        expected_balance = deposit_amount

        assert balance == expected_balance

    @pytest.mark.asyncio
    async def test_success_get_balance_with_ts_no_snapshots(self, db_session, user):
        repo = PaymentRepository(db_session)
        ts_before_transactions = datetime.utcnow()
        await asyncio.sleep(0.1)

        deposit_amount = Decimal('50.00')
        deposit = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=deposit_amount,
            type=TransactionType.DEPOSIT
        )
        await repo.create_transaction(deposit)

        balance = await repo.get_user_balance(user.id, ts_before_transactions)
        assert balance == Decimal(0)

    @pytest.mark.asyncio
    async def test_success_get_balance_with_ts_snapshot_at_ts(self, db_session, user):
        repo = PaymentRepository(db_session)
        deposit_amount = Decimal('200.00')
        deposit = TransactionCreate(
            id=uuid.uuid4(),
            user_id=user.id,
            amount=deposit_amount,
            type=TransactionType.DEPOSIT
        )

        await repo.create_transaction(deposit)
        async with db_session() as session:
            query = (
                sa.select(BalancesSnapshots.created_at)
                .where(BalancesSnapshots.user_id == user.id)
                .order_by(BalancesSnapshots.created_at.desc())
                .limit(1)
            )
            result = await session.execute(query)
            snapshot_ts = result.scalar()

        balance = await repo.get_user_balance(user.id, snapshot_ts)

        assert balance == deposit_amount