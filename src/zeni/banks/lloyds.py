"""Parse statements from Lloyds Bank"""

from zeni.basic_types import TransactionColumns

from .bank import Bank
from .utils import IGNORE_COLUMN


class Lloyds(Bank):
    """Defines parsing rules for Lloyds bank credit card statements."""

    COLUMNS = (
        TransactionColumns.DATE,
        IGNORE_COLUMN,
        TransactionColumns.NOTES,
        TransactionColumns.NAME,
        TransactionColumns.AMOUNT,
    )
