from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Concatenate

import pandas as pd

from zeni.banks import bank_directory
from zeni.basic_types import AccountType, TransactionColumns
from zeni.utils.input_resolution import coerce_datetimes, resolve_argument

from .engine import Engineer
from .models import ImportedStatement
from .utils import DEFAULT_PATHWAY, Workspace


def transactional[**P, R](
    function: Callable[Concatenate[Manager, Workspace, P], R],
) -> Callable[Concatenate[Manager, P], R]:
    """Decorator to automatically open an active workspace for `Manager` methods.

    If there is already an active workspace (i.e. if a decorated function called another)
    then that is used, else one is created and then torn down at the end of the SQL
    Alchemy transaction.
    """

    @wraps(function)
    def _inner(self: Manager, *args: P.args, **kwargs: P.kwargs) -> R:
        if (active := self._active_workspace) is not None:
            return function(self, active, *args, **kwargs)

        with Workspace.open(self.engine) as ws:
            self._active_workspace = ws
            try:
                return function(self, ws, *args, **kwargs)
            finally:
                self._active_workspace = None

    return _inner


class Manager:
    """Class for handling adding, retrieving, and updating a database."""

    def __init__(self, db: str, pathway: Path | str = DEFAULT_PATHWAY):
        self.engineer = Engineer(db, pathway)
        self.engine = self.engineer.engine

        self._active_workspace: Workspace | None = None

    @property
    @transactional
    def accounts(self, workspace: Workspace) -> tuple[str, ...]:
        return workspace.accounts.names

    @transactional
    def add_account(
        self,
        workspace: Workspace,
        name: str,
        bank: str,
        account_type: AccountType = AccountType.CURRENT,
    ):
        if name in self.accounts:
            raise ValueError(f"Account with name '{name}' already exists.")
        workspace.accounts.add_account(name, bank, account_type)

    def _register_statement(
        self, workspace: Workspace, account: str, source_file: str | Path
    ) -> str:
        imported = ImportedStatement(account=account, source_file=source_file)
        workspace.session.add(imported)
        workspace.session.flush()
        return imported.id

    @transactional
    @resolve_argument("account", lambda self: self.accounts)
    def import_statement(
        self,
        workspace: Workspace,
        account: str,
        pathway: str | Path,
    ) -> None:
        """Import a bank statement file.

        Parameters
        ----------
        account : str
            Account name to link this statement to.
        pathway : str | Path
            Path to the statement file.
        """
        pathway = str(pathway)
        acc = workspace.accounts.from_name(account)
        bank = acc.bank
        standardized_statement = bank_directory(bank)(pathway).standardize()
        statement_id = self._register_statement(workspace, acc.name, pathway)
        workspace.transactions.add_transactions(
            acc.name, standardized_statement, imported_from=statement_id
        )

    @transactional
    def retrieve_transactions(
        self, workspace: Workspace, show_metadata: bool = False, **filters
    ) -> pd.DataFrame:
        df = pd.DataFrame.from_records(
            [tx.to_dict() for tx in workspace.transactions.filter(**filters)]
        )
        if show_metadata:
            return df
        return df[[col for col in TransactionColumns] + ["account_name"]]

    @transactional
    @coerce_datetimes("from_date", "to_date")
    def transactions_in_date_range(
        self,
        workspace: Workspace,
        from_date: str | datetime,
        to_date: str | datetime,
        show_metadata: bool = False,
    ) -> pd.DataFrame:
        return self.retrieve_transactions(
            show_metadata=show_metadata, date=(from_date, to_date)
        )
