from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import TypeAlias

from sqlalchemy import ColumnElement, Select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm.attributes import QueryableAttribute

from zeni.utils.filters import HAS, NOT, Entry

Predicate: TypeAlias = Callable[[QueryableAttribute], ColumnElement[bool]]
"""A callable that receives a column and returns a SQLAlchemy boolean expression."""

DatabaseFilterT: TypeAlias = list[Entry] | tuple[Entry, Entry] | Entry | Predicate
"""Possible database filters."""


class DatabaseFilters:
    """A collection of common filtering functions for SQLAlchemy queries."""

    @staticmethod
    def equals(column: QueryableAttribute, value: Entry) -> ColumnElement[bool]:
        return column == value

    @staticmethod
    def approx_equals(
        column: QueryableAttribute, value: Decimal | float, tolerance: float = 0.01
    ) -> ColumnElement[bool]:
        v = float(value)
        return column.between(v - tolerance, v + tolerance)

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


def filter_query(
    statement: Select, model: type[DeclarativeBase], **kwargs: DatabaseFilterT
) -> Select:
    """Apply filters to a SQLAlchemy select statement.

    Mirrors the pattern-matching approach of filter_dataframe, but produces
    chained .where() clauses instead of filtered DataFrames.

    Parameters
    ----------
    stmt : Select
        A SQLAlchemy select statement.
    model : type[DeclarativeBase]
        The ORM model to resolve column names against.

    Returns
    -------
    Select
        The filtered select statement.
    """
    for col_name, setting in kwargs.items():
        column = getattr(model, col_name)
        match setting:
            case tuple():
                statement = statement.where(DatabaseFilters.between(column, setting))
            case list():
                statement = statement.where(DatabaseFilters.is_in(column, setting))
            case float() | Decimal():
                statement = statement.where(
                    DatabaseFilters.approx_equals(column, setting)
                )
            case int():
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


def get_project_root() -> Path:
    """Get the project root directory (where .git or pyproject.toml exists)."""
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


DEFAULT_PATHWAY: Path = get_project_root() / ".zeni"


def sql_directory(folder_path: str, name: str) -> str:
    return f"sqlite:///{folder_path}/{name}.db"


def list_databases(folder_path: str = DEFAULT_PATHWAY) -> list[str]:
    """List all database names in the specified folder.

    Args:
        folder_path: Path to folder containing databases (default: .zeni/)

    Returns:
        List of database names (without .db extension)
    """
    db_path = Path(folder_path)
    if not db_path.exists():
        return []

    return [db.stem for db in db_path.glob("*.db")]
