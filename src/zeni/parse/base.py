from __future__ import annotations

import pandas as pd

standard_columns = ["date", "time", "type", "name", "amount", "currency"]


class Parse:
    """Parse a CSV file into a standardised format."""

    def __init__(self, field_map: dict[str, str]):
        self.field_map = field_map

    def standardise(self, df: pd.DataFrame) -> pd.DataFrame:
        parsed = pd.DataFrame()
        for to_column, from_column in self.field_map.items():
            parsed[to_column] = df[
                next(col for col in df.columns if from_column.lower() in col.lower())
            ]

        for datetime_col in ["date", "time"]:
            parsed[datetime_col] = pd.to_datetime(parsed[datetime_col]).dt.date
        for string_col in ["type", "name", "currency"]:
            parsed[string_col] = parsed[string_col].astype(str)

        for numeric_col in ["amount"]:
            parsed[numeric_col] = pd.to_numeric(parsed[numeric_col], errors="coerce")

        return parsed


parse_monzo = Parse(
    field_map=zip(
        standard_columns, ["date", "time", "type", "name", "amount", "currency"]
    )
)

parse_chase = Parse(
    field_map=zip(
        standard_columns, ["date", "time", "type", "description", "amount", "currency"]
    )
)
