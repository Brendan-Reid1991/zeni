"""SQLAlchemy models for the Zeni database."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd
import sqlalchemy.sql.sqltypes as sqlt
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_model import ZeniBase

if TYPE_CHECKING:
    from .accounts import Account
    from .imported_statements import ImportedStatement


class Transaction(ZeniBase):
    """Represents a single transaction."""

    __tablename__ = "transactions"

    # Columns
    date: Mapped[date] = mapped_column(sqlt.DateTime, nullable=False, index=True)
    time: Mapped[str] = mapped_column(sqlt.String(8), nullable=False)
    name: Mapped[str] = mapped_column(sqlt.String(200), nullable=False)
    category: Mapped[str] = mapped_column(sqlt.String(50), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(sqlt.Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(sqlt.String(3), nullable=False)
    notes: Mapped[str | None] = mapped_column(sqlt.String(2000), nullable=True)
    balance: Mapped[Decimal] = mapped_column(sqlt.Numeric(12, 2), nullable=False)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        sqlt.DateTime, nullable=False, default=lambda: datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        sqlt.DateTime,
        nullable=False,
        default=lambda: datetime.now(tz=UTC),
        onupdate=lambda: datetime.now(tz=UTC),
    )

    # Foreign Keys
    account_name: Mapped[str] = mapped_column(
        sqlt.String(100), ForeignKey("accounts.name"), nullable=False, index=True
    )
    imported_from: Mapped[str | None] = mapped_column(
        sqlt.String(36),
        ForeignKey("imported_statements.id"),
        nullable=True,
        index=True,
    )

    # Relationships
    account: Mapped[Account] = relationship(
        back_populates="transactions", foreign_keys=[account_name]
    )

    imported_statement: Mapped[ImportedStatement | None] = relationship(
        back_populates="transactions"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "account_name",
            "date",
            "name",
            "balance",
            name="unique_transaction",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, account={self.account_name}, "
            f"date={self.date.date()}, name={self.name!r}, amount={self.amount})>"
        )

    @classmethod
    def from_standardized(
        cls, account: str, data: pd.Series, imported_from: str | None = None
    ) -> Transaction:
        """Generate a Transaction from a row of a standardized statement."""
        name = "Unknown" if pd.isna(_name := data["name"]) else str(_name)
        category = "UNCATEGORISED" if pd.isna(_cat := data["category"]) else str(_cat)
        return Transaction(
            account_name=account,
            date=data["date"],
            time=data["time"],
            name=name,
            category=category,
            amount=Decimal(str(data["amount"])).quantize(Decimal("0.01")),
            currency=data["currency"],
            notes=data["notes"] if pd.notna(data.get("notes")) else None,
            balance=Decimal(str(data["balance"])).quantize(Decimal("0.01")),
            imported_from=imported_from,
        )
