"""The DatabaseManager class creates and manages databases."""

import json
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


import pandas as pd
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeni.banks.bank import standardize
from zeni.basic_types import Account, StandardColumns, TransactionFields
from zeni.database.engine import Engine, SQLEngine
from zeni.database.models import ImportedStatements, Rule, Transaction
from zeni.database.utils import (
    DEFAULT_PATHWAY,
    DatabaseFilterT,
    filter_query,
    parse_conditions,
)
from zeni.utils import coerce_to


class DatabaseRetrievalError(Exception): ...


class DatabaseManager:
    """Manage a database."""

    def __init__(
        self, database: str, folder_path: str = DEFAULT_PATHWAY, hard_reset: bool = False
    ):
        self.label = database
        self._zeni = Engine(name=self.label, pathway=folder_path)
        if hard_reset:
            self.delete()
            self._zeni = Engine(name=self.label, pathway=folder_path)
        self.inspector = inspect(self._zeni._sql)

    @property
    def tables(self) -> list[str]:
        """A list of all tables in the database."""
        return self.inspector.get_table_names()

    def load_table(self, table: str, focused: bool = True) -> pd.DataFrame:
        """Load a table from the database and return it as a pandas dataframe.

        Parameters
        ----------
        table : str
            The name of the table.
        focused : bool, optional
            Whether or not to only show the columns included in StandardColummns,
            by default True

        Returns
        -------
        pd.DataFrame
            A pandas dataframe object.

        Raises
        ------
        DatabaseRetrievalError
            If an invalid table name is supplied.
        """
        try:
            df = pd.read_sql_table(table, self.backend)
        except ValueError as exc:
            populated = "\n\t- " + "\n\t- ".join(self.tables)
            raise DatabaseRetrievalError(
                f"No table '{table}' in database instance: {self.label}.\n"
                f"Populated tables are: {populated}"
            ) from exc
        if focused:
            return df[[TransactionFields.BANK, *StandardColumns]]
        return df

    @property
    def backend(self) -> SQLEngine:
        """The SQLAlchemy engine object."""
        return self._zeni._sql

    def delete(self):
        """Remove this database."""
        self._zeni.close_connections()
        self._zeni.delete()

    def read_in(
        self,
        bank: str,
        account_type: Account,
        statement: str,
    ) -> ImportedStatements:
        """Import a bank statement into the database.

        Parameters
        ----------
        bank : str
            Bank name (e.g., "Chase")
        account_type : Account
            Type of account (e.g., Account.CURRENT)
        statement : str
            Path to the CSV file

        Returns
        -------
        ImportedStatements
            ImportedStatements record with import statistics
        """
        standardized: pd.DataFrame = standardize(bank, statement)

        with Session(self.backend, expire_on_commit=False) as session:
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
                except IntegrityError:
                    savepoint.rollback()  # Only rollback this transaction
                    duplicate_count += 1

            # Update statistics
            import_record.transaction_count = len(standardized)
            import_record.new_count = new_count
            import_record.duplicate_count = duplicate_count

            session.commit()

        # Apply categorisation rules to newly imported transactions
        new_ids = [t.id for t in import_record.transactions]
        if new_ids:
            self.apply_rules(transaction_ids=new_ids)

        return import_record

    @coerce_to(tuple(TransactionFields))
    def lookup(self, focused: bool = True, **kwargs) -> pd.DataFrame:
        """Look up transactions using filter patterns.

        Uses the same filter syntax as filter_dataframe:
            - str: exact match (e.g. bank="Chase")
            - "^...": substring match (e.g. name="^coffee")
            - "!...": substring exclusion (e.g. name="!fee")
            - list: membership (e.g. bank=["Chase", "Amex"])
            - tuple: range (e.g. amount=(100, 500))
            - float/Decimal: approximate match

        Kwargs are fuzzy-matched to Transaction field names via @coerce_to.

        Parameters
        ----------
        focused : bool, optional
            Whether to only show StandardColumns, by default True.

        Returns
        -------
        pd.DataFrame
        """
        stmt = filter_query(select(Transaction), Transaction, **kwargs)
        stmt = stmt.order_by(Transaction.date.desc())

        with Session(self.backend) as session:
            results = session.execute(stmt).scalars().all()
            if not results:
                return pd.DataFrame(columns=[*StandardColumns] if focused else [])
            df = pd.DataFrame(
                [
                    {field: getattr(transaction, field) for field in TransactionFields}
                    for transaction in results
                ]
            )
            if focused:
                return df[[*StandardColumns]]
            return df

    def get_transaction(self, transaction_id: str) -> Transaction | None:
        """Get a single transaction by ID.

        Parameters
        ----------
        transaction_id : str
            The UUID of the transaction.

        Returns
        -------
        Transaction | None
            The transaction if found, None otherwise.
        """
        with Session(self.backend) as session:
            return session.get(Transaction, transaction_id)

    def update_transaction(
        self,
        transaction_id: str,
        *,
        name: str | None = None,
        category: str | None = None,
        notes: str | None = None,
    ) -> Transaction | None:
        """Update user-editable fields of a transaction.

        Parameters
        ----------
        transaction_id : str
            The UUID of the transaction to update.
        name : str, optional
            New name for the transaction.
        category : str, optional
            New category for the transaction.
        notes : str, optional
            New notes for the transaction.

        Returns
        -------
        Transaction | None
            The updated transaction. If name, category and notes are all "None",
            "None" is returned.

        Raises
        ------
        DatabaseRetrievalError
            If no transaction with the given ID exists.
        """
        if not any([name, category, notes]):
            return None

        with Session(self.backend, expire_on_commit=False) as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction is None:
                raise DatabaseRetrievalError(
                    f"No transaction with ID '{transaction_id}' found."
                )

            if name:
                transaction.name = name
            if category:
                transaction.category = category
            if notes:
                transaction.notes = notes

            transaction.updated_at = datetime.now()

            session.commit()
            return transaction

    def update_transactions(
        self,
        transaction_ids: list[str],
        *,
        category: str | None = None,
        notes: str | None = None,
    ) -> int:
        """Bulk update multiple transactions.

        Parameters
        ----------
        transaction_ids : list[str]
            List of transaction UUIDs to update.
        category : str, optional
            New category for all specified transactions.
        notes : str, optional
            New notes for all specified transactions.

        Returns
        -------
        int
            Number of transactions updated.
        """
        if not transaction_ids:
            return 0

        updated_count = 0
        with Session(self.backend) as session:
            for tid in transaction_ids:
                if self.update_transaction(tid, category=category, notes=notes):
                    updated_count += 1
            session.commit()
        return updated_count

    def add_rule(
        self,
        conditions: dict[TransactionFields, DatabaseFilterT],
        category: str,
        *,
        notes: str | None = None,
        priority: int = 0,
    ) -> Rule:
        """Create a categorisation rule and apply it retroactively.

        Parameters
        ----------
        conditions : dict
            Filter conditions mapping field names to patterns, e.g.
            {"name": "^tesco"} or {"name": "^tesco", "amount": (-50, 0)}.
            Uses the same syntax as filter_query / lookup.
        category : str
            Target category to assign to matching transactions.
        notes : str, optional
            Notes to set on matching transactions.
        priority : int, optional
            Rule priority (higher priority rules run later and can override).

        Returns
        -------
        Rule
            The created rule.
        """
        # Serialize conditions — convert tuples to lists for JSON
        serializable = {
            k: list(v) if isinstance(v, tuple) else v for k, v in conditions.items()
        }
        with Session(self.backend, expire_on_commit=False) as session:
            rule = Rule(
                conditions=json.dumps(serializable),
                category=category,
                notes=notes,
                priority=priority,
            )
            session.add(rule)
            session.commit()

        # Apply retroactively to all existing transactions
        self.apply_rules(rule_ids=[rule.id])
        return rule

    def get_rules(self) -> list[Rule]:
        """Return all rules ordered by priority ascending."""
        with Session(self.backend) as session:
            return (
                session.execute(select(Rule).order_by(Rule.priority, Rule.created_at))
                .scalars()
                .all()
            )

    def delete_rule(self, rule_id: str) -> None:
        """Delete a rule by ID. Does not revert affected transactions."""
        with Session(self.backend) as session:
            rule = session.get(Rule, rule_id)
            if rule is None:
                raise DatabaseRetrievalError(f"No rule with ID '{rule_id}' found.")
            session.delete(rule)
            session.commit()

    def apply_rules(
        self,
        *,
        transaction_ids: list[str] | None = None,
        rule_ids: list[str] | None = None,
    ) -> int:
        """Apply categorisation rules to transactions.

        Parameters
        ----------
        transaction_ids : list[str], optional
            If provided, only apply rules to these transactions.
            Otherwise applies to all transactions.
        rule_ids : list[str], optional
            If provided, only apply these specific rules.
            Otherwise applies all rules.

        Returns
        -------
        int
            Total number of transactions updated.
        """
        total_updated = 0
        with Session(self.backend) as session:
            # Fetch rules
            stmt = select(Rule).order_by(Rule.priority, Rule.created_at)
            if rule_ids:
                stmt = stmt.where(Rule.id.in_(rule_ids))
            rules = session.execute(stmt).scalars().all()

            for rule in rules:
                match_stmt = filter_query(
                    select(Transaction), Transaction, **parse_conditions(rule.conditions)
                )
                if transaction_ids:
                    match_stmt = match_stmt.where(Transaction.id.in_(transaction_ids))

                matches: Sequence[Transaction] = (
                    session.execute(match_stmt).scalars().all()
                )
                for txn in matches:
                    txn.category = rule.category
                    if rule.notes is not None:
                        txn.notes = rule.notes
                    total_updated += 1

            session.commit()
        return total_updated
