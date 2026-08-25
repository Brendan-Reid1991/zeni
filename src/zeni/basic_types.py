from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import EnumMeta, StrEnum, auto


class _ZeniEnum(EnumMeta):
    @property
    def keys(cls) -> tuple[str, ...]:
        """Get the keys of the enum as a pain tuple."""
        return tuple(cls._member_names_)


class AccountType(StrEnum, metaclass=_ZeniEnum):
    """Basic enum to capture kinds of bank accounts."""

    CURRENT = auto()
    SAVINGS = auto()
    INVESTMENT = auto()
    CREDIT = auto()


class Payment(StrEnum, metaclass=_ZeniEnum):
    """Base enum for all payment types."""


class Outgoing(Payment):
    """Outgoing payment categories."""

    RENT = auto()
    BILL = auto()
    SUBSCRIPTION = auto()
    CASH_WITHDRAWAL = auto()
    TRANSFER_OUT_EXTERNAL = auto()
    INVESTMENT = auto()
    FEE = auto()
    LOAN_PAYMENT = auto()
    CREDIT_CARD = auto()
    LEISURE = auto()
    UNCATEGORISED = auto()
    GROCERIES = auto()


class Incoming(Payment):
    """Incoming payment categories."""

    SALARY = auto()
    INTEREST = auto()
    REFUND = auto()
    TRANSFER_IN_EXTERNAL = auto()
    CASH_DEPOSIT = auto()
    INCOME = auto()


class Internal(Payment):
    """Internal payment categories."""

    TRANSFER = auto()
    SAVINGS = auto()
    ROUNDUP = auto()


class TransactionColumns(StrEnum, metaclass=_ZeniEnum):
    """The standard columns to be used when parsing bank statements into CSV.

    Ordering in this class is implicitly the "preferred" ordering.

    """

    DATE = auto()
    NAME = auto()
    CATEGORY = auto()
    AMOUNT = auto()
    BALANCE = auto()
    CURRENCY = auto()
    NOTES = auto()


class ColumnFlags(StrEnum, metaclass=_ZeniEnum):
    IGNORE = auto()
    """Flag to ignore a column in a statement."""

    TIMELIKE = auto()
    """Flag to detect a time-like column if it is reported separately."""


type COLUMN_DTYPES = str | date | time | Decimal | float | int
_NOW = datetime.now(tz=UTC)

COLUMN_DEFAULTS: dict[TransactionColumns, COLUMN_DTYPES] = {
    TransactionColumns.DATE: _NOW,
    TransactionColumns.NAME: "None",
    TransactionColumns.CATEGORY: "None",
    TransactionColumns.AMOUNT: 0,
    TransactionColumns.CURRENCY: "GBP",
    TransactionColumns.NOTES: "",
    TransactionColumns.BALANCE: 0,
}
