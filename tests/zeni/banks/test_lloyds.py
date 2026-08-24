import numpy as np
import pandas as pd

from zeni.banks import LloydsCC
from zeni.banks.lloyds import negate_amount
from zeni.banks.utils import IGNORE_COLUMN
from zeni.basic_types import TransactionColumns


def test_lloyds_class_vars():
    assert LloydsCC.COLUMNS == (
        TransactionColumns.DATE,
        IGNORE_COLUMN,
        TransactionColumns.NOTES,
        TransactionColumns.NAME,
        TransactionColumns.AMOUNT,
    )
    assert LloydsCC.HEADER_ROWS == 0


def test_decorated_functions():
    np.testing.assert_array_equal(
        LloydsCC.pre_processing_steps,
        [(0, negate_amount)],
    )
    assert LloydsCC.post_processing_steps == []


def test_negate_amount_pre_processing():
    df = pd.DataFrame(
        {
            "Transaction Amount": [10.50, -7.99, 0.0],
            "Transaction Description": [
                "Purchase",
                "Payment received",
                "No movement",
            ],
        }
    )

    altered = negate_amount(df.copy())

    np.testing.assert_array_equal(
        altered["Transaction Amount"],
        [-10.50, 7.99, 0.0],
    )
    np.testing.assert_array_equal(
        altered["Transaction Description"], df["Transaction Description"]
    )
