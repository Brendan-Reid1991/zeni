from __future__ import annotations

from decimal import Decimal
from enum import StrEnum, auto
from typing import TypedDict

from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON, Integer, String

from zeni.utils.filters import Entry

from .base_model import ZeniBase


class Filter(StrEnum):
    EQ = auto()
    APPROX_EQ = auto()
    IN = auto()
    BETWEEN = auto()
    CONTAINS = auto()
    NOT_CONTAINS = auto()
    GT = auto()
    GTE = auto()
    LT = auto()
    LTE = auto()


class Condition(TypedDict):
    apply_to: str
    operation: Filter
    value: Entry | list[Entry] | tuple[Entry, Entry]


class Modifier(StrEnum):
    SET = auto()
    APPEND = auto()
    PREPEND = auto()
    INCREMENT = auto()
    DECREMENT = auto()


class Action(TypedDict):
    apply_to: str
    operation: Modifier
    value: Decimal | str


class Rule(ZeniBase):
    """Entries for the `Rules` table.

    Rules are described by a list of conditions and a list of actions.

    Conditions are stored as lists of tuples
    """

    __tablename__ = "rules"

    # Columns
    name: Mapped[str] = mapped_column(String(36), nullable=True)
    conditions: Mapped[list[Condition]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=False, default=list
    )
    actions: Mapped[list[Action]] = mapped_column(
        MutableList.as_mutable(JSON), nullable=False, default=list
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Rule({self.name or self.id}, {self.conditions} -> {self.category})>"
