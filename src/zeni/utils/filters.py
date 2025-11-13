"""Quick access filtering for dataframes."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from numbers import Number
from functools import wraps
from typing import TypeAlias

import numpy as np
import pandas as pd
from numpy import typing as npt

from zeni.utils.fuzzy_matcher import fuzzy_string_matcher


def map_column_name(function: Callable[[pd.DataFrame, str, FilterT], pd.DataFrame]):
    """A decorator that maps a function argument to a column in a dataframe.

    Can only be applied to a function where the first argument is a pandas dataframe.
    """

    @wraps(function)
    def inner(df: pd.DataFrame, column_name: str, settings: FilterT):
        best_match = fuzzy_string_matcher(column_name, tuple(df.columns))
        return function(df, best_match, settings)

    return inner


Entry: TypeAlias = Decimal | str | float
"""Generic dataframe entry."""

BooleanArray: TypeAlias = (
    pd.Series | npt.NDArray[np.bool] | list[bool] | tuple[bool, ...]
)
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
    def approx_equals(df: pd.DataFrame, column: str, value: float) -> pd.DataFrame:
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
        return df[np.isclose(df[column], value)]

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
        df: pd.DataFrame, column: str, values: tuple[Number, Number]
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
        predicate: Callable[[pd.Series], BooleanArray],
    ) -> pd.DataFrame:
        """Apply a bespoke function to a dataframe.

        Function must act on a pd.Series and return a boolean array of the same length.

        Returns sub-dataframe where rows satisfy the predicate.

        Parameters
        ----------
        df : pd.DataFrame
        column : str
        predicate : Callable[ [pd.Series], BooleanArray]
            A bespoke function to apply. Must act on a pd.Series and return a boolean
            array.

        Returns
        -------
        pd.DataFrame

        Raises
        ------
        ValueError
            If the function does not return a boolean, or the returned array is the
            wrong length.
        """
        col = df[column]
        mask = predicate(col)
        if isinstance(mask, pd.Series):
            mask = mask.reindex(df.index, fill_value=False)
        else:
            mask = pd.Series(mask, index=col.index, dtype=bool)
        if mask.dtype != bool or len(mask) != len(df):
            raise ValueError(
                "Predicate must produce a boolean mask aligned with the dataframe."
            )
        return df[mask]


FilterT: TypeAlias = (
    list[Entry]
    | tuple[Entry, Entry]
    | Entry
    | Callable[
        [pd.Series],
        BooleanArray
    ]
)
"""Possible dataframe filters."""

HAS = "^"
"""Substring inclusion."""

NOT = "!"
"""Substring exclusion."""


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
        case Callable():
            try:
                return DataframeFilters.apply_predicate(dataframe, column, settings)
            except ValueError as exc:
                raise ValueError(
                    f"Can't parse this function call: {settings!r}"
                ) from exc
        case _:
            raise ValueError(
                f"Invalid filters settings: {settings!r} has type {type(settings)}."
            )


def filter_dataframe(dataframe: pd.DataFrame, **kwargs) -> pd.DataFrame:
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