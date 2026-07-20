"""Parse statements from Lloyds Bank"""

from zeni.basic_types import StandardColumns

from .bank import Bank
from .utils import IGNORE_COLUMN


class Lloyds(Bank):
    """Defines parsing rules for Lloyds bank credit card statements."""

    COLUMNS = (
        StandardColumns.DATE,
        IGNORE_COLUMN,
        StandardColumns.NOTES,
        StandardColumns.NAME,
        StandardColumns.AMOUNT,
    )
