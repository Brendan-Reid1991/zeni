from __future__ import annotations

from decimal import Decimal

from zeni.banks.bank import BANK_REGISTRY
from zeni.basic_types import AccountType
from zeni.database.models import Account
from zeni.utils.input_resolution import coerce_to

from .base_repo import Repository, values_of


class AccountRepo(Repository[Account]):
    """A repository class for Account management.

    Parameters
    ----------
    session: Session
        The sqlalchemy session context.
    """

    def __init__(self, session):
        super().__init__(session, Account)

    @coerce_to("bank", BANK_REGISTRY)
    def add_account(
        self, name: str, bank: str, account_type: AccountType = AccountType.CURRENT
    ) -> None:
        """Add an account to the table.

        Parameters
        ----------
        name : str
            The name of the account, must be unique.
        bank : str
            The bank this account is registered to.
        account_type : AccountType, optional
            What kind of account it is, by default AccountType.CURRENT
        """
        self.session.add(Account(name=name, bank=bank, account_type=account_type))

    @coerce_to("name", values_of("name"))
    def from_name(self, name: str) -> Account:
        """Retrieve an account given it's name.

        Parameters
        ----------
        name : str
            The name of the account.

        Returns
        -------
        Account
            The relevant row in the table.
        """
        return self.filter(name=name)[0]

    @property
    def names(self) -> tuple[str, ...]:
        """Get all account names currently present.

        Returns
        -------
        tuple[str, ...]
            A tuple of account names currently present in the table.
        """
        return tuple(self.elements_of("name"))

    @coerce_to("bank", BANK_REGISTRY)
    def with_bank(self, bank: str) -> tuple[str, ...]:
        """Return all account names with the provided bank.

        Parameters
        ----------
        bank : str
            Which bank to isolate acocunts from.

        Returns
        -------
        tuple[str, ...]
            A tuple of account names registered with the input bank.
        """
        return tuple(self.filter(bank=bank))

    def total_outgoings_from(self, name: str) -> Decimal:
        """Return the total outgoings from the given account.

        Parameters
        ----------
        name : str
            An account name.

        Returns
        -------
        Decimal
            The sum of all negative transactions from this account.
        """
        acc = self.from_name(name)
        return sum(tx.amount for tx in acc.transactions if tx.amount <= 0)

    def total_incomings_to(self, name: str) -> Decimal:
        """Return the total incomings to the given account.

        Parameters
        ----------
        name : str
            An account name.

        Returns
        -------
        Decimal
            The sum of all positive transactions from this account.
        """
        acc = self.from_name(name)
        return sum(tx.amount for tx in acc.transactions if tx.amount > 0)

    def net(self, name: str) -> Decimal:
        """Return the net (total incomings minus total outgoings) for the given account.

        Parameters
        ----------
        name : str
            An account name.

        Returns
        -------
        Decimal
            The sum of all transactions registered to this account.
        """
        return self.total_incomings_to(name) - self.total_outgoings_from(name)
