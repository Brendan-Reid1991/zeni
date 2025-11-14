# Zeni Database Layer

This module provides a centralized SQLite database for storing and managing bank transactions across multiple institutions.

## Features

- **Multi-bank support**: Store transactions from different banks in one database
- **Automatic deduplication**: Prevents duplicate transactions based on bank transaction IDs
- **Import tracking**: Keeps history of all imports with metadata
- **Flexible querying**: Filter by date, bank, category, amount, and more
- **Manual editing support**: Mark transactions as manually edited for review workflows
- **Export capabilities**: Export to pandas DataFrames for analysis

## Database Schema

### Transactions Table
- Internal UUID for each transaction
- Bank transaction ID (when provided by bank)
- Bank name and account identifier
- Date, name, amount, currency
- Category and notes
- Metadata: created/updated timestamps, manual edit flag

### Import Batches Table
- Tracks each import session
- Source file, timestamp
- Statistics (new transactions, duplicates)
- Many-to-many relationship with transactions

## Quick Start

```python
from zeni import Database, import_statement

# Create a database
db = Database("my_finances.db")

# Import a bank statement
batch = import_statement(
    db=db,
    csv_path="data/monzo_statement.csv",
    bank_name="monzo",
    account_identifier="current_account",
    bank_id_column="Transaction ID"
)

print(f"Imported {batch.new_count} new transactions")
```

## Core Operations

### Importing Data

```python
# Method 1: Import directly from CSV (recommended)
from zeni import import_statement

batch = import_statement(
    db=db,
    csv_path="statement.csv",
    bank_name="monzo",  # Must be a registered bank
    account_identifier="my_account",  # Optional
    bank_id_column="Transaction ID"  # Column with bank's IDs
)

# Method 2: Import from standardized DataFrame
from zeni import import_standardized_dataframe

batch = import_standardized_dataframe(
    db=db,
    df=standardized_df,  # Must have: date, name, amount, currency, category, notes
    bank_name="monzo",
    bank_id_column="_bank_id"  # Optional
)
```

### Querying Transactions

```python
# Get all transactions
all_txns = db.get_transactions()

# Filter by bank
monzo_txns = db.get_transactions(bank_name="monzo")

# Filter by date range
from datetime import datetime
jan_txns = db.get_transactions(
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 1, 31)
)

# Filter by category
groceries = db.get_transactions(category="groceries")

# Filter by amount
from decimal import Decimal
large_purchases = db.get_transactions(min_amount=Decimal("100.00"))

# Combine filters
recent_groceries = db.get_transactions(
    category="groceries",
    start_date=datetime(2025, 1, 1),
    limit=10
)
```

### Finding Specific Transactions

```python
# By internal ID
txn = db.get_transaction("uuid-here")

# By bank transaction ID
txn = db.find_transaction_by_bank_id("monzo", "tx_0000ABC123")
```

### Updating Transactions

```python
# Update transaction details
updated = db.update_transaction(
    transaction_id="uuid-here",
    name="Corrected Name",
    category="corrected_category",
    notes="Fixed manually"
)

# The transaction will be marked as manually edited
print(updated.is_manually_edited)  # True
```

### Deleting Transactions

```python
success = db.delete_transaction("uuid-here")
```

### Export and Analysis

```python
# Export to DataFrame
df = db.export_to_dataframe(
    bank_name="monzo",  # Optional filter
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 12, 31)
)

# Get summary statistics
stats = db.get_summary_stats()
print(f"Total income: £{stats['total_income']}")
print(f"Total expenses: £{stats['total_expenses']}")
print(f"Net: £{stats['net']}")

# Get import history
batches = db.get_import_batches(bank_name="monzo", limit=5)
for batch in batches:
    print(f"{batch.import_timestamp}: {batch.new_count} new, {batch.duplicate_count} dupes")
```

## Deduplication

The database automatically prevents duplicate transactions:

1. **Bank ID based**: If a transaction has a bank-provided ID, the combination of `(bank_name, bank_transaction_id)` must be unique
2. **Import tracking**: Duplicate transactions found during import are linked to the new import batch but not re-inserted
3. **Statistics**: Import batches track how many duplicates were found

```python
# First import
batch1 = import_statement(db, "statement_jan.csv", "monzo", bank_id_column="Transaction ID")
print(batch1.new_count)  # e.g., 50

# Re-import same file
batch2 = import_statement(db, "statement_jan.csv", "monzo", bank_id_column="Transaction ID")
print(batch2.new_count)  # 0
print(batch2.duplicate_count)  # 50
```

## Multiple Accounts

Use the `account_identifier` parameter to distinguish multiple accounts from the same bank:

```python
# Import from checking account
import_statement(
    db, "monzo_checking.csv", "monzo",
    account_identifier="checking",
    bank_id_column="Transaction ID"
)

# Import from savings account
import_statement(
    db, "monzo_savings.csv", "monzo",
    account_identifier="savings",
    bank_id_column="Transaction ID"
)

# Query specific account
checking_txns = db.get_transactions(
    bank_name="monzo",
    account_identifier="checking"
)
```

## Manual Editing Workflow

The database supports a workflow where some transactions need manual review:

```python
# Import transactions (auto-categorized)
batch = import_statement(db, "statement.csv", "monzo")

# Find uncategorized transactions
uncategorized = db.get_transactions(category="uncategorised")

# Update them manually
for txn in uncategorized:
    # Show to user, get their input...
    db.update_transaction(
        txn.id,
        category="correct_category",
        mark_as_edited=True
    )

# Later, find all manually edited transactions
edited = db.get_transactions()
manually_edited = [t for t in edited if t.is_manually_edited]
```

## Database Location

By default, the database is created as `zeni.db` in the current directory. You can specify a custom path:

```python
# Default location
db = Database()  # Creates ./zeni.db

# Custom location
db = Database("data/my_finances.db")

# Absolute path
db = Database("/Users/me/Documents/finances.db")
```

## Notes

- The database uses SQLite, which is file-based and requires no setup
- All date/time values are stored in UTC
- Amounts are stored as `Decimal` with 19 digits precision and 4 decimal places
- The database is thread-safe for concurrent reads, but writes should be serialized
- For production use with multiple users, consider migrating to PostgreSQL (the SQLAlchemy models will work with any database)
