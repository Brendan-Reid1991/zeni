from collections.abc import Sequence
from pathlib import Path

import pandas as pd
from sqlalchemy import func, insert, inspect, select
from sqlalchemy.orm import Session

from zeni.banks import bank_directory

from .engine import Engineer
from .models import Account, ImportedStatement, ModelT, Rule, Transaction
from .models.rules import Action, Condition
from .utils import DEFAULT_PATHWAY


class Manager:
    """Class for handling adding, retrieving, and updating a database."""

    def __init__(self, db: str, pathway: Path | str = DEFAULT_PATHWAY):
        self.engineer = Engineer(db, pathway)
        self.engine = self.engineer.engine

    def add_transaction(self, account: str, transaction_data: pd.Series) -> None:
        """Add a transaction to the database.

        Duplicate transactions are silently ignored.

        Parameters
        ----------
        account : str
            Account name to link this transaction to.
        transaction_data : pd.Series
            Transaction data from a pandas Series.
        """
        with Session(self.engine) as session:
            account = self._resolve_account(session, account)
            self._insert_transactions(session, account, pd.DataFrame([transaction_data]))
            session.commit()

    def add_statement(self, account: str, statement: pd.DataFrame) -> None:
        """Add a bank statement to the database.

        Similar to a batched call of meth:`add_transaction` but more efficient.

        Any overlap with existing transactions is ignored.

        Parameters
        ----------
        account : str
            Account name to link this statement to.
        statement : pd.DataFrame
            The statement dataframe.
        """
        with Session(self.engine) as session:
            account = self._resolve_account(session, account)
            self._insert_transactions(session, account, statement)
            session.commit()

    def import_statement(self, account: str, pathway: str | Path) -> None:
        """Import a bank statement file, recording provenance for its transactions.

        Parameters
        ----------
        account : str
            Account name to link this statement to.
        pathway : str | Path
            Path to the statement file.
        """
        pathway = str(pathway)
        with Session(self.engine) as session, session.begin():
            account = self._resolve_account(session, account)
            bank = session.scalar(select(Account.bank).where(Account.name == account))
            standardized_statement = bank_directory(bank)(pathway).standardize()

            imported = ImportedStatement(account=account, source_file=pathway)
            session.add(imported)
            session.flush()

            self._insert_transactions(
                session, account, standardized_statement, imported_from=imported.id
            )

    def total_entries(self, table: type[ModelT]) -> int:
        """Return the total entries of the given table.

        Parameters
        ----------
        table : Model

        Returns
        -------
        int
            Total number of entries.
        """
        with Session(self.engine) as session:
            return self._num_entries(session, table)

    def add_rule(
        self,
        conditions: Sequence[Condition],
        actions: Sequence[Action],
        name: str | None = None,
    ) -> None:
        """Add a rule to the database.

        Parameters
        ----------
        conditions : Sequence[Condition]
            Sequence of conditions to apply.
        actions : Sequence[Action]
            Sequence of actions to apply to those entries that satisfy `conditions`.
        name : str | None, optional
            A name to give to this rule, by default None. If None, is replaced with
            `Rule #x` where x is the number of current rules implemented, plus 1.
        """
        with Session(self.engine) as session:
            if not name:
                name = f"Rule #{self._num_entries(session, Rule) + 1}"
            session.add(Rule(conditions=conditions, actions=actions, name=name))
            session.commit()

    def accounts(self) -> pd.DataFrame:
        return self._get_table(Account)

    def transactions(self) -> pd.DataFrame:
        return self._get_table(Transaction)

    def rules(self) -> pd.DataFrame:
        return self._get_table(Rule)

    def imports(self) -> pd.DataFrame:
        return self._get_table(ImportedStatement)

    def _insert_transactions(
        self,
        session: Session,
        account: str,
        statement: pd.DataFrame,
        imported_from: str | None = None,
    ) -> None:
        transactions = [
            Transaction.from_standardized(account, row, imported_from=imported_from)
            for _, row in statement.iterrows()
        ]
        rows = [inspect(t).dict for t in transactions]
        session.execute(insert(Transaction).prefix_with("OR IGNORE"), rows)

    def _select_all(self, session: Session, table: type[ModelT], field: str):
        return session.scalars(select(getattr(table, field))).all()

    def _num_entries(self, session: Session, table: type[ModelT]) -> int:
        """Private method to return the total number of entries in a specific table.

        To be used during an open context window.

        Parameters
        ----------
        session : Session
            The active database session.
        table : Model
            Which table to count.

        Returns
        -------
        int
            Number of entries in the given table.
        """
        return session.scalar(select(func.count()).select_from(table))
