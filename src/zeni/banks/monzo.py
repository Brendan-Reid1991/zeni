"""A Bank class for parsing Monzo statements."""
from __future__ import annotations

import pandas as pd

from zeni.basic_types import Incoming, Internal, Outgoing, StandardColumns
from zeni.banks.bank import register_bank
from zeni.utils import filter_rows


def _post_process_flex_payments(statement: pd.DataFrame) -> pd.DataFrame:
    """Flex payments in Monzo show up with a NaN name, this step
    renames those columns."""
    flex_rows = filter_rows(statement, "notes", "^flex").index
    statement.loc[flex_rows, StandardColumns.NAME] = "Flex payment"
    return statement


def _post_process_overdraft_fees(statement: pd.DataFrame) -> pd.DataFrame:
    """Overdraft fees are registered as an UNCATEGORISED payment, this step
    appropriately changes the category to FEE."""
    overdraft_rows = filter_rows(statement, "notes", "^overdraft fees").index
    statement.loc[overdraft_rows, StandardColumns.NAME] = "Overdraft fees"
    statement.loc[overdraft_rows, StandardColumns.CATEGORY] = Outgoing.FEE
    return statement


@register_bank
class Monzo:
    """Defines parsing rules for Monzo bank statements."""

    post_processing_steps = [_post_process_flex_payments, _post_process_overdraft_fees]

    @classmethod
    def column_map(cls) -> dict[str, str]:
        return {
            StandardColumns.NAME: "Name",
            StandardColumns.AMOUNT: "Amount",
            StandardColumns.DATE: "Date",
            StandardColumns.NOTES: "Description",
            StandardColumns.CATEGORY: "Category",
            StandardColumns.CURRENCY: "Currency",
        }

    @classmethod
    def category_map(cls) -> dict[str, str]:
        return {
            "Bills": Outgoing.BILL,
            "Eating out": Outgoing.LEISURE,
            "Entertainment": Outgoing.LEISURE,
            "General": Outgoing.UNCATEGORISED,
            "Groceries": Outgoing.GROCERIES,
            "Income": Incoming.INCOME,
            "Personal Care": Outgoing.LEISURE,
            "SAvings": Internal.SAVINGS,
            "Shopping": Outgoing.LEISURE,
            "TRansfers": Internal.TRANSFER,
        }
