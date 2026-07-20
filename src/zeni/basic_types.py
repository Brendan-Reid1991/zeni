from __future__ import annotations

from datetime import UTC, date, datetime, time
from decimal import Decimal
from enum import StrEnum, auto
from typing import NamedTuple, TypeAlias


class AccountType(StrEnum):
    """Basic enum to capture kinds of bank accounts."""

    CURRENT = auto()
    SAVINGS = auto()
    INVESTMENT = auto()
    CREDIT = auto()


class Account(NamedTuple):
    """Data structure for storing information about an account."""

    bank: str
    type: AccountType


class Payment(StrEnum): ...


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


class StandardColumns(StrEnum):
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

COLUMN_DEFAULTS: dict[StandardColumns, COLUMN_DTYPES] = {
    StandardColumns.DATE: _NOW.date(),
    StandardColumns.TIME: _NOW.time(),
    StandardColumns.NAME: "None",
    StandardColumns.CATEGORY: "None",
    StandardColumns.AMOUNT: 0,
    StandardColumns.CURRENCY: "GBP",
    StandardColumns.NOTES: "",
    StandardColumns.BALANCE: 0,
}


TransactionFields = StrEnum(
    "TransactionFields",
    ["ID", "BANK", "ACCOUNT"]
    + [entry.name for entry in StandardColumns]
    + ["CREATED_AT", "UPDATED_AT"],
)
"""Enum for defining the fields used in database entries. Same as StandardColumns
with other metadata fields."""
