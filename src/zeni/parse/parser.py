from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from zeni.parse.banks.monzo import Monzo
from zeni.types import StandardColumns

if TYPE_CHECKING:
    from zeni.parse.banks.base import Bank


PERFERRED_ORDERING = tuple(
    map(
        getattr,
        (
            StandardColumns.DATE,
            StandardColumns.TIME,
            StandardColumns.TYPE,
            StandardColumns.CATEGORY,
            StandardColumns.NAME,
            StandardColumns.AMOUNT,
            StandardColumns.CURRENCY,
        ),
        ("value",) * len(StandardColumns),
    )
)


class Parse:
    """Parse a CSV file into a standardised format."""

    def __init__(self, bank: Bank):
        self.bank = bank

    def __call__(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        parsed = pd.DataFrame([], columns=PERFERRED_ORDERING)
        for from_column, to_column in self.bank.column_map.items():
            to_column = to_column.value
            from_column = from_column.value
            try:
                parsed[to_column] = dataframe[
                    next(col for col in dataframe.columns if from_column.lower() in col.lower())
                ]
            except StopIteration as exc:
                raise ValueError(
                    f"Can't find a valid column '{from_column}' to map to '{to_column}'."
                    f" Columns in the dataframe are {list(dataframe.columns)}"
                ) from exc

        for datetime_col in []:
            parsed[datetime_col] = getattr(pd.to_datetime(parsed[datetime_col], format=format).dt, datetime_col)
        for string_col in [
            StandardColumns.CATEGORY,
            StandardColumns.CURRENCY,
            StandardColumns.TYPE,
            StandardColumns.NAME,
        ]:
            parsed[string_col.value] = parsed[string_col.value].astype(str)

        for numeric_col in [StandardColumns.AMOUNT]:
            parsed[numeric_col.value] = pd.to_numeric(parsed[numeric_col.value], errors="coerce")

        return parsed


parse_monzo = Parse(Monzo)
