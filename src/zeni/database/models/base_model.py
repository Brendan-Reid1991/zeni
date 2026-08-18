"""SQLAlchemy models for the Zeni database."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from zeni.utils.filters import Entry


class ZeniBase(DeclarativeBase):
    """Base class for all Zeni database models.

    Defines the ID column for all subsequent tables.
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(tz=UTC)
    )

    def to_dict(self) -> dict[str, Entry]:
        """Convert this tmodel to a ditionary."""
        return {
            column.key: getattr(self, column.key)
            for column in self.__mapper__.column_attrs
        }
