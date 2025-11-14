"""SQLAlchemy models for the Zeni database."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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
        "import_batch_id", String(36), ForeignKey("import_batches.id"), primary_key=True
    ),
)


class Transaction(Base):
    """Represents a single financial transaction."""

    __tablename__ = "transactions"

    # Primary key - internal UUID
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Bank identification
    bank_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    account_identifier: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Transaction details
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=19, scale=4), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Metadata
    is_manually_edited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    import_batches: Mapped[list[ImportBatch]] = relationship(
        secondary=transaction_imports, back_populates="transactions"
    )

    # Unique constraint: combination of bank_name and bank_transaction_id must be unique
    __table_args__ = (
        UniqueConstraint(
            "bank_name",
            "bank_transaction_id",
            name="uq_bank_transaction",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, bank={self.bank_name}, "
            f"date={self.date.date()}, name={self.name!r}, amount={self.amount})>"
        )


class ImportBatch(Base):
    """Represents a batch import of transactions."""

    __tablename__ = "import_batches"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Import metadata
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    import_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    source_file: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Statistics
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    transactions: Mapped[list[Transaction]] = relationship(
        secondary=transaction_imports, back_populates="import_batches"
    )

    def __repr__(self) -> str:
        return (
            f"<ImportBatch(id={self.id}, bank={self.bank_name}, "
            f"timestamp={self.import_timestamp}, new={self.new_count}, "
            f"duplicates={self.duplicate_count})>"
        )
