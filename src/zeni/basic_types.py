from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import StrEnum, auto
from typing import TypeAlias


class AccountType(StrEnum):
    """Basic enum to capture kinds of bank accounts."""

    CURRENT = auto()
    SAVINGS = auto()
    INVESTMENT = auto()
    CREDIT = auto()


class Payment(StrEnum):
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


class TransactionColumns(StrEnum):
    """The standard columns to be used when parsing bank statements into CSV.

    Ordering in this class is implicitly the "preferred" ordering.

    """

    DATE = auto()
    TIME = auto()
    NAME = auto()
    CATEGORY = auto()
    AMOUNT = auto()
    BALANCE = auto()
    CURRENCY = auto()
    NOTES = auto()


COLUMN_DTYPES: TypeAlias = str | date | time | Decimal | float | int
_NOW = datetime.now(tz=UTC)

COLUMN_DEFAULTS: dict[TransactionColumns, COLUMN_DTYPES] = {
    TransactionColumns.DATE: _NOW.date(),
    TransactionColumns.TIME: _NOW.time(),
    TransactionColumns.NAME: "None",
    TransactionColumns.CATEGORY: "None",
    TransactionColumns.AMOUNT: 0,
    TransactionColumns.CURRENCY: "GBP",
    TransactionColumns.NOTES: "",
    TransactionColumns.BALANCE: 0,
}
