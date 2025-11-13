"""Tests for the database layer."""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from zeni.db.database import Database
from zeni.db.models import ImportBatch, Transaction


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Create a temporary database for testing."""
    db_path = tmp_path / "test.db"
    return Database(db_path)


@pytest.fixture
def sample_transactions() -> pd.DataFrame:
    """Create a sample DataFrame of standardized transactions."""
    return pd.DataFrame(
        [
            {
                "date": "2025-01-01",
                "name": "Coffee Shop",
                "amount": -3.50,
                "currency": "GBP",
                "category": "leisure",
                "notes": "Morning coffee",
            },
            {
                "date": "2025-01-02",
                "name": "Grocery Store",
                "amount": -45.00,
                "currency": "GBP",
                "category": "groceries",
                "notes": "Weekly shopping",
            },
            {
                "date": "2025-01-03",
                "name": "Salary",
                "amount": 3000.00,
                "currency": "GBP",
                "category": "income",
                "notes": "Monthly salary",
            },
        ]
    )


def test_database_initialization(temp_db: Database):
    """Test that database initializes and creates tables."""
    assert temp_db.db_path.exists()
    assert temp_db.engine is not None


def test_import_from_dataframe(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test importing transactions from a DataFrame."""
    batch = temp_db.import_from_dataframe(
        df=sample_transactions, bank_name="test_bank", source_file="test.csv"
    )

    assert isinstance(batch, ImportBatch)
    assert batch.bank_name == "test_bank"
    assert batch.new_count == 3
    assert batch.duplicate_count == 0
    assert batch.transaction_count == 3


def test_import_with_bank_ids(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test importing transactions with bank transaction IDs."""
    sample_transactions["_bank_id"] = ["tx_001", "tx_002", "tx_003"]

    batch = temp_db.import_from_dataframe(
        df=sample_transactions,
        bank_name="test_bank",
        source_file="test.csv",
        bank_id_column="_bank_id",
    )

    assert batch.new_count == 3

    # Verify we can find transactions by bank ID
    transaction = temp_db.find_transaction_by_bank_id("test_bank", "tx_001")
    assert transaction is not None
    assert transaction.name == "Coffee Shop"
    assert transaction.bank_transaction_id == "tx_001"


def test_duplicate_detection(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test that duplicate transactions are detected."""
    sample_transactions["_bank_id"] = ["tx_001", "tx_002", "tx_003"]

    # First import
    batch1 = temp_db.import_from_dataframe(
        df=sample_transactions,
        bank_name="test_bank",
        bank_id_column="_bank_id",
    )
    assert batch1.new_count == 3
    assert batch1.duplicate_count == 0

    # Second import of same data
    batch2 = temp_db.import_from_dataframe(
        df=sample_transactions,
        bank_name="test_bank",
        bank_id_column="_bank_id",
    )
    assert batch2.new_count == 0
    assert batch2.duplicate_count == 3


def test_get_transactions(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test querying transactions with filters."""
    temp_db.import_from_dataframe(df=sample_transactions, bank_name="test_bank")

    # Get all transactions
    all_transactions = temp_db.get_transactions()
    assert len(all_transactions) == 3

    # Filter by bank name
    bank_transactions = temp_db.get_transactions(bank_name="test_bank")
    assert len(bank_transactions) == 3

    # Filter by category
    groceries = temp_db.get_transactions(category="groceries")
    assert len(groceries) == 1
    assert groceries[0].name == "Grocery Store"

    # Filter by amount range
    expensive = temp_db.get_transactions(min_amount=Decimal("100.00"))
    assert len(expensive) == 1
    assert expensive[0].name == "Salary"


def test_get_transactions_date_range(
    temp_db: Database, sample_transactions: pd.DataFrame
):
    """Test querying transactions by date range."""
    temp_db.import_from_dataframe(df=sample_transactions, bank_name="test_bank")

    # Get transactions in date range
    transactions = temp_db.get_transactions(
        start_date=datetime(2025, 1, 2), end_date=datetime(2025, 1, 3)
    )
    assert len(transactions) == 2


def test_update_transaction(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test updating a transaction."""
    temp_db.import_from_dataframe(df=sample_transactions, bank_name="test_bank")

    # Get a transaction
    transactions = temp_db.get_transactions(limit=1)
    transaction_id = transactions[0].id

    # Update it
    updated = temp_db.update_transaction(
        transaction_id=transaction_id,
        name="Updated Name",
        category="updated_category",
    )

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.category == "updated_category"
    assert updated.is_manually_edited is True


def test_delete_transaction(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test deleting a transaction."""
    temp_db.import_from_dataframe(df=sample_transactions, bank_name="test_bank")

    # Get a transaction
    transactions = temp_db.get_transactions(limit=1)
    transaction_id = transactions[0].id

    # Delete it
    result = temp_db.delete_transaction(transaction_id)
    assert result is True

    # Verify it's gone
    deleted = temp_db.get_transaction(transaction_id)
    assert deleted is None

    # Try deleting again
    result = temp_db.delete_transaction(transaction_id)
    assert result is False


def test_get_import_batches(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test retrieving import batch history."""
    # Import some data
    temp_db.import_from_dataframe(
        df=sample_transactions, bank_name="bank1", source_file="file1.csv"
    )
    temp_db.import_from_dataframe(
        df=sample_transactions, bank_name="bank2", source_file="file2.csv"
    )

    # Get all batches
    all_batches = temp_db.get_import_batches()
    assert len(all_batches) == 2

    # Filter by bank
    bank1_batches = temp_db.get_import_batches(bank_name="bank1")
    assert len(bank1_batches) == 1
    assert bank1_batches[0].source_file == "file1.csv"


def test_export_to_dataframe(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test exporting transactions to DataFrame."""
    temp_db.import_from_dataframe(df=sample_transactions, bank_name="test_bank")

    # Export all
    exported = temp_db.export_to_dataframe()
    assert len(exported) == 3
    assert "name" in exported.columns
    assert "amount" in exported.columns

    # Export filtered
    exported_filtered = temp_db.export_to_dataframe(bank_name="test_bank")
    assert len(exported_filtered) == 3


def test_get_summary_stats(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test getting summary statistics."""
    temp_db.import_from_dataframe(df=sample_transactions, bank_name="test_bank")

    stats = temp_db.get_summary_stats()

    assert stats["total_transactions"] == 3
    assert stats["total_income"] == 3000.00
    assert stats["total_expenses"] == 48.50
    assert stats["net"] == 2951.50


def test_account_identifier(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test using account identifiers to distinguish multiple accounts."""
    # Import to account 1
    temp_db.import_from_dataframe(
        df=sample_transactions, bank_name="test_bank", account_identifier="account_1"
    )

    # Import to account 2
    temp_db.import_from_dataframe(
        df=sample_transactions, bank_name="test_bank", account_identifier="account_2"
    )

    # Verify we have 6 transactions total
    all_transactions = temp_db.get_transactions()
    assert len(all_transactions) == 6

    # Verify we can filter by account
    account_1_txns = temp_db.get_transactions(account_identifier="account_1")
    assert len(account_1_txns) == 3
    assert all(t.account_identifier == "account_1" for t in account_1_txns)


def test_transaction_model_repr(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test Transaction __repr__ method."""
    temp_db.import_from_dataframe(df=sample_transactions, bank_name="test_bank")
    transaction = temp_db.get_transactions(limit=1)[0]

    repr_str = repr(transaction)
    assert "Transaction" in repr_str
    assert "test_bank" in repr_str


def test_import_batch_model_repr(temp_db: Database, sample_transactions: pd.DataFrame):
    """Test ImportBatch __repr__ method."""
    batch = temp_db.import_from_dataframe(df=sample_transactions, bank_name="test_bank")

    repr_str = repr(batch)
    assert "ImportBatch" in repr_str
    assert "test_bank" in repr_str
