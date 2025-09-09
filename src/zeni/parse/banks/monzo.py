from collections.abc import Mapping
from enum import Enum
from typing import ClassVar

from zeni.parse.banks.base import Bank
from zeni.types import Incoming, Internal, Outgoing, Payment, StandardColumns


class Monzo(Bank):
    class Columns(str, Enum):
        NAME = "name"
        DATE = "date"
        TIME = "time"
        TYPE = "TYPE"
        CATEGORY = "category"
        AMOUNT = "amount"
        CURRENCY = "currency"

    class Types(str, Enum):
        CARD_PAYMENT = "card payment"
        DIRECT_DEBIT = "direct debit"
        FASTER_PAYMENT = "faster payment"
        FLEX = "flex"
        MONZO_TO_MONZO = "monzo-to-monzo"
        POT_TRANSFER = "pot transfer"
        OVERDRAFT = "overdraft"

    class Categories(str, Enum):
        BILLs = "bills"
        EATING_OUT = "eating_out"
        ENTERTAINMENT = "entertainment"
        GENERAL = "general"
        GROCERIES = "groceries"
        INCOME = "income"
        PERSONAL_CARE = "personal_care"
        SAVINGS = "savings"
        SHOPPING = "shopping"
        TRANSFERS = "transfers"

    column_map: ClassVar[Mapping[Columns, StandardColumns]] = {
        Columns.AMOUNT: StandardColumns.AMOUNT,
        Columns.CATEGORY: StandardColumns.CATEGORY,
        Columns.CURRENCY: StandardColumns.CURRENCY,
        Columns.DATE: StandardColumns.DATE,
        Columns.TIME: StandardColumns.TIME,
        Columns.NAME: StandardColumns.NAME,
        Columns.TYPE: StandardColumns.TYPE,
    }

    type_map: ClassVar[Mapping[Types, Payment]] = {
        Internal: (Types.POT_TRANSFER,),
        Outgoing: (
            Types.MONZO_TO_MONZO,
            Types.CARD_PAYMENT,
            Types.DIRECT_DEBIT,
        ),
        Incoming: {
            Types.MONZO_TO_MONZO,
            Types.FASTER_PAYMENT,
        },
    }

    category_map: ClassVar[Mapping[Categories, Incoming | Outgoing | Internal]] = {
        Categories.BILLs: Outgoing.BILL,
        Categories.EATING_OUT: Outgoing.LEISURE,
        Categories.ENTERTAINMENT: Outgoing.LEISURE,
        Categories.GENERAL: Outgoing.UNCATEGORISED,
        Categories.GROCERIES: Outgoing.GROCERIES,
        Categories.INCOME: Incoming.TRANSFER_IN_EXTERNAL,
        Categories.PERSONAL_CARE: Outgoing.LEISURE,
        Categories.SAVINGS: Internal.SAVINGS,
        Categories.SHOPPING: Outgoing.LEISURE,
        Categories.TRANSFERS: Internal.TRANSFER,
    }
