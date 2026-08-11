from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zeni.basic_types import AccountType

from .base_model import ZeniBase

if TYPE_CHECKING:
    from .transactions import Transaction


class Account(ZeniBase):
    """Represents a user account at a financial institution."""

    __tablename__ = "accounts"

    # Columns
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    bank: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account(name={self.name}, bank={self.bank}, type={self.account_type})>"
