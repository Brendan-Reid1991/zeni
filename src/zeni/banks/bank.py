"""This module defines the Bank base class, as well as standardization procedures."""

from __future__ import annotations

import logging
from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

import pandas as pd

from zeni.basic_types import COLUMN_DEFAULTS, TransactionColumns
from zeni.utils.input_resolution import NoMatchingStringsError, resolve

from .utils import IGNORE_COLUMN, standardize_dtypes

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)

type DataframeProcessor = Callable[[pd.DataFrame], pd.DataFrame]
type ProcessingStep = list[tuple[int, DataframeProcessor]]


BANK_REGISTRY: dict[str, type[Bank]] = {}
"""The registry records all implemented institutions. To be registered, they
must be imported into the zeni/bank/__init__.py"""


def bank_directory(name: str) -> type[Bank]:
    """Return the Bank class for the input bank name.

    Supports fuzzy string matching.
    """
    registered = tuple(BANK_REGISTRY.keys())
    try:
        return BANK_REGISTRY[resolve(name, registered)]
    except NoMatchingStringsError as exc:
        raise KeyError(
            f"Invalid bank name: '{name}'. Supported banks are: {registered}"
        ) from exc


class Bank(ABC):
    """Abstract base class for all implemented institutions.

    Subclasses must define the COLUMNS class variable, which maps each column
    in the bank's CSV to a StandardColumn (or IGNORE_COLUMN to drop it).

    Optionally, pre- and post-processing steps can be registered via the
    @pre_process and @post_process decorators to transform the statement
    before and after column trimming.
    """

    COLUMNS: ClassVar[tuple[str, ...]]

    pre_processing_steps: ClassVar[ProcessingStep]
    post_processing_steps: ClassVar[ProcessingStep]

    def __init_subclass__(cls) -> None:
        """Initialize processing step lists for each subclass."""
        cls.pre_processing_steps = []
        cls.post_processing_steps = []
        BANK_REGISTRY[cls.__name__] = cls

    def __init__(self, filepath: Path | str) -> None:
        self._statement = self.load(filepath)

    @classmethod
    def load(cls, filepath: Path | str) -> pd.DataFrame:
        return pd.read_csv(filepath)

    @classmethod
    def pre_process(
        cls, order: int = 0
    ) -> Callable[[DataframeProcessor], DataframeProcessor]:
        """Decorator to register pre-processing steps with optional ordering."""

        def decorator(fn: DataframeProcessor) -> DataframeProcessor:
            cls.pre_processing_steps.append((order, fn))
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

    def standardize(self) -> pd.DataFrame:
        """Standardize the raw statement into the canonical Zeni format.

        Returns a new DataFrame; the raw statement stored on the instance
        is not mutated.
        """
        statement = self._statement

        if len(self.COLUMNS) != len(statement.columns):
            raise ValueError(
                f"Column map with {len(self.COLUMNS)} items is insufficient for "
                f"{len(statement.columns)} columns in the statement."
                " To ignore some columns, populate that index with IGNORE_COLUMN."
            )

        for _, fn in sorted(self.pre_processing_steps, key=lambda x: x[0]):
            logger.debug(
                "Running %s pre-processing: %s", type(self).__name__, fn.__name__
            )
            statement = fn(statement)

        statement = self._trim(statement)

        for _, fn in sorted(self.post_processing_steps, key=lambda x: x[0]):
            logger.debug(
                "Running %s post-processing: %s", type(self).__name__, fn.__name__
            )
            statement = fn(statement)

        has_balance = TransactionColumns.BALANCE in statement.columns

        missing_columns = [
            col
            for col, _ in TransactionColumns._value2member_map_.items()
            if col not in statement.columns
        ]
        for missing in missing_columns:
            statement[missing] = pd.Series([COLUMN_DEFAULTS[missing]] * len(statement))

        logger.info(
            "Standardized %d transactions from %s", len(statement), type(self).__name__
        )
        statement = standardize_dtypes(statement[list(map(str, TransactionColumns))])

        if not has_balance:
            statement = statement.sort_values(TransactionColumns.DATE)
            statement[TransactionColumns.BALANCE] = statement[
                TransactionColumns.AMOUNT
            ].cumsum()

        return statement

    def _trim(self, statement: pd.DataFrame) -> pd.DataFrame:
        """Drop unwanted columns and rename surviving ones."""
        renaming: dict[str, TransactionColumns] = {}
        drop_columns = []
        for current, map_to in zip(statement.columns, self.COLUMNS, strict=False):
            if map_to is IGNORE_COLUMN:
                drop_columns.append(current)
                continue
            renaming[current] = map_to

        return statement.drop(columns=drop_columns).rename(columns=renaming)
