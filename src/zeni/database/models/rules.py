from decimal import Decimal
from enum import StrEnum, auto
from typing import Any, TypedDict

from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON, Integer, String

from .base_model import ZeniBase


class Filter(StrEnum):
    EQ = auto()
    IN = auto()
    BETWEEN = auto()
    APPROX_EQ = auto()
    CONTAINS = auto()
    NOT_CONTAINS = auto()


class Condition(TypedDict):
    apply_to: str
    operation: Filter
    value: Any


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

    # @validates("conditions_data")
    # def validate_conditions_data(self, key, value):
    #     return [self._normalize_condition(c) for c in value]

    # @validates("actions_data")
    # def validate_actions_data(self, key, value):
    #     return [self._normalize_action(a) for a in value]

    # def _normalize_condition(self, condition: ConditionDict) -> ConditionDict:
    #     return {
    #         "apply_to": str(condition["apply_to"]),
    #         "operation": str(Filter(condition["operation"])),
    #         "value": condition["value"],
    #     }

    # def _normalize_action(self, action: ActionDict) -> ActionDict:
    #     return {
    #         "apply_to": str(action["apply_to"]),
    #         "operation": str(Modifier(action["operation"])),
    #         "value": action["value"],
    #     }
