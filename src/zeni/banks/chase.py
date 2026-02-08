"""A bank class for parsing statements from Chase bank."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pandas as pd

from zeni.banks.bank import Bank, register_bank
from zeni.basic_types import Incoming, Internal, Outgoing, Payment, StandardColumns
from zeni.utils import filter_dataframe


@register_bank
class Chase(Bank):
    """Defines parsing rules for Chase bank statements."""

    @staticmethod
    def load(filepath: Path | str) -> pd.DataFrame:
        return pd.read_csv(filepath, skiprows=1)

    @classmethod
    def column_map(cls) -> dict[str, StandardColumns]:
        return {
            "Transaction Description": StandardColumns.NAME,
            "Time": StandardColumns.TIME,
            "Amount": StandardColumns.AMOUNT,
            "Date": StandardColumns.DATE,
            "Transaction Type": StandardColumns.CATEGORY,
            "Currency": StandardColumns.CURRENCY,
            "Balance": StandardColumns.BALANCE,
        }

    @classmethod
    def category_map(cls) -> dict[str, Payment]:
        return {
            "Purchase": Outgoing.LEISURE,
            "Transfer": Internal.TRANSFER,
            "Payment": Incoming.INCOME,
            "Refund": Incoming.REFUND,
            "Direct Debit": Outgoing.BILL,
        }


@Chase.post_process()
def round_ups(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """Chase defines very few payment categories, this step moves round ups
    to an internal ROUNDUP category."""
    round_up_index = filter_dataframe(chase_statement, name="^round up").index
    chase_statement.loc[round_up_index, StandardColumns.CATEGORY] = Internal.ROUNDUP
    return chase_statement


@Chase.post_process()
def classify_payments(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """Chase does not differentiate between bank payments in or out. This finds
    all negative bank payments and maps to a BILL."""
    payments: pd.DataFrame = filter_dataframe(chase_statement, category="^income")
    outgoing_index = filter_dataframe(payments, amount=lambda x: x < 0).index
    chase_statement.loc[outgoing_index, StandardColumns.CATEGORY] = Outgoing.BILL
    return chase_statement


@Chase.post_process()
def withdrawals(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """Cash withdrawals can appear in multiple different formats, this unifies them."""
    payments: pd.DataFrame = filter_dataframe(chase_statement, category="^withdrawal")
    indices = payments.index
    chase_statement.loc[indices, StandardColumns.CATEGORY] = Outgoing.CASH_WITHDRAWAL
    chase_statement.loc[indices, StandardColumns.NOTES] = payments[
        StandardColumns.CATEGORY
    ]
    return chase_statement
