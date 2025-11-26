"""SQLAlchemy models for the Zeni database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from zeni.basic_types import Account


class Base(DeclarativeBase):
    """Base class for all database models."""


# Association table for many-to-many relationship between transactions and imports
transaction_imports = Table(
    "transaction_imports",
    Base.metadata,
    Column(
        "transaction_id", String(36), ForeignKey("transactions.id"), primary_key=True
    ),
    Column(
        "statement_id",
        String(36),
        ForeignKey("imported_statements.id"),
        primary_key=True,
    ),
)


class Transaction(Base):
    """Represents a single transaction."""

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), unique=True, primary_key=True, default=lambda: str(uuid.uuid4())
    )

    bank: Mapped[str] = mapped_column(String(10), nullable=False)
    account: Mapped[Account] = mapped_column(Enum(Account), nullable=False)

    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    time: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(), nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(tz=UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.now(tz=UTC),
        onupdate=datetime.now(tz=UTC),
    )

    import_links: Mapped[list[ImportedStatements]] = relationship(
        secondary=transaction_imports, back_populates="transactions"
    )

    # Unique constraint: prevent duplicate transactions
    # Use balance as it's unique for each transaction in statement
    __table_args__ = (
        UniqueConstraint("bank", "date", "name", "balance", name="uq_transaction"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, bank={self.bank}, "
            f"date={self.date.date()}, name={self.name!r}, amount={self.amount})>"
        )

    @classmethod
    def from_standardized(
        cls, bank_name: str, account_type: Account, data: pd.Series
    ) -> Transaction:
        return Transaction(
            bank=bank_name,
            account=account_type,
            date=data["date"],
            time=data["time"],
            name=data["name"],
            category=data["category"],
            amount=Decimal(str(data["amount"])),
            currency=data["currency"],
            notes=data["notes"] if pd.notna(data.get("notes")) else None,
            balance=Decimal(str(data["balance"])),
        )


class ImportedStatements(Base):
    """Statement importer class."""

    __tablename__ = "imported_statements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Import metadata
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    import_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(tz=UTC), index=True
    )
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    transactions: Mapped[list[Transaction]] = relationship(
        secondary=transaction_imports, back_populates="import_links"
    )

    def __repr__(self) -> str:
        return (
            f"<StatementImport(id={self.id}, bank={self.bank_name}, "
            f"timestamp={self.import_timestamp}, new={self.new_count}, "
            f"duplicates={self.duplicate_count})>"
        )
