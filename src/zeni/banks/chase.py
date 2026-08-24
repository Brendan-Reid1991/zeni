"""A bank class for parsing statements from Chase bank."""

from __future__ import annotations

import pandas as pd

from zeni.banks.bank import Bank
from zeni.basic_types import Internal, Outgoing, TransactionColumns
from zeni.utils import filter_dataframe

from .utils import TIMELIKE


class Chase(Bank):
    """Defines parsing rules for Chase bank statements."""

    COLUMNS = (
        TransactionColumns.DATE,
        TIMELIKE,
        TransactionColumns.CATEGORY,
        TransactionColumns.NAME,
        TransactionColumns.AMOUNT,
        TransactionColumns.CURRENCY,
        TransactionColumns.BALANCE,
    )
    HEADER_ROWS = 1


@Chase.post_process()
def round_ups(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """Chase defines very few payment categories, this step moves round ups
    to an internal ROUNDUP category."""
    round_up_index = filter_dataframe(chase_statement, name="^round up").index
    chase_statement.loc[round_up_index, TransactionColumns.CATEGORY] = Internal.ROUNDUP
    return chase_statement


@Chase.post_process()
def withdrawals(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """Cash withdrawals can appear in multiple different formats, depending on dispensed
    currency, this unifies them."""
    payments: pd.DataFrame = filter_dataframe(chase_statement, category="^withdrawal")
    indices = payments.index
    chase_statement.loc[indices, TransactionColumns.CATEGORY] = Outgoing.CASH_WITHDRAWAL
    chase_statement.loc[indices, TransactionColumns.NOTES] = payments[
        TransactionColumns.CATEGORY
    ]
    return chase_statement


@Chase.post_process()
def foreign_purchases(chase_statement: pd.DataFrame) -> pd.DataFrame:
    """Foreign purchases hold the exchange rate in the category field.

    This means each foreign purchase is essentially it's own category. This
    post processing steps moves the FX information into the Notes field.
    """
    fx_info = chase_statement[TransactionColumns.CATEGORY].str.extract(
        r"Purchase \| (.+)", expand=False
    )
    fx_mask = fx_info.notna()
    chase_statement.loc[fx_mask, TransactionColumns.NOTES] = fx_info[fx_mask]
    chase_statement.loc[fx_mask, TransactionColumns.CATEGORY] = "Purchase"
    return chase_statement
