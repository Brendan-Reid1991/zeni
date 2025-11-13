"""This module defines the Bank protocol, as well as standardization procedures."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

import pandas as pd

from zeni.basic_types import Payment, StandardColumns
from zeni.utils import filter_dataframe
from zeni.utils.fuzzy_matcher import NoMatchingStringsError, fuzzy_string_matcher

PREFERRED_ORDERING: list[str] = [
    StandardColumns.DATE,
    StandardColumns.NAME,
    StandardColumns.CATEGORY,
    StandardColumns.AMOUNT,
    StandardColumns.CURRENCY,
    StandardColumns.NOTES,
    StandardColumns.BALANCE,
]
"""The current preferred ordering of standard columns."""


@runtime_checkable
class Bank(Protocol):
    """This protocol defines the interface for all implemented institutions.

    It requires no initialization, only classmethods column_map and category_map to
    be defined. THese define the mapping from Bank-specific columns and categories
    to Zenei-defined standards.

    Optionally, pre- and post-processing steps can be defined to ensure the input
    dataframe is output in the correct format.

    """

    pre_processing_steps: ClassVar[Callable[[pd.DataFrame], pd.DataFrame]] = lambda x: x
    post_processing_steps: ClassVar[
        Iterable[Callable[[pd.DataFrame], pd.DataFrame]]
    ] = ()

    @classmethod
    def column_map(cls) -> dict[str, StandardColumns]:
        """Map bank-specific columns to Zeni standard columns."""

    @classmethod
    def category_map(cls) -> dict[str, Payment]:
        """Map the bank-specific categories to Zeni standard categories."""


_BANK_REGISTRY: dict[str, type[Bank]] = {}
"""The registry records all implemented institutions. To be registered, they
must be imported into the zeni/bank/__init__.py"""


def register_bank(cls: type[Bank]) -> type[Bank]:
    """Decorator to register a bank implementation."""
    _BANK_REGISTRY[cls.__name__] = cls
    return cls


def bank_directory(name: str) -> type[Bank]:
    """Return the Bank class for the input bank name.

    Supports fuzzy string matching.
    """
    registered = tuple(_BANK_REGISTRY.keys())
    try:
        return _BANK_REGISTRY[fuzzy_string_matcher(name, registered)]
    except NoMatchingStringsError as exc:
        raise KeyError(
            f"Invalid bank name: '{name}'. Supported banks are: {registered}"
        ) from exc


def standardize(bank_cls: type[Bank], statement: pd.DataFrame) -> pd.DataFrame:
    """Standardize a bank statement using the provided bank class.

    Parameters
    ----------
    bank_cls: type[Bank]
        The implemented Bank class for the institution the statement is from.
    statement: pd.DataFrame
        The dataframe file for the statement.

    Returns
    -------
    pd.DataFrame
        A standardized dataframe.
    """
    statement = bank_cls.pre_processing_steps(statement)

    statement = standardize_dtypes(
        statement.rename(columns=bank_cls.column_map())[PREFERRED_ORDERING]
    )

    for old_category, new_category in bank_cls.category_map().items():
        statement.loc[
            filter_dataframe(statement, category="^" + old_category).index,
            StandardColumns.CATEGORY,
        ] = new_category

    for fn in bank_cls.post_processing_steps:
        statement = fn(statement)

    return statement


def standardize_dtypes(
    df: pd.DataFrame,
    use_decimal: bool = False,
) -> pd.DataFrame:
    """
    Standardize DataFrame column types and index by date.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame
    use_decimal : bool, default False
        If True, convert amount columns to Decimal instead of float

    Returns
    -------
    pd.DataFrame
        DataFrame with standardized dtypes.
    """
    df = df.copy()

    date_column = StandardColumns.DATE

    df[date_column] = pd.to_datetime(df[date_column], format="mixed", dayfirst=True)

    amount_columns = [
        col
        for col in df.columns
        if any(
            keyword in col.lower()
            for keyword in [StandardColumns.AMOUNT, StandardColumns.BALANCE]
        )
    ]

    for col in amount_columns:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace("£", "", regex=False)
                df[col] = df[col].str.replace("$", "", regex=False)
                df[col] = df[col].str.replace(",", "", regex=False)

            if use_decimal:
                df[col] = df[col].apply(
                    lambda x: Decimal(str(x)) if pd.notna(x) else None
                )
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype("string")

    return df
