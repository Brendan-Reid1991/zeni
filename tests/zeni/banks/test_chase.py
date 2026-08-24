import numpy as np
import pandas as pd

from zeni.banks import Chase
from zeni.banks.chase import foreign_purchases, round_ups, withdrawals
from zeni.banks.utils import TIMELIKE
from zeni.basic_types import Internal, Outgoing, TransactionColumns


def test_chase_class_vars():
    assert Chase.COLUMNS == (
        TransactionColumns.DATE,
        TIMELIKE,
        TransactionColumns.CATEGORY,
        TransactionColumns.NAME,
        TransactionColumns.AMOUNT,
        TransactionColumns.CURRENCY,
        TransactionColumns.BALANCE,
    )
    assert Chase.HEADER_ROWS == 1


def test_decorated_functions():
    assert Chase.pre_processing_steps == []
    np.testing.assert_array_equal(
        Chase.post_processing_steps,
        [
            (0, round_ups),
            (0, withdrawals),
            (0, foreign_purchases),
        ],
    )


def test_round_ups_post_processing():
    df = pd.DataFrame(
        {
            TransactionColumns.NAME: ["Round up", "round up", "rund up", "misc other"],
            TransactionColumns.CATEGORY: [
                "Not a round up",
                "Maybe a round up",
                "Def not",
                "Misc Other",
            ],
        }
    )
    altered_cats = round_ups(df)[TransactionColumns.CATEGORY].values
    should_be = [Internal.ROUNDUP, Internal.ROUNDUP, "Def not", "Misc Other"]
    np.testing.assert_array_equal(altered_cats, should_be)


def test_withdrawals_post_processing():
    df = pd.DataFrame(
        {
            TransactionColumns.NAME: [
                "Cash withdrawal, Cashzone, BENALMADENA",
                "Cash withdrawal, NoteMachine, Ohares",
                "misc other",
            ],
            TransactionColumns.CATEGORY: [
                "Cash withdrawal | EUR 154.99 | FX rate £1 = €1.1510",
                "Cash withdrawal",
                "Misc Other",
            ],
            TransactionColumns.NOTES: ["", "", ""],
        }
    )
    altered = withdrawals(df.copy())

    np.testing.assert_array_equal(
        altered[TransactionColumns.CATEGORY].values,
        [Outgoing.CASH_WITHDRAWAL, Outgoing.CASH_WITHDRAWAL, "Misc Other"],
    )
    np.testing.assert_array_equal(
        altered[TransactionColumns.NOTES].values,
        [
            "Cash withdrawal | EUR 154.99 | FX rate £1 = €1.1510",
            "Cash withdrawal",
            "",
        ],
    )


def test_foreign_purchases_post_processing():
    df = pd.DataFrame(
        {
            TransactionColumns.NAME: [
                "Ryanair",
                "Supermercado",
                "ViVOEXTRA",
            ],
            TransactionColumns.CATEGORY: [
                "Purchase | EUR 35.99 | FX rate £1 = €1.1404",
                "Purchase | EUR 44.71 | FX rate £1 = €1.1403",
                "Purchase",
            ],
            TransactionColumns.NOTES: ["", "", ""],
        }
    )
    altered = foreign_purchases(df.copy())
    np.testing.assert_array_equal(
        altered[TransactionColumns.CATEGORY], ["Purchase", "Purchase", "Purchase"]
    )
    np.testing.assert_array_equal(
        altered[TransactionColumns.NOTES],
        [
            "EUR 35.99 | FX rate £1 = €1.1404",
            "EUR 44.71 | FX rate £1 = €1.1403",
            "",
        ],
    )
    np.testing.assert_array_equal(
        altered[TransactionColumns.NAME], df[TransactionColumns.NAME]
    )
