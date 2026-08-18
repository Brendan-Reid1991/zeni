"""Helper functions for bank parsing."""

from html import unescape

import pandas as pd

from zeni.basic_types import TransactionColumns
from zeni.utils.input_resolution import normalize_date, normalize_time

IGNORE_COLUMN = object()
"""Filler to ignore a column in a statement."""


def standardize_dtypes(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Standardize DataFrame column types and index by date.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame

    Returns
    -------
    pd.DataFrame
        DataFrame with standardized dtypes.
    """
    df = df.copy()

    date_column = TransactionColumns.DATE
    df[date_column] = df[date_column].apply(normalize_date)

    time_column = TransactionColumns.TIME
    df[time_column] = df[time_column].apply(normalize_time)

    amount_columns = [TransactionColumns.AMOUNT, TransactionColumns.BALANCE]

    for col in amount_columns:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace("£", "", regex=False)
                df[col] = df[col].str.replace("$", "", regex=False)
                df[col] = df[col].str.replace(",", "", regex=False)
                df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in df.select_dtypes(include=["object"]).columns:
        if col == date_column or col == time_column:
            continue
        df[col] = df[col].map(unescape, na_action="ignore").astype("string")

    return df
