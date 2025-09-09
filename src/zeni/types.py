from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


@dataclass(slots=True, frozen=True)
class Transaction:
    """Store the important details of a transaction."""

    date: date
    description: str
    amount: float
    account: str
    currency: str | None = None
    uuid: str | None = None


class Account(str, Enum):
    """Account enum."""

    DEBIT = "debit"
    CREDIT = "credit"
    SAVINGS = "savings"
    ISA = "isa"


class Payment(str, Enum): ...


class Outgoing(Payment):
    """Outgoing payment categories."""

    RENT = "rent"
    BILL = "bill"
    SUBSCRIPTION = "subscription"
    CASH_WITHDRAWAL = "cash_withdrawal"
    TRANSFER_OUT_EXTERNAL = "transfer_out_external"
    FEE = "fee"
    LOAN_PAYMENT = "loan_payment"
    CREDIT_CARD = "credit_card"
    LEISURE = "leisure"
    UNCATEGORISED = "uncategorised"
    GROCERIES = "groceries"


class Incoming(Payment):
    """Incoming payment categories."""

    SALARY = "salary"
    INTEREST = "interest"
    REFUND = "refund"
    TRANSFER_IN_EXTERNAL = "transfer_in_external"
    CASH_DEPOSIT = "cash_deposit"


class Internal(Payment):
    """Internal payment categories."""

    TRANSFER = "transfer"
    SAVINGS = "savings"
    ROUNDUP = "roundup"


class StandardColumns(str, Enum):
    DATE = "date"
    TIME = "time"
    TYPE = "type"
    CATEGORY = "category"
    NAME = "name"
    AMOUNT = "amount"
    CURRENCY = "currency"
