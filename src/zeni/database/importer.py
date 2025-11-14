"""Utilities for importing bank statements into the database."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from zeni.db.database import Database
from zeni.parse.parser import standardize

# Import banks to register them

if TYPE_CHECKING:
    from zeni.db.models import ImportBatch


def import_statement(
    db: Database,
    csv_path: str | Path,
    bank_name: str,
    account_identifier: str | None = None,
    bank_id_column: str | None = None,
) -> ImportBatch:
    """Import a bank statement CSV into the database.

    This is a convenience function that:
    1. Reads the CSV file
    2. Standardizes it using the bank's adapter
    3. Imports it into the database

    Args:
        db: Database instance
        csv_path: Path to the CSV file
        bank_name: Name of the bank (must be registered)
        account_identifier: Optional identifier for the account
        bank_id_column: Column name containing bank transaction IDs in the raw CSV

    Returns:
        ImportBatch with import statistics

    Example:
        >>> db = Database("my_finances.db")
        >>> batch = import_statement(
        ...     db=db,
        ...     csv_path="data/monzo_statement.csv",
        ...     bank_name="monzo",
        ...     bank_id_column="Transaction ID"
        ... )
        >>> print(f"Imported {batch.new_count} new transactions")
    """
    csv_path = Path(csv_path)

    # Verify bank is registered
    try:
        BankRegistry.get_bank(bank_name.lower())
    except KeyError as e:
        raise ValueError(
            f"Bank '{bank_name}' is not registered. "
            f"Available banks: {list(BankRegistry._supported_institutions.keys())}"
        ) from e

    # Read and standardize the CSV
    raw_df = pd.read_csv(csv_path)
    standardized_df = standardize(statement=raw_df, bank=bank_name)

    # If there's a bank ID column in the raw data, we need to preserve it
    # Map it to the standardized dataframe
    if bank_id_column and bank_id_column in raw_df.columns:
        # Add the bank ID column to the standardized dataframe
        standardized_df["_bank_transaction_id"] = raw_df[bank_id_column].values

    # Import into database
    import_batch = db.import_from_dataframe(
        df=standardized_df,
        bank_name=bank_name,
        source_file=csv_path.name,
        account_identifier=account_identifier,
        bank_id_column="_bank_transaction_id" if bank_id_column else None,
    )

    return import_batch


def import_standardized_dataframe(
    db: Database,
    df: pd.DataFrame,
    bank_name: str,
    source_file: str | None = None,
    account_identifier: str | None = None,
    bank_id_column: str | None = None,
) -> ImportBatch:
    """Import an already-standardized DataFrame into the database.

    Use this if you've already processed your data and have it in the
    standardized format (date, name, amount, currency, category, notes).

    Args:
        db: Database instance
        df: Standardized DataFrame
        bank_name: Name of the bank
        source_file: Optional source filename for tracking
        account_identifier: Optional identifier for the account
        bank_id_column: Column name containing bank transaction IDs

    Returns:
        ImportBatch with import statistics
    """
    return db.import_from_dataframe(
        df=df,
        bank_name=bank_name,
        source_file=source_file,
        account_identifier=account_identifier,
        bank_id_column=bank_id_column,
    )
