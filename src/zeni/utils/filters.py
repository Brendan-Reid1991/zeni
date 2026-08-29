"""Quick access filtering for dataframes."""

from __future__ import annotations

import operator
import re
from ast import literal_eval
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from functools import wraps

import numpy as np
import pandas as pd
from numpy import typing as npt

from zeni.utils.input_resolution import resolve


def map_column_name(
    function: Callable[[pd.DataFrame, str, FilterT], pd.DataFrame],
) -> Callable[[pd.DataFrame, str, FilterT], pd.DataFrame]:
    """A decorator that maps a function argument to a column in a dataframe.

    Can only be applied to a function where the first argument is a pandas dataframe.
    """

    @wraps(function)
    def inner(df: pd.DataFrame, column_name: str, settings: FilterT) -> pd.DataFrame:
        best_match = resolve(column_name, tuple(df.columns))
        return function(df, best_match, settings)

    return inner


type Entry = Decimal | str | float | datetime | bool
"""Generic dataframe entry."""

type BooleanArray = pd.Series | npt.NDArray[np.bool] | list[bool] | tuple[bool, ...]
"""An array of booleans."""


class DataframeFilters:
    """A collection of common filtering functions for dataframes."""

    @staticmethod
    def equals(df: pd.DataFrame, column: str, value: Entry) -> pd.DataFrame:
        """Equality checking for dataframe entries.

        Returns a sub-dataframe that satisfies df[column] == value.

        Parameters
        ----------
        df: pd.DataFrame
        column: str
        value: Entry

        Returns
        -------
        pd.DataFrame
        """
        return df[df[column] == value]

    @staticmethod
    def approx_equals(
        df: pd.DataFrame, column: str, value: Decimal | float
    ) -> pd.DataFrame:
        """Approximate equality checking for dataframe float values.

        Returns a sub-dataframe that satisfies np.isclose(df[column], value).

        Parameters
        ----------
        df: pd.DataFrame
        column: str
        value: float

        Returns
        -------
        pd.DataFrame
        """
        return df[np.isclose(df[column], float(value))]

    @staticmethod
    def has_substring(
        df: pd.DataFrame, column: str, value: str, negate: bool = False
    ) -> pd.DataFrame:
        """Substring detection/exclusion for dataframe entries.

        Returns a sub-dataframe where rows either have, or do not have, a specified
        substring.

        Parameters
        ----------
        df: pd.DataFrame
        column: str
        value: str
        negate: bool
            Whether or not to negate substring detection. If True, moves to substring
            _exclusion_.

        Returns
        -------
        pd.DataFrame
        """

        mask = (
            df[column]
            .astype("string")
            .str.contains(value, case=False, regex=False, na=False)
        )
        return df[~mask if negate else mask]

    @staticmethod
    def is_in(df: pd.DataFrame, column: str, values: list[Entry]) -> pd.DataFrame:
        """Membership check for dataframe entries.

        Returns a sub-dataframe where rows have elements in the specified list.

        Parameters
        ----------
        df: pd.DataFrame
        column: str
        values: list[Entry]
            Membership list.

        Returns
        -------
        pd.DataFrame
        """
        return df[df[column].isin(values)]

    @staticmethod
    def between(
        df: pd.DataFrame, column: str, values: tuple[Entry, Entry]
    ) -> pd.DataFrame:
        """Check if a value in a dataframe falls within a range.

        Returns a sub-dataframe where rows have elements within the specified range.

        Parameters
        ----------
        df: pd.DataFrame
        column: str
        values: tuple[Number, Number]
            Value range; bounds inclusive.

        Returns
        -------
        pd.DataFrame
        """
        return df[df[column].between(*values, inclusive="both")]

    @staticmethod
    def apply_predicate(
        df: pd.DataFrame,
        column: str,
        predicate: Callable[[Entry], bool],
    ) -> pd.DataFrame:
        """Apply a bespoke function to a dataframe.

        Function must act on a pd.Series and return a boolean array of the same length.

        Returns sub-dataframe where rows satisfy the predicate.

        Parameters
        ----------
        df : pd.DataFrame
        column : str
        predicate : Callable[ [Entry], bool]
            A function to apply to each entry in the column.

        Returns
        -------
        pd.DataFrame
        """
        return df[df[column].apply(predicate)]


type FilterT = (
    list[Entry] | tuple[Entry, Entry] | Entry | Callable[[pd.Series], BooleanArray]
)
"""Possible dataframe filters."""

HAS = "^"
"""Substring inclusion."""

NOT = "!"
"""Substring exclusion."""


def preprocess_string_values[P, R](function: Callable[[P], R]) -> Callable[[P], R]:
    """Preprocess string inputs into predicates, if possible."""

    def _inner(*args: P.args, **kwargs: P.kwargs) -> R:
        for field, setting in kwargs.items():
            if isinstance(setting, str):
                try:
                    pred = convert_string_to_predicate(setting)
                    kwargs |= {field: pred}
                except ValueError as _:
                    pass
        return function(*args, **kwargs)

    return _inner


@map_column_name
def filter_rows(dataframe: pd.DataFrame, column: str, settings: FilterT) -> pd.DataFrame:
    """Filter rows of a dataframe by supplying a column name and setting.

    Parameters
    ----------
    dataframe : pd.DataFrame
        Dataframe to filter.
    column : str
        The column to filter on.
    settings : FilterT
        The setting to look for. Could be an entry value, a list of entry values, etc.

    Returns
    -------
    pd.DataFrame
        A dataframe satisfying the setting.

    Raises
    ------
    ValueError
        If a function call (via apply_predicate) cannot be parsed.
    ValueError
        If an unrecognised setting is passed.
    """
    match settings:
        case tuple():
            return DataframeFilters.between(dataframe, column, settings)
        case list():
            return DataframeFilters.is_in(dataframe, column, settings)
        case float() | Decimal():
            return DataframeFilters.approx_equals(dataframe, column, settings)
        case int():
            return DataframeFilters.equals(dataframe, column, settings)
        case str():
            if settings == "":
                return DataframeFilters.equals(dataframe, column, settings)
            if (head := settings[0]) in [HAS, NOT]:
                return DataframeFilters.has_substring(
                    dataframe, column, settings[1:], head == NOT
                )
            return DataframeFilters.equals(dataframe, column, settings)
        case _ if callable(settings):
            try:
                return DataframeFilters.apply_predicate(dataframe, column, settings)
            except TypeError as exc:
                raise ValueError(
                    f"Can't parse this function call: {settings!r}"
                ) from exc
        case _:
            raise ValueError(
                f"Invalid filter settings: {settings!r} has type {type(settings)}."
            )


@preprocess_string_values
def filter_dataframe(dataframe: pd.DataFrame, **kwargs: FilterT) -> pd.DataFrame:
    """Access point for multi-setting filtering of dataframes.

    Settings can be applied as kwargs where the argument name is the column name, and the
    value is the setting..

    Parameters
    ----------
    dataframe : pd.DataFrame
        Dataframe to filter.

    Returns
    -------
    pd.DataFrame
    """
    df = dataframe
    for column, setting in kwargs.items():
        df = filter_rows(df, column, setting)

    return df


OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}

COMPARATORS = re.compile(r"\s*(>=|<=|==|!=|>|<)\s*(.+?)\s*")
WITHIN_RANGE = re.compile(r"\s*([+-]?\d+(?:\.\d+)?)\((\d*\.?\d+)\)\s*")


def convert_string_to_predicate(input_string: str) -> Callable[..., BooleanArray]:
    """Convert a string to a predicate. This function allows syntactic sugar,
    such as `x = "<=10"` instead of `x = lambda x: x <= 10`.
    """
    if (range_match := WITHIN_RANGE.fullmatch(input_string)) is not None:
        anchor, plus_minus = range_match.groups()
        return lambda candidate: abs(literal_eval(anchor) - candidate) <= literal_eval(
            plus_minus
        )
    match = COMPARATORS.fullmatch(input_string)
    if match is None:
        raise ValueError(f"Invalid string to convert to a predicate: {input_string}")
    op, value = match.groups()
    return lambda candidate: OPERATORS[op](candidate, literal_eval(value))
