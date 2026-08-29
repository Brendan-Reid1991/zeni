from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
from sqlalchemy import insert, inspect, select
from sqlalchemy.orm import Session

from zeni.banks.bank import BANK_REGISTRY
from zeni.database.models import Transaction
from zeni.utils.input_resolution import coerce_to

from .base_repo import Repository, values_of


class TransactionRepo(Repository[Transaction]):
    """A repository for handling transactions in a database."""

    def __init__(self, session: Session):
        super().__init__(session, Transaction)

    @coerce_to("name", values_of("account_name"))
    def from_account(self, name: str) -> Sequence[Transaction]:
        """Get all transactions from the given account name."""
        return self.filter(account_name=name)

    @coerce_to("bank", BANK_REGISTRY)
    def from_bank(self, bank: str) -> Sequence[Transaction]:
        """Get all transactions from the given bank."""
        return self.session.scalars(
            select(Transaction).where(Transaction.account.bank == bank)
        )

    def add_transactions(
        self, account: str, transactions: pd.DataFrame, imported_from: str | None = None
    ) -> None:
        """Bulk add transactions to an account, from a standardized statement.

        Parameters:
        ----------
        account : str
            The name of the account to add these transactions to.
        transactions : pd.DataFrame
            The standardized bank statement that contains these transactions.
        imported_from : str | None, optional
            The statement ID, if it exists. By default None.
        """
        input_data = [
            Transaction.from_standardized(account, data, imported_from=imported_from)
            for _, data in transactions.iterrows()
        ]
        rows = [inspect(t).dict for t in input_data]
        self.session.execute(insert(Transaction).prefix_with("OR IGNORE"), rows)

    def add_transaction(self, account: str, transaction_data: pd.Series) -> None:
        """Add a single transaction from a pandas series."""
        return self.add_transactions(account, pd.DataFrame([transaction_data]))
