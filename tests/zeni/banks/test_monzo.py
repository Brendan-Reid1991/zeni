import numpy as np
import pandas as pd

from zeni.banks import Monzo
from zeni.banks.monzo import flex_payments, overdraft_fees, rounds_ups
from zeni.banks.utils import IGNORE_COLUMN, TIMELIKE
from zeni.basic_types import Internal, Outgoing, TransactionColumns


def test_monzo_class_vars():
    assert Monzo.COLUMNS == (
        IGNORE_COLUMN,
        TransactionColumns.DATE,
        TIMELIKE,
        IGNORE_COLUMN,
        TransactionColumns.NAME,
        IGNORE_COLUMN,
        TransactionColumns.CATEGORY,
        TransactionColumns.AMOUNT,
        TransactionColumns.CURRENCY,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        TransactionColumns.NOTES,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
        IGNORE_COLUMN,
    )
    assert Monzo.HEADER_ROWS == 0


def test_decorated_functions():
    assert Monzo.pre_processing_steps == []
    np.testing.assert_array_equal(
        Monzo.post_processing_steps,
        [
            (0, flex_payments),
            (0, overdraft_fees),
            (0, rounds_ups),
        ],
    )


def test_flex_payments_post_processing():
    df = pd.DataFrame(
        {
            TransactionColumns.NAME: [None, "Original name", "Unrelated payment"],
            TransactionColumns.NOTES: [
                "Flex purchase",
                "Paid using FLEX",
                "Ordinary card payment",
            ],
        }
    )

    altered = flex_payments(df.copy())

    np.testing.assert_array_equal(
        altered[TransactionColumns.NAME],
        ["Flex payment", "Flex payment", "Unrelated payment"],
    )
    np.testing.assert_array_equal(
        altered[TransactionColumns.NOTES], df[TransactionColumns.NOTES]
    )


def test_overdraft_fees_post_processing():
    df = pd.DataFrame(
        {
            TransactionColumns.NAME: [None, "Original name", "Unrelated payment"],
            TransactionColumns.CATEGORY: ["General", "General", "Groceries"],
            TransactionColumns.NOTES: [
                "Overdraft charge",
                "Fee for your OVERDRAFT",
                "Ordinary card payment",
            ],
        }
    )

    altered = overdraft_fees(df.copy())

    np.testing.assert_array_equal(
        altered[TransactionColumns.NAME],
        ["Overdraft fees", "Overdraft fees", "Unrelated payment"],
    )
    np.testing.assert_array_equal(
        altered[TransactionColumns.CATEGORY],
        [Outgoing.FEE, Outgoing.FEE, "Groceries"],
    )
    np.testing.assert_array_equal(
        altered[TransactionColumns.NOTES], df[TransactionColumns.NOTES]
    )


def test_rounds_ups_post_processing():
    df = pd.DataFrame(
        {
            TransactionColumns.NAME: [
                "Round Ups Pot",
                "round ups transfer",
                "Round up",
                "Unrelated payment",
            ],
            TransactionColumns.CATEGORY: [
                "Transfers",
                "Savings",
                "Transfers",
                "Groceries",
            ],
        }
    )

    altered = rounds_ups(df.copy())

    np.testing.assert_array_equal(
        altered[TransactionColumns.CATEGORY],
        [Internal.ROUNDUP, Internal.ROUNDUP, "Transfers", "Groceries"],
    )
    np.testing.assert_array_equal(
        altered[TransactionColumns.NAME], df[TransactionColumns.NAME]
    )
