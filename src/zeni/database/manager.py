from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from zeni.banks.bank import standardize
from zeni.basic_types import Account
from zeni.database.engine import Engine
from zeni.database.models import ImportedStatements, Transaction
from zeni.database.utils import DEFAULT_PATHWAY


class DatabaseManager:
    def __init__(
        self, database: str, folder_path: str = DEFAULT_PATHWAY, hard_reset: bool = False
    ):
        self._zeni_engine = Engine(name=database, pathway=folder_path)
        if hard_reset:
            self.delete()
        self._engine = self._zeni_engine.create()

    def delete(self):
        return self._zeni_engine.delete()

    def read_in(
        self, statement: str, bank: str, account_type: Account
    ) -> ImportedStatements:
        """Import a bank statement into the database.

        Args:
            statement: Path to the CSV file
            bank: Bank name (e.g., "Chase")
            account_type: Type of account (e.g., Account.CURRENT)

        Returns:
            ImportedStatements record with import statistics
        """
        standardized: pd.DataFrame = standardize(bank, statement)

        with Session(self._engine, expire_on_commit=False) as session:
            import_record = ImportedStatements(
                bank_name=bank, source_file=statement, import_timestamp=datetime.now()
            )
            session.add(import_record)
            session.flush()

            new_count = 0
            duplicate_count = 0

            for _, row in standardized.iterrows():
                transaction = Transaction.from_standardized(bank, account_type, row)

                # Use nested transaction (savepoint) for each insert
                savepoint = session.begin_nested()
                try:
                    session.add(transaction)
                    session.flush()
                    import_record.transactions.append(transaction)
                    savepoint.commit()
                    new_count += 1
                except Exception:
                    savepoint.rollback()  # Only rollback this transaction
                    duplicate_count += 1

            # Update statistics
            import_record.transaction_count = len(standardized)
            import_record.new_count = new_count
            import_record.duplicate_count = duplicate_count

            session.commit()
            return import_record
