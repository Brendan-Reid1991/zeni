"""A Bank class for parsing Monzo statements."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from zeni.banks.bank import IGNORE_COLUMN, Bank
from zeni.basic_types import Internal, Outgoing, TransactionColumns
from zeni.utils import filter_dataframe

from .utils import TIMELIKE


class Monzo(Bank):
    """Defines parsing rules for Monzo bank statements."""

    COLUMNS = (
        IGNORE_COLUMN,
        TransactionColumns.DATE,
        TIMELIKE,
        IGNORE_COLUMN,
        TransactionColumns.NAME,
        IGNORE_COLUMN,
        TransactionColumns.CATEGORY,
        TransactionColumns.AMOUNT,
        TransactionColumns.CURRENCY,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        TransactionColumns.NOTES,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
    )


@Monzo.post_process()
def flex_payments(statement: pd.DataFrame) -> pd.DataFrame:
    """Flex payments in Monzo show up with a NaN name, this step
    renames those columns."""
    flex_rows = filter_dataframe(statement, notes="^flex").index
    statement.loc[flex_rows, TransactionColumns.NAME] = "Flex payment"
    return statement


@Monzo.post_process()
def overdraft_fees(statement: pd.DataFrame) -> pd.DataFrame:
    """Overdraft fees are registered as an UNCATEGORISED payment, this step
    appropriately changes the category to FEE."""
    overdraft_rows = filter_dataframe(statement, notes="^overdraft").index
    statement.loc[overdraft_rows, TransactionColumns.NAME] = "Overdraft fees"
    statement.loc[overdraft_rows, TransactionColumns.CATEGORY] = Outgoing.FEE
    return statement


@Monzo.post_process()
def rounds_ups(statement: pd.DataFrame) -> pd.DataFrame:
    """Post processing Monzo roundups."""
    roundups = filter_dataframe(statement, name="^round ups").index
    statement.loc[roundups, TransactionColumns.CATEGORY] = Internal.ROUNDUP
    return statement
