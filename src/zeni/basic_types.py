from __future__ import annotations

from enum import Enum, auto


class ZeniStrEnum(str, Enum):
    """A base class for all str enums in Zeni."""

    value: str

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return self.value

    @staticmethod
    def _generate_next_value_(
        name: str, start: int, count: int, last_values: list[str]
    ) -> str:
        return name.lower()


class Account(ZeniStrEnum):
    """Account enum."""

    CURRENT = auto()
    CREDIT_CARD = auto()
    SAVINGS = auto()
    ISA = auto()


class Payment(ZeniStrEnum): ...


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


class StandardColumns(ZeniStrEnum):
    """The standard columns to be used when parsing bank statements into CSV.

    Ordering in this class is implicitly the "preferred" ordering.

    """

    DATE = auto()
    TIME = auto()
    NAME = auto()
    CATEGORY = auto()
    AMOUNT = auto()
    CURRENCY = auto()
    NOTES = auto()
    BALANCE = auto()


TransactionFields = ZeniStrEnum(
    "TransactionFields",
    ["ID", "BANK", "ACCOUNT"]
    + [entry.name for entry in StandardColumns]
    + ["CREATED_AT", "UPDATED_AT"],
)
"""Enum for defining the fields used in database entries. Same as StandardColumns
with other metadata fields."""
