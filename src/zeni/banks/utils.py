"""Helper functions for bank parsing."""

from datetime import time
from decimal import Decimal
from html import unescape

import pandas as pd

from zeni.basic_types import StandardColumns

IGNORE_COLUMN = object()
"""Filler to ignore a column in a statement."""


def _normalize_time(val: object) -> str | None:
    match val:
        case time():
            return val.strftime("%H:%M:%S")
        case _ if pd.isna(val):
            return None
        case str():
            return pd.to_datetime(val, format="mixed").strftime("%H:%M:%S")
        case _:
            raise TypeError(
                f"Cannot normalize time value of type {type(val).__name__!r}: {val!r}"
            )


def standardize_dtypes(
    df: pd.DataFrame,
    use_decimal: bool = False,
) -> pd.DataFrame:
    """
    Standardize DataFrame column types and index by date.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame
    use_decimal : bool, default False
        If True, convert amount columns to Decimal instead of float

    Returns
    -------
    pd.DataFrame
        DataFrame with standardized dtypes.
    """
    df = df.copy()

    date_column = StandardColumns.DATE
    df[date_column] = pd.to_datetime(df[date_column], format="mixed", dayfirst=False)

    time_column = StandardColumns.TIME
    df[time_column] = df[time_column].apply(_normalize_time)

    amount_columns = [StandardColumns.AMOUNT, StandardColumns.BALANCE]

    for col in amount_columns:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace("£", "", regex=False)
                df[col] = df[col].str.replace("$", "", regex=False)
                df[col] = df[col].str.replace(",", "", regex=False)

            if use_decimal:
                df[col] = df[col].apply(
                    lambda x: Decimal(str(x)) if pd.notna(x) else None
                )
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(unescape, na_action="ignore").astype("string")

    return df
