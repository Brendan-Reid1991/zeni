from __future__ import annotations
from dataclasses import dataclass
from datetime import date

@dataclass(slots=True, frozen=True)
class Transaction:
    date: date
    description: str
    amount: float
    account: str
    currency: str | None = None
    category: str | None = None
