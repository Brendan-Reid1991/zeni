"""Helper functions for bank parsing."""

from html import unescape

import pandas as pd

from zeni.basic_types import TransactionColumns

IGNORE_COLUMN = object()
"""Filter to ignore a column in a statement."""

TIMELIKE = object()
"""Filter to detect a time-like column if it is reported separately."""


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

    amount_columns = [TransactionColumns.AMOUNT, TransactionColumns.BALANCE]

    for col in amount_columns:
        if col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].astype(str).str.replace("£", "", regex=False)
                df[col] = df[col].str.replace("$", "", regex=False)
                df[col] = df[col].str.replace(",", "", regex=False)
                df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(unescape, na_action="ignore").astype("string")

    return df
