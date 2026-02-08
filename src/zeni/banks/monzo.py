"""A Bank class for parsing Monzo statements."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

from zeni.banks.bank import Bank, register_bank
from zeni.basic_types import Incoming, Internal, Outgoing, Payment, StandardColumns
from zeni.utils import filter_dataframe


@register_bank
class Monzo(Bank):
    """Defines parsing rules for Monzo bank statements."""

    @classmethod
    def column_map(cls) -> dict[str, StandardColumns]:
        return {
            "Name": StandardColumns.NAME,
            "Time": StandardColumns.TIME,
            "Amount": StandardColumns.AMOUNT,
            "Date": StandardColumns.DATE,
            "Description": StandardColumns.NOTES,
            "Category": StandardColumns.CATEGORY,
            "Currency": StandardColumns.CURRENCY,
        }

    @classmethod
    def category_map(cls) -> dict[str, Payment]:
        return {
            "Bills": Outgoing.BILL,
            "Eating out": Outgoing.LEISURE,
            "Entertainment": Outgoing.LEISURE,
            "General": Outgoing.UNCATEGORISED,
            "Groceries": Outgoing.GROCERIES,
            "Income": Incoming.INCOME,
            "Personal Care": Outgoing.LEISURE,
            "Savings": Internal.SAVINGS,
            "Shopping": Outgoing.LEISURE,
            "TRansfers": Internal.TRANSFER,
        }


@Monzo.pre_process()
def add_balance_column(statement: pd.DataFrame) -> pd.DataFrame:
    """Monzo statements do not provide a Balance column, this adds on."""
    statement[StandardColumns.BALANCE] = statement["Amount"].cumsum()
    return statement


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
    overdraft_rows = filter_dataframe(statement, notes="^overdraft fees").index
    statement.loc[overdraft_rows, StandardColumns.NAME] = "Overdraft fees"
    statement.loc[overdraft_rows, StandardColumns.CATEGORY] = Outgoing.FEE
    return statement


@Monzo.post_process()
def rounds_ups(statement: pd.DataFrame) -> pd.DataFrame:
    """Post processing Monzo roundups."""
    roundups = filter_dataframe(statement, name="^round ups").index
    statement.loc[roundups, StandardColumns.CATEGORY] = Internal.ROUNDUP
    return statement
