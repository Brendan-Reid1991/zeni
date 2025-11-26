"""Test script to import a CSV into the database."""

from datetime import datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy.orm import Session

from zeni.banks.bank import standardize
from zeni.basic_types import Account
from zeni.database.engine import Engine
from zeni.database.models import ImportedStatements, Transaction

# Step 1: Create engine and create tables if they don't exist
print("Setting up database...")
engine = Engine(name="transactions", pathway=".zeni/", echoes=True).create()

# Step 2: Read and standardize the CSV
print("\nReading and standardizing CSV...")
csv_path = "data/samples/Chase.csv"
bank_name = "Chase"

# Use the standardize function (handles loading + processing)
standardized_df = standardize(bank=bank_name, filepath=csv_path)

# Add account column (Chase CSVs don't specify this)
standardized_df["account"] = (
    Account.DEBIT
)  # Assume all Chase transactions are from debit account

print(f"Loaded {len(standardized_df)} rows")
print(f"\nStandardized columns: {list(standardized_df.columns)}")
print(f"\nFirst standardized row:\n{standardized_df.iloc[0]}")

# Step 3: Create a session
print("\n" + "=" * 50)
print("Creating database session...")
session = Session(engine)

try:
    # Step 4: Create an ImportedStatements record
    import_record = ImportedStatements(
        bank_name=bank_name,
        source_file=csv_path,
        import_timestamp=datetime.now(),
    )
    session.add(import_record)
    session.flush()  # Get the ID without committing

    print(f"\nCreated import record: {import_record.id}")

    # Step 5: Import transactions
    new_count = 0
    duplicate_count = 0

    for idx, row in standardized_df.iterrows():
        # Create Transaction object
        transaction = Transaction(
            bank=bank_name,
            account=row["account"],  # From standardized data
            date=row["date"],
            time=row["time"],
            name=row["name"],
            category=row["category"],
            amount=Decimal(str(row["amount"])),
            currency=row["currency"],
            notes=row["notes"] if pd.notna(row.get("notes")) else None,
            balance=Decimal(str(row["balance"])),
        )

        try:
            session.add(transaction)
            session.flush()  # Try to insert

            # Link to import record
            import_record.transactions.append(transaction)

            new_count += 1
            print(
                f"✓ Added: {transaction.date.date()} {transaction.time} - {transaction.name} - {transaction.amount}"
            )

        except Exception as e:
            session.rollback()
            duplicate_count += 1
            print(f"⚠ Error on {row['date'].date()} {row['time']} - {row['name']}: {e}")

    # Step 6: Update import record stats
    import_record.transaction_count = len(standardized_df)
    import_record.new_count = new_count
    import_record.duplicate_count = duplicate_count

    # Step 7: Commit everything
    print("\n" + "=" * 50)
    print("Committing to database...")
    session.commit()

    print("\n✅ Import complete!")
    print(f"   Total transactions: {import_record.transaction_count}")
    print(f"   New: {import_record.new_count}")
    print(f"   Duplicates: {import_record.duplicate_count}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    session.rollback()
    raise

finally:
    session.close()
    print("\nSession closed.")
