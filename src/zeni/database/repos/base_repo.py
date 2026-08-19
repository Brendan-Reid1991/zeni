from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache

import pandas as pd
from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from zeni.basic_types import TransactionColumns
from zeni.database.models import Model
from zeni.utils.filters import Entry
from zeni.utils.input_resolution import coerce_date, coerce_kwargs

from .utils import filter_query


@lru_cache
def _model_columns(model: type[Model]) -> tuple[str, ...]:
    """Cached private function to return the columns of a table."""
    return tuple(inspect(model).columns.keys())


def columns(repo: Repository) -> tuple[str, ...]:
    """Callable for passing into a coerce_kwargs decorator."""
    return _model_columns(repo.table)


def values_of(field: str) -> Callable[[Repository], tuple[str, ...]]:
    """Returns a callable that inspects the existing elements of `field`
    in the repository's `table`."""

    def _valid_values(repo: Repository) -> tuple[str, ...]:
        return tuple(repo.elements_of(field))

    return _valid_values


class Repository[T: Model]:
    """A basic repository for handling table data.

    Parameters
    ----------
    session: Session
        The sqlalchemy session context.
    table: Model
        Which table this repository is for.
    """

    def __init__(self, session: Session, table: type[T]):
        self.session = session
        self.table = table

    @property
    def count(self) -> int:
        """The number of entries in this table."""
        if (
            num_entries := self.session.scalar(
                select(func.count()).select_from(self.table)
            )
        ) is not None:
            return num_entries
        return 0

    def as_df(self) -> pd.DataFrame:
        """Return the entire table as a dataframe."""
        return pd.read_sql(select(self.table).order_by(self.table.id), self.session.bind)

    def elements_of(self, field: str) -> Sequence[Entry]:
        """Return the elements of the given field."""
        return self.session.scalars(select(getattr(self.table, field))).all()

    @coerce_kwargs(columns)
    @coerce_date(TransactionColumns.DATE)
    def filter(self, **filters: Entry) -> Sequence[T]:
        """Apply filters to the table and return those objects that satisfy the query.

        Returns
        -------
        Sequence[T]
            A sequence of objects in the table that satisfy all kwarg conditions.

        Raises
        ------
        ValueError
            If no entries satisfy the conditions.
        """
        statement = filter_query(select(self.table), self.table, **filters)
        if entries := self.session.scalars(statement).all():
            return entries

        _as_list = "\n\t- ".join(f"{key} = {value}" for key, value in filters.items())
        raise ValueError(
            f"No '{self.table.__name__}' entries satisfy the following conditions:"
            "\n\t- " + _as_list
        )

    def from_id(self, id: str) -> T:
        """Return the object with the given `id`."""
        return self.filter(id=id)[0]
