from collections.abc import Callable
from decimal import Decimal

from sqlalchemy import ColumnElement, Select, func
from sqlalchemy.orm.attributes import QueryableAttribute

from zeni.database.models import ZeniBase
from zeni.utils.filters import HAS, NOT, Entry, preprocess_string_values

type Predicate = Callable[[QueryableAttribute], ColumnElement[bool]]
"""A callable that receives a column and returns a SQLAlchemy boolean expression."""

type DatabaseFilterT = list[Entry] | tuple[Entry, Entry] | Entry | Predicate
"""Possible database filters."""


class DatabaseFilters:
    """A collection of common filtering functions for SQLAlchemy queries."""

    @staticmethod
    def equals(column: QueryableAttribute, value: Entry) -> ColumnElement[bool]:
        if isinstance(value, str):
            return func.lower(column) == func.lower(value)
        return column == value

    @staticmethod
    def between(
        column: QueryableAttribute, values: tuple[Entry, Entry]
    ) -> ColumnElement[bool]:
        return column.between(*values)

    @staticmethod
    def is_in(column: QueryableAttribute, values: list[Entry]) -> ColumnElement[bool]:
        return column.in_(values)

    @staticmethod
    def has_substring(
        column: QueryableAttribute, value: str, negate: bool = False
    ) -> ColumnElement[bool]:
        clause = column.ilike(f"%{value}%")
        return ~clause if negate else clause

    @staticmethod
    def apply_predicate(
        column: QueryableAttribute, predicate: Predicate
    ) -> ColumnElement[bool]:
        return predicate(column)


@preprocess_string_values
def filter_query(
    statement: Select, model: type[ZeniBase], **kwargs: DatabaseFilterT
) -> Select:
    """Apply filters to a SQLAlchemy select statement.

    Mirrors the pattern-matching approach of filter_dataframe, but produces
    chained .where() clauses instead of filtered DataFrames.

    Parameters
    ----------
    stmt : Select
        A SQLAlchemy select statement.
    model : type[ZeniBase]
        The ORM model to resolve column names against.

    Returns
    -------
    Select
        The filtered select statement.
    """
    for col_name, setting in kwargs.items():
        column: QueryableAttribute = getattr(model, col_name)
        match setting:
            case tuple():
                statement = statement.where(DatabaseFilters.between(column, setting))
            case list():
                statement = statement.where(DatabaseFilters.is_in(column, setting))
            case int() | float() | Decimal():
                statement = statement.where(DatabaseFilters.equals(column, setting))
            case str():
                if setting == "":
                    statement = statement.where(DatabaseFilters.equals(column, setting))
                elif (head := setting[0]) in [HAS, NOT]:
                    statement = statement.where(
                        DatabaseFilters.has_substring(column, setting[1:], head == NOT)
                    )
                else:
                    statement = statement.where(DatabaseFilters.equals(column, setting))
            case _ if callable(setting):
                statement = statement.where(
                    DatabaseFilters.apply_predicate(column, setting)
                )
            case _:
                raise ValueError(
                    f"Invalid filter setting: {setting!r} has type {type(setting)}."
                )
    return statement
