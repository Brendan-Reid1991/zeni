from zeni.basic_types import Addressable, Incoming, Internal, Outgoing, StandardColumns
from zeni.parse.banks.base import Bank, BankRegistry


@BankRegistry.register
class Monzo(Bank):
    _columns = Addressable({"name", "date", "time", "category", "amount", "currency"})
    _categories = Addressable(
        {
            "bills",
            "eating_out",
            "entertainment",
            "general",
            "groceries",
            "income",
            "personal_care",
            "savings",
            "shopping",
            "transfers",
        }
    )

    @classmethod
    def column_map(cls) -> dict[str, str]:
        return {
            cls._columns.name: StandardColumns.NAME,
            cls._columns.amount: StandardColumns.AMOUNT,
            cls._columns.date: StandardColumns.DATE,
            cls._columns.time: StandardColumns.TIME,
            cls._columns.category: StandardColumns.CATEGORY,
            cls._columns.currency: StandardColumns.CURRENCY,
        }

    @classmethod
    def category_map(cls) -> dict[str, str]:
        return {
            cls._categories.bills: Outgoing.BILL,
            cls._categories.eating_out: Outgoing.LEISURE,
            cls._categories.entertainment: Outgoing.LEISURE,
            cls._categories.general: Outgoing.UNCATEGORISED,
            cls._categories.groceries: Outgoing.GROCERIES,
            cls._categories.income: Incoming.INCOME,
            cls._categories.personal_care: Outgoing.LEISURE,
            cls._categories.savings: Internal.SAVINGS,
            cls._categories.shopping: Outgoing.LEISURE,
            cls._categories.tranfers: Internal.TRANSFER,
        }


if __name__ == "__main__":
    print(Addressable(set(["a", "B"])))
