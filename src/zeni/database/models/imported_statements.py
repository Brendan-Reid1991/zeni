from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import DateTime, Integer, String

from .association_tables import transaction_imports
from .base_model import ZeniBase

if TYPE_CHECKING:
    from .transactions import Transaction


class ImportedStatements(ZeniBase):
    """Statement importer class."""

    __tablename__ = "imported_statements"

    # Columns
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    import_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(tz=UTC), index=True
    )
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    transactions: Mapped[list[Transaction]] = relationship(
        secondary=transaction_imports, back_populates="import_links"
    )

    def __repr__(self) -> str:
        return (
            f"<StatementImport(id={self.id}, bank={self.bank_name}, "
            f"timestamp={self.import_timestamp}, new={self.new_count}, "
            f"duplicates={self.duplicate_count})>"
        )
