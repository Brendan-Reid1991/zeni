"""Example usage of the Zeni database layer."""

from pathlib import Path

import pandas as pd

from zeni import Database, import_statement

# Create a database instance
db = Database("my_finances.db")

# Example 1: Import a bank statement directly from CSV
# This will automatically standardize and import the data
batch = import_statement(
    db=db,
    csv_path="data/samples/monzo.csv",
    bank_name="monzo",
    account_identifier="my_monzo_current",
    bank_id_column="Transaction ID",
)

print(f"Import completed!")
print(f"  New transactions: {batch.new_count}")
print(f"  Duplicates skipped: {batch.duplicate_count}")
print(f"  Total: {batch.transaction_count}")

# Example 2: Query transactions
print("\n--- Recent Transactions ---")
recent = db.get_transactions(limit=5)
for txn in recent:
    print(f"{txn.date.date()} | {txn.name:30s} | £{txn.amount:>8.2f}")

# Example 3: Query by category
print("\n--- Groceries ---")
groceries = db.get_transactions(category="groceries")
total_groceries = sum(float(t.amount) for t in groceries)
print(f"Found {len(groceries)} grocery transactions totaling £{abs(total_groceries):.2f}")

# Example 4: Update a transaction
if recent:
    transaction_id = recent[0].id
    db.update_transaction(
        transaction_id=transaction_id, category="updated_category", notes="Fixed category"
    )
    print(f"\nUpdated transaction {transaction_id}")

# Example 5: Get summary statistics
print("\n--- Summary Statistics ---")
stats = db.get_summary_stats()
print(f"Total transactions: {stats['total_transactions']}")
print(f"Total income: £{stats['total_income']:.2f}")
print(f"Total expenses: £{stats['total_expenses']:.2f}")
print(f"Net: £{stats['net']:.2f}")

# Example 6: Export to DataFrame for analysis
print("\n--- Export to DataFrame ---")
df = db.export_to_dataframe(bank_name="monzo")
print(f"Exported {len(df)} transactions")
print(df.head())

# Example 7: Get import history
print("\n--- Import History ---")
imports = db.get_import_batches(limit=5)
for imp in imports:
    print(
        f"{imp.import_timestamp.date()} | {imp.bank_name:10s} | "
        f"{imp.new_count} new, {imp.duplicate_count} dupes"
    )
