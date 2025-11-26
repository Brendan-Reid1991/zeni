"""This module defines the Bank protocol, as well as standardization procedures."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import (
    ClassVar,
    Protocol,
    TypeAlias,
    runtime_checkable,
)

import pandas as pd

from zeni.basic_types import Payment, StandardColumns
from zeni.utils import filter_dataframe
from zeni.utils.fuzzy_matcher import NoMatchingStringsError, fuzzy_string_matcher

PREFERRED_ORDERING: list[str] = [
    StandardColumns.DATE,
    StandardColumns.TIME,
    StandardColumns.NAME,
    StandardColumns.CATEGORY,
    StandardColumns.AMOUNT,
    StandardColumns.CURRENCY,
    StandardColumns.NOTES,
    StandardColumns.BALANCE,
]
"""The current preferred ordering of standard columns."""

DataframeProcessor: TypeAlias = Callable[[pd.DataFrame], pd.DataFrame]
ProcessingStep: TypeAlias = list[tuple[int, DataframeProcessor]]


@runtime_checkable
class Bank(Protocol):
    """This protocol defines the interface for all implemented institutions.

    It requires no initialization, only classmethods column_map and category_map to
    be defined. THese define the mapping from Bank-specific columns and categories
    to Zeni-defined standards.

    Optionally, pre- and post-processing steps can be defined to ensure the input
    dataframe is output in the correct format.

    """

    @staticmethod
    def load(filepath: Path | str) -> pd.DataFrame:
        return pd.read_csv(filepath)

    @classmethod
    def column_map(cls) -> dict[str, StandardColumns]:
        """Map bank-specific columns to Zeni standard columns."""

    @classmethod
    def category_map(cls) -> dict[str, Payment]:
        """Map the bank-specific categories to Zeni standard categories."""

    pre_processing_steps: ClassVar[ProcessingStep] = []
    post_processing_steps: ClassVar[ProcessingStep] = []

    def __init_subclass__(cls) -> None:
        """Initialize processing step lists for each subclass."""
        cls.pre_processing_steps = []
        cls.post_processing_steps = []

    @classmethod
    def pre_process(
        cls, order: int = 0
    ) -> Callable[[DataframeProcessor], DataframeProcessor]:
        """Decorator to register pre-processing steps with optional ordering."""

        def decorator(fn: DataframeProcessor) -> DataframeProcessor:
            cls.pre_processing_steps.append((order, fn))
            # cls.pre_processing_steps.sort(key=lambda x: x[0])
            return fn

        return decorator

    @classmethod
    def post_process(
        cls, order: int = 0
    ) -> Callable[[DataframeProcessor], DataframeProcessor]:
        """Decorator to register post-processing steps with optional ordering."""

        def decorator(fn: DataframeProcessor) -> DataframeProcessor:
            cls.post_processing_steps.append((order, fn))
            return fn

        return decorator


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


def standardize(bank: str, filepath: Path | str) -> pd.DataFrame:
    """Standardize a bank statement using the provided bank name.

    Parameters
    ----------
    bank: str
        The name of the bank the statement is from.
    filepath: Path | str
        The pathway to the statement.

    Returns
    -------
    pd.DataFrame
        A standardized dataframe.
    """
    bank_cls = bank_directory(bank)
    statement = bank_cls.load(filepath)

    for _, _pre in sorted(bank_cls.pre_processing_steps, key=lambda x: x[0]):
        statement = _pre(statement)
    if StandardColumns.NOTES not in bank_cls.column_map().values():
        statement[StandardColumns.NOTES] = pd.Series([], dtype="str")
    statement = standardize_dtypes(
        statement.rename(columns=bank_cls.column_map())[PREFERRED_ORDERING]
    )

    for old_category, new_category in bank_cls.category_map().items():
        statement.loc[
            filter_dataframe(statement, category="^" + old_category).index,
            StandardColumns.CATEGORY,
        ] = new_category

    for _, _post in sorted(bank_cls.post_processing_steps, key=lambda x: x[0]):
        statement = _post(statement)

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

    time_column = StandardColumns.TIME
    df[time_column] = pd.to_datetime(df[time_column], format="mixed").dt.strftime(
        "%H:%M:%S"
    )

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
