class InsufficientFundsError(Exception):
    pass


class UserExistsError(Exception):
    pass


class UserNotExistsError(Exception):
    pass


class TransactionAmountZeroError(Exception):
    pass


class TransactionAlreadyExistsError(Exception):
    pass


class UnknownTransactionTypeError(Exception):
    pass
