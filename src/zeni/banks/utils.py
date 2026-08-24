"""Helper functions for bank parsing."""

from html import unescape

import pandas as pd

from zeni.basic_types import ColumnFlags, TransactionColumns

IGNORE_COLUMN = ColumnFlags.IGNORE
TIMELIKE = ColumnFlags.TIMELIKE
type ColumnMapping = TransactionColumns | ColumnFlags


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
            df[col] = pd.to_numeric(
                df[col].astype("string").str.replace(r"[£$,]", "", regex=True),
                errors="coerce",
            ).astype("float64")

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].map(unescape, na_action="ignore").astype("string")

    return df.convert_dtypes(convert_floating=False)
