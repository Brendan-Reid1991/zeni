"""A Bank class for parsing Monzo statements."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from zeni.banks.bank import IGNORE_COLUMN, Bank
from zeni.basic_types import Internal, Outgoing, StandardColumns
from zeni.utils import filter_dataframe


class Monzo(Bank):
    """Defines parsing rules for Monzo bank statements."""

    COLUMNS = (
        IGNORE_COLUMN,
        StandardColumns.DATE,
        StandardColumns.TIME,
        IGNORE_COLUMN,
        StandardColumns.NAME,
        IGNORE_COLUMN,
        StandardColumns.CATEGORY,
        StandardColumns.AMOUNT,
        StandardColumns.CURRENCY,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        StandardColumns.NOTES,
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
    statement.loc[flex_rows, StandardColumns.NAME] = "Flex payment"
    return statement


@Monzo.post_process()
def overdraft_fees(statement: pd.DataFrame) -> pd.DataFrame:
    """Overdraft fees are registered as an UNCATEGORISED payment, this step
    appropriately changes the category to FEE."""
    overdraft_rows = filter_dataframe(statement, notes="^overdraft").index
    statement.loc[overdraft_rows, StandardColumns.NAME] = "Overdraft fees"
    statement.loc[overdraft_rows, StandardColumns.CATEGORY] = Outgoing.FEE
    return statement


@Monzo.post_process()
def rounds_ups(statement: pd.DataFrame) -> pd.DataFrame:
    """Post processing Monzo roundups."""
    roundups = filter_dataframe(statement, name="^round ups").index
    statement.loc[roundups, StandardColumns.CATEGORY] = Internal.ROUNDUP
    return statement
