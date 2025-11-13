"""A bank class for parsing statements from Chase bank."""

from __future__ import annotations

import pandas as pd

from zeni.banks.bank import PREFERRED_ORDERING, register_bank
from zeni.basic_types import Incoming, Internal, Outgoing, StandardColumns
from zeni.utils import filter_rows


def chase_pre_processor(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """The statements from chase come as a dataframe with a single column,
    and transactions are recorded in a pd.Series in each row.

    Each pd.Series only stores the balance as data, but the .name of the Series is
    as such:
    ```python
    ('17 May 2025', '10:54', 'Purchase', 'Posh Pig', '-7.10', 'GBP')
    ```
    where that is date, time, category, notes, amount and currency.

    This function extracts this information and properly formats it in a dataframe.
    """
    data = []
    for _, entry in list(chase_statement.iterrows())[1:]:
        balance, details = entry.iloc[0], entry.name
        data.append(
            [
                details[0],
                details[3],
                details[2],
                details[4],
                details[5],
                details[3],
                balance,
            ]
        )
    return pd.DataFrame(data, columns=PREFERRED_ORDERING)


def _post_process_round_ups(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """Chase defines very few payment categories, this step moves round ups
    to an internal ROUNDUP category."""
    round_up_index = filter_rows(chase_statement, "name", "^round up").index
    chase_statement.loc[round_up_index, StandardColumns.CATEGORY] = Internal.ROUNDUP
    return chase_statement


def _post_process_payments(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """Chase does not differentiate between bank payments in or out. This finds
    all negative bank payments and maps to a BILL."""
    payments: pd.DataFrame = filter_rows(chase_statement, "category", "^income")
    outgoing_index = filter_rows(payments, "amount", lambda x: x < 0).index
    chase_statement.loc[outgoing_index, StandardColumns.CATEGORY] = Outgoing.BILL
    return chase_statement


@register_bank
class Chase:
    """Defines parsing rules for Chase bank statements."""

    pre_processing_steps = chase_pre_processor
    post_processing_steps = (_post_process_round_ups, _post_process_payments)

    @classmethod
    def column_map(cls) -> dict[str, str]:
        return {
            StandardColumns.NAME: "Name",
            StandardColumns.AMOUNT: "Amount",
            StandardColumns.DATE: "Date",
            StandardColumns.NOTES: "Description",
            StandardColumns.CATEGORY: "Category",
            StandardColumns.CURRENCY: "Currency",
            StandardColumns.BALANCE: "Balance",
        }

    @classmethod
    def category_map(cls) -> dict[str, str]:
        return {
            "Purchase": Outgoing.LEISURE,
            "Transfer": Internal.TRANSFER,
            "Payment": Incoming.INCOME,
        }
