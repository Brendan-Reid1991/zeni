"""Database interface for managing transactions."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from zeni.db.models import Base, ImportBatch, Transaction

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence


class Database:
    """Main interface for interacting with the Zeni transaction database."""

    def __init__(self, db_path: str | Path = ".zeni/zeni.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to 'zeni.db'.
        """
        self.db_path = Path(db_path)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)

        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def import_from_dataframe(
        self,
        df: pd.DataFrame,
        bank_name: str,
        source_file: str | None = None,
        account_identifier: str | None = None,
        bank_id_column: str | None = None,
    ) -> ImportBatch:
        """Import transactions from a standardized pandas DataFrame.

        Args:
            df: DataFrame with standardized columns (date, name, amount, currency, etc.)
            bank_name: Name of the bank (e.g., 'monzo', 'hsbc')
            source_file: Original filename of the import
            account_identifier: Optional identifier for the specific account
            bank_id_column: Column name containing bank transaction IDs (if available)

        Returns:
            ImportBatch object with import statistics
        """
        with self.session() as session:
            # Create import batch
            import_batch = ImportBatch(
                bank_name=bank_name.lower(),
                source_file=source_file,
                import_timestamp=datetime.utcnow(),
            )
            session.add(import_batch)
            session.flush()  # Get the import_batch ID

            new_count = 0
            duplicate_count = 0

            for _, row in df.iterrows():
                # Extract bank transaction ID if available
                bank_transaction_id = None
                if bank_id_column and bank_id_column in df.columns:
                    bank_transaction_id = str(row[bank_id_column])

                # Parse date
                if isinstance(row["date"], str):
                    date = pd.to_datetime(row["date"], dayfirst=True).to_pydatetime()
                else:
                    date = row["date"].to_pydatetime()

                # Create transaction
                transaction = Transaction(
                    bank_transaction_id=bank_transaction_id,
                    bank_name=bank_name.lower(),
                    account_identifier=account_identifier,
                    date=date,
                    name=str(row["name"]),
                    amount=Decimal(str(row["amount"])),
                    currency=str(row.get("currency", "GBP")),
                    category=str(row["category"])
                    if pd.notna(row.get("category"))
                    else None,
                    notes=str(row["notes"]) if pd.notna(row.get("notes")) else None,
                )

                try:
                    session.add(transaction)
                    session.flush()
                    import_batch.transactions.append(transaction)
                    new_count += 1
                except IntegrityError:
                    # Duplicate transaction (same bank_name + bank_transaction_id)
                    session.rollback()
                    duplicate_count += 1

                    # Find existing transaction and link to this import batch
                    if bank_transaction_id:
                        existing = session.execute(
                            select(Transaction).where(
                                Transaction.bank_name == bank_name.lower(),
                                Transaction.bank_transaction_id == bank_transaction_id,
                            )
                        ).scalar_one_or_none()

                        if existing and existing not in import_batch.transactions:
                            import_batch.transactions.append(existing)

                    session.flush()

            # Update batch statistics
            import_batch.transaction_count = new_count + duplicate_count
            import_batch.new_count = new_count
            import_batch.duplicate_count = duplicate_count

            session.commit()
            return import_batch

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        """Get a transaction by its internal ID.

        Args:
            transaction_id: Internal UUID of the transaction

        Returns:
            Transaction object or None if not found
        """
        with self.session() as session:
            return session.get(Transaction, transaction_id)

    def find_transaction_by_bank_id(
        self, bank_name: str, bank_transaction_id: str
    ) -> Transaction | None:
        """Find a transaction by bank name and bank transaction ID.

        Args:
            bank_name: Name of the bank
            bank_transaction_id: Bank's transaction ID

        Returns:
            Transaction object or None if not found
        """
        with self.session() as session:
            result = session.execute(
                select(Transaction).where(
                    Transaction.bank_name == bank_name.lower(),
                    Transaction.bank_transaction_id == bank_transaction_id,
                )
            )
            return result.scalar_one_or_none()

    def get_transactions(
        self,
        bank_name: str | None = None,
        account_identifier: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        category: str | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        limit: int | None = None,
    ) -> Sequence[Transaction]:
        """Query transactions with various filters.

        Args:
            bank_name: Filter by bank name
            account_identifier: Filter by account
            start_date: Filter by minimum date
            end_date: Filter by maximum date
            category: Filter by category
            min_amount: Filter by minimum amount
            max_amount: Filter by maximum amount
            limit: Maximum number of results

        Returns:
            List of Transaction objects
        """
        with self.session() as session:
            query = select(Transaction).order_by(Transaction.date.desc())

            if bank_name:
                query = query.where(Transaction.bank_name == bank_name.lower())
            if account_identifier:
                query = query.where(Transaction.account_identifier == account_identifier)
            if start_date:
                query = query.where(Transaction.date >= start_date)
            if end_date:
                query = query.where(Transaction.date <= end_date)
            if category:
                query = query.where(Transaction.category == category)
            if min_amount:
                query = query.where(Transaction.amount >= min_amount)
            if max_amount:
                query = query.where(Transaction.amount <= max_amount)
            if limit:
                query = query.limit(limit)

            result = session.execute(query)
            return result.scalars().all()

    def update_transaction(
        self,
        transaction_id: str,
        name: str | None = None,
        amount: Decimal | None = None,
        category: str | None = None,
        notes: str | None = None,
        mark_as_edited: bool = True,
    ) -> Transaction | None:
        """Update a transaction's editable fields.

        Args:
            transaction_id: Internal UUID of the transaction
            name: New name/description
            amount: New amount
            category: New category
            notes: New notes
            mark_as_edited: Whether to mark transaction as manually edited

        Returns:
            Updated Transaction object or None if not found
        """
        with self.session() as session:
            transaction = session.get(Transaction, transaction_id)
            if not transaction:
                return None

            if name is not None:
                transaction.name = name
            if amount is not None:
                transaction.amount = amount
            if category is not None:
                transaction.category = category
            if notes is not None:
                transaction.notes = notes

            if mark_as_edited:
                transaction.is_manually_edited = True

            transaction.updated_at = datetime.utcnow()
            session.commit()
            return transaction

    def delete_transaction(self, transaction_id: str) -> bool:
        """Delete a transaction.

        Args:
            transaction_id: Internal UUID of the transaction

        Returns:
            True if deleted, False if not found
        """
        with self.session() as session:
            transaction = session.get(Transaction, transaction_id)
            if not transaction:
                return False

            session.delete(transaction)
            session.commit()
            return True

    def get_import_batches(
        self, bank_name: str | None = None, limit: int | None = None
    ) -> Sequence[ImportBatch]:
        """Get import batch history.

        Args:
            bank_name: Filter by bank name
            limit: Maximum number of results

        Returns:
            List of ImportBatch objects
        """
        with self.session() as session:
            query = select(ImportBatch).order_by(ImportBatch.import_timestamp.desc())

            if bank_name:
                query = query.where(ImportBatch.bank_name == bank_name.lower())
            if limit:
                query = query.limit(limit)

            result = session.execute(query)
            return result.scalars().all()

    def export_to_dataframe(
        self,
        bank_name: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pd.DataFrame:
        """Export transactions to a pandas DataFrame.

        Args:
            bank_name: Filter by bank name
            start_date: Filter by minimum date
            end_date: Filter by maximum date

        Returns:
            DataFrame with transaction data
        """
        transactions = self.get_transactions(
            bank_name=bank_name, start_date=start_date, end_date=end_date
        )

        data = [
            {
                "id": t.id,
                "bank_transaction_id": t.bank_transaction_id,
                "bank_name": t.bank_name,
                "account_identifier": t.account_identifier,
                "date": t.date,
                "name": t.name,
                "amount": float(t.amount),
                "currency": t.currency,
                "category": t.category,
                "notes": t.notes,
                "is_manually_edited": t.is_manually_edited,
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in transactions
        ]

        return pd.DataFrame(data)

    def get_summary_stats(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Get summary statistics for transactions.

        Args:
            start_date: Filter by minimum date
            end_date: Filter by maximum date

        Returns:
            Dictionary with summary statistics
        """
        transactions = self.get_transactions(start_date=start_date, end_date=end_date)

        total_income = sum(float(t.amount) for t in transactions if float(t.amount) > 0)
        total_expenses = sum(
            float(t.amount) for t in transactions if float(t.amount) < 0
        )

        return {
            "total_transactions": len(transactions),
            "total_income": total_income,
            "total_expenses": abs(total_expenses),
            "net": total_income + total_expenses,
            "date_range": {
                "start": min((t.date for t in transactions), default=None),
                "end": max((t.date for t in transactions), default=None),
            },
        }
