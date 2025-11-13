# Database Quickstart Guide

You now have a fully functional database layer for storing and managing your bank transactions! Here's how to use it.

## Installation

First, install the updated dependencies:

```bash
pip install -e .
```

## Basic Usage

### 1. Import Transactions from a Bank Statement

```python
from zeni import Database, import_statement

# Create a database (or connect to existing one)
db = Database("my_finances.db")

# Import a Monzo statement
batch = import_statement(
    db=db,
    csv_path="data/samples/monzo.csv",
    bank_name="monzo",
    account_identifier="current_account",  # Optional - for multiple accounts
    bank_id_column="Transaction ID"  # Column with bank's transaction IDs
)

print(f"Imported {batch.new_count} new transactions")
print(f"Skipped {batch.duplicate_count} duplicates")
```

### 2. Query Transactions

```python
# Get all transactions
all_txns = db.get_transactions()

# Get recent transactions
recent = db.get_transactions(limit=10)

# Filter by date range
from datetime import datetime
jan_txns = db.get_transactions(
    start_date=datetime(2025, 1, 1),
    end_date=datetime(2025, 1, 31)
)

# Filter by category
groceries = db.get_transactions(category="groceries")

# Combine filters
recent_groceries = db.get_transactions(
    category="groceries",
    start_date=datetime(2025, 1, 1),
    limit=5
)

# Print transactions
for txn in recent:
    print(f"{txn.date.date()} | {txn.name:30s} | £{float(txn.amount):>8.2f}")
```

### 3. Get Summary Statistics

```python
stats = db.get_summary_stats()

print(f"Total transactions: {stats['total_transactions']}")
print(f"Total income: £{stats['total_income']:.2f}")
print(f"Total expenses: £{stats['total_expenses']:.2f}")
print(f"Net: £{stats['net']:.2f}")
```

### 4. Update Transactions (Manual Editing)

```python
# Get a transaction by ID
txn = db.get_transaction("some-uuid-here")

# Or find by bank transaction ID
txn = db.find_transaction_by_bank_id("monzo", "tx_0000ABC123")

# Update it
db.update_transaction(
    transaction_id=txn.id,
    category="corrected_category",
    notes="Manually corrected"
)
```

### 5. Export to Pandas for Analysis

```python
# Export all transactions
df = db.export_to_dataframe()

# Export with filters
df = db.export_to_dataframe(
    bank_name="monzo",
    start_date=datetime(2025, 1, 1)
)

# Now you can do pandas analysis
print(df.groupby("category")["amount"].sum())
```

## Complete Example

Here's a complete workflow:

```python
from zeni import Database, import_statement
from datetime import datetime

# Create database
db = Database("finances.db")

# Import statements
print("Importing Monzo transactions...")
batch = import_statement(
    db=db,
    csv_path="data/samples/monzo.csv",
    bank_name="monzo",
    account_identifier="current_account",
    bank_id_column="Transaction ID"
)

print(f"✓ Imported {batch.new_count} transactions")

# Get summary
stats = db.get_summary_stats()
print(f"\n💰 Summary:")
print(f"  Income:   £{stats['total_income']:>10,.2f}")
print(f"  Expenses: £{stats['total_expenses']:>10,.2f}")
print(f"  Net:      £{stats['net']:>10,.2f}")

# Show top spending categories
df = db.export_to_dataframe()
expenses = df[df["amount"] < 0]
by_category = expenses.groupby("category")["amount"].sum().sort_values()

print(f"\n📊 Top Spending Categories:")
for category, amount in by_category.head(5).items():
    print(f"  {category:20s}: £{abs(amount):>8.2f}")

# Find transactions that might need review
uncategorised = db.get_transactions(category="uncategorised")
print(f"\n⚠️  {len(uncategorised)} transactions need categorisation")
```

## Key Features

### ✅ Automatic Deduplication
- Won't import the same transaction twice (based on bank transaction ID)
- Safe to re-import the same statement file

### ✅ Multi-Bank Support
- Store transactions from different banks in one database
- Each bank has its own adapter for standardization

### ✅ Multiple Accounts
- Use `account_identifier` to distinguish accounts from the same bank
- Query by specific account

### ✅ Import Tracking
- Every import creates a batch record
- Track when data was imported and from which file

### ✅ Manual Editing Support
- Update transactions after import
- Automatically marks transactions as manually edited
- Perfect for building a review UI later

## Next Steps

1. **Add More Banks**: Create adapters for your other banks (HSBC, Barclays, etc.)
2. **Build Streamlit UI**: Create an interactive app for reviewing and categorizing transactions
3. **Add Analytics**: Build reports, charts, and budget tracking
4. **Category Management**: Implement auto-categorization rules

## File Structure

```
zeni/
├── src/zeni/
│   ├── db/
│   │   ├── __init__.py         # Database exports
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── database.py         # Database interface
│   │   ├── importer.py         # Import utilities
│   │   └── README.md           # Detailed docs
│   ├── parse/
│   │   ├── banks/
│   │   │   ├── monzo.py        # Monzo adapter
│   │   │   └── base.py         # Bank protocol
│   │   └── parser.py           # Standardization logic
│   └── basic_types.py          # Core types
└── tests/
    └── test_database.py        # Database tests
```

## Need Help?

- Check [src/zeni/db/README.md](src/zeni/db/README.md) for detailed documentation
- See [examples/database_usage.py](examples/database_usage.py) for more examples
- Run tests: `pytest tests/test_database.py -v`
