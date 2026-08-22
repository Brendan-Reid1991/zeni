"""This module defines the Bank base class, as well as standardization procedures."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

import pandas as pd

from zeni.basic_types import COLUMN_DEFAULTS, TransactionColumns
from zeni.utils.input_resolution import DATE_FMT, coerce_to, normalize_date

from .utils import IGNORE_COLUMN, TIMELIKE, standardize_dtypes

if TYPE_CHECKING:
    from pathlib import Path


logger = logging.getLogger(__name__)

type DataframeProcessor = Callable[[pd.DataFrame], pd.DataFrame]
type ProcessingStep = list[tuple[int, DataframeProcessor]]


BANK_REGISTRY: dict[str, type[Bank]] = {}
"""The registry records all implemented institutions. To be registered, they
must be imported into the zeni/bank/__init__.py"""


@coerce_to("name", BANK_REGISTRY)
def bank_directory(name: str) -> type[Bank]:
    """Return the Bank class for the input bank name."""
    return BANK_REGISTRY[name]


class Bank:
    """Base class for all implemented institutions.

    Subclasses must define the COLUMNS class variable, which maps each column
    in the bank's CSV to a StandardColumn (or IGNORE_COLUMN to drop it).

    If the bank's CSV has header rows, overwrite the HEADER_ROWS class variable.

    Optionally, pre- and post-processing steps can be registered via the
    @pre_process and @post_process decorators to transform the statement
    before and after column trimming.
    """

    COLUMNS: ClassVar[tuple[str, ...]]
    HEADER_ROWS: int = 0

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
        return pd.read_csv(filepath, header=cls.HEADER_ROWS)

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

        statement = self._run_pre_processing(statement)

        statement = self._normalize_datetime(statement)

        statement = self._trim(statement)

        statement = self._run_post_processing(statement)

        has_balance = TransactionColumns.BALANCE in statement.columns

        missing_columns = [
            col for col in TransactionColumns if col not in statement.columns
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

    def _run_pre_processing(self, statement: pd.DataFrame) -> pd.DataFrame:
        """Run, and log, the pre processing steps."""
        for _, fn in sorted(self.pre_processing_steps, key=lambda x: x[0]):
            logger.debug(
                "Running %s pre-processing: %s", type(self).__name__, fn.__name__
            )
            statement = fn(statement)
        return statement

    def _run_post_processing(self, statement: pd.DataFrame) -> pd.DataFrame:
        """Run, and log, the post processing steps."""
        for _, fn in sorted(self.post_processing_steps, key=lambda x: x[0]):
            logger.debug(
                "Running %s post-processing: %s", type(self).__name__, fn.__name__
            )
            statement = fn(statement)
        return statement

    def _trim(self, statement: pd.DataFrame) -> pd.DataFrame:
        """Drop unwanted columns and rename surviving ones."""
        renaming: dict[str, TransactionColumns] = {}
        drop_columns = []
        for current, map_to in zip(statement.columns, self.COLUMNS, strict=False):
            if map_to in [IGNORE_COLUMN, TIMELIKE]:
                logger.debug(f"Dropped column {current} - marked as {map_to}")
                drop_columns.append(current)
                continue
            renaming[current] = map_to
        return statement.drop(columns=drop_columns).rename(columns=renaming)

    def _normalize_datetime(self, statement: pd.DataFrame) -> pd.DataFrame:
        """If the dataframe has both a TIME and DATE column, merge the former into
        the latter.

        If it does not, append midnight onto the dates.
        """
        date_column = statement.columns[self.COLUMNS.index(TransactionColumns.DATE)]
        if TIMELIKE in self.COLUMNS:
            time_column = statement.columns[self.COLUMNS.index(TIMELIKE)]
            _time_data = statement[time_column].astype(str)
        else:
            _time_data = "00:00:00"

        statement[date_column] = pd.to_datetime(
            (statement[date_column].astype(str) + " " + _time_data).apply(
                normalize_date
            ),
            format=DATE_FMT,
        )
        return statement
