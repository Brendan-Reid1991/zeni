from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import DateTime, String

from .base_model import ZeniBase

if TYPE_CHECKING:
    from .transactions import Transaction


class ImportedStatement(ZeniBase):
    """Statement importer class."""

    __tablename__ = "imported_statements"

    # Foreign Keys
    account: Mapped[str] = mapped_column(
        String(100), ForeignKey("accounts.name"), nullable=False, index=True
    )

    # Columns
    import_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(tz=UTC), index=True
    )
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)

    # Relationships
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="imported_statement"
    )

    def __repr__(self) -> str:
        return (
            f"<ImportedStatement(account={self.account}, "
            f"timestamp={self.import_timestamp})>"
        )
