"""Parse statements from Lloyds Bank"""

import pandas as pd

from zeni.basic_types import TransactionColumns

from .bank import Bank
from .utils import IGNORE_COLUMN


class LloydsCC(Bank):
    """Defines parsing rules for Lloyds bank credit card statements."""

    COLUMNS = (
        TransactionColumns.DATE,
        IGNORE_COLUMN,
        TransactionColumns.NOTES,
        TransactionColumns.NAME,
        TransactionColumns.AMOUNT,
    )


@LloydsCC.pre_process()
def negate_amount(df: pd.DataFrame) -> pd.DataFrame:
    """Lloyds Credit Card statements don't have the concept of balance, so payments
    out are positive while payments in are negative. This steps negates the entire
    `amount` column so it properly represents "payments out / payemnts in".
    """
    df["Transaction Amount"] = -df["Transaction Amount"]
    return df
