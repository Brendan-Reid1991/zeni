from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from datetime import date


@dataclass(slots=True, frozen=True)
class Transaction:
    """Store the important details of a transaction."""

    date: date
    description: str
    amount: Decimal
    account: str
    currency: str | None = None
    uuid: str | None = None


class ZeniStrEnum(str, Enum):
    """A base class for all str enums in Zeni."""

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()


class Account(ZeniStrEnum):
    """Account enum."""

    DEBIT = auto()
    CREDIT = auto()
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
    DATE = auto()
    NAME = auto()
    NOTES = auto()
    CATEGORY = auto()
    AMOUNT = auto()
    CURRENCY = auto()
    BALANCE = auto()


class Addressable:
    def __init__(self, iterable: Iterable[str]):
        self.iterable = iterable
        if not all(isinstance(x, str) for x in iterable):
            raise ValueError(
                "To make an iterable addressable all elements must be strings."
            )
        for item in self.iterable:
            attr_name = item.lower().replace(" ", "_").replace("-", "_")
            if attr_name.isidentifier():
                setattr(self, attr_name, item)
            else:
                raise ValueError(f"Cannot convert '{item}' to a valid attribute name.")

    def __iter__(self) -> Iterator[str]:
        return self.iterable.__iter__()

    def __len__(self) -> int:
        return len(self.iterable)

    def __getitem__(self, index):
        return self.iterable[index]

    def __repr__(self):
        return self.iterable.__repr__()
