from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    INTERNAL = "internal"


class Transaction(str, Enum): ...


class Outgoing(Transaction):
    RENT = "rent"
    BILL = "bill"
    SUBSCRIPTION = "subscription"
    CASH_WITHDRAWAL = "cash_withdrawal"
    TRANSFER_OUT_EXTERNAL = "transfer_out_external"
    FEE = "fee"
    LOAN_PAYMENT = "loan_payment"
    CREDIT_CARD = "credit_card"


class Incoming(Transaction):
    SALARY = "salary"
    INTEREST = "interest"
    REFUND = "refund"
    TRANSFER_IN_EXTERNAL = "transfer_in_external"
    CASH_DEPOSIT = "cash_deposit"


class Internal(Transaction):
    TRANSFER = "transfer"
    ROUNDUP = "roundup"


@dataclass(slots=True, frozen=True)
class Transaction:
    date: date
    description: str
    amount: float  # outflow negative, inflow positive
    account: str
    currency: Optional[str] = None

    # Structural classification
    direction: Optional[Direction] = None
    kind: Optional[Kind] = None
    method: Optional[Method] = None

    # For transfers/refunds/linking related legs
    counterparty: Optional[str] = None  # merchant/employer/bank name
    related_id: Optional[str] = None  # to link refund ↔ original, or transfer legs
    transfer_group_id: Optional[str] = (
        None  # stable id for both legs of an internal transfer
    )

    # User-facing budgeting label (your existing pipeline fills this)
    category: Optional[str] = None

    # State
    is_pending: bool = False
    notes: Optional[str] = None
