import numpy as np
import pandas as pd

from zeni.banks.utils import standardize_dtypes
from zeni.basic_types import TransactionColumns


def test_standardize_dtypes_cleans_monetary_columns():
    raw = pd.DataFrame(
        {
            TransactionColumns.AMOUNT: [
                "£1,234.56",
                "$7.89",
                "-10",
                None,
                "invalid",
            ],
            TransactionColumns.BALANCE: [
                "£2,000.00",
                "1,992.11",
                "2,002.11",
                None,
                "0",
            ],
        }
    )

    result = standardize_dtypes(raw)

    pd.testing.assert_series_equal(
        result[TransactionColumns.AMOUNT],
        pd.Series(
            [1234.56, 7.89, -10.0, np.nan, np.nan],
            name=TransactionColumns.AMOUNT,
            dtype="float64",
        ),
    )
    pd.testing.assert_series_equal(
        result[TransactionColumns.BALANCE],
        pd.Series(
            [2000.0, 1992.11, 2002.11, np.nan, 0.0],
            name=TransactionColumns.BALANCE,
            dtype="float64",
        ),
    )


def test_standardize_dtypes_cleans_text_and_preserves_missing_values():
    raw = pd.DataFrame(
        {
            TransactionColumns.NAME: ["Coach &amp; Horses", None],
            TransactionColumns.NOTES: ["A &lt; B", pd.NA],
        }
    )

    result = standardize_dtypes(raw)

    assert result[TransactionColumns.NAME].iloc[0] == "Coach & Horses"
    assert pd.isna(result[TransactionColumns.NAME].iloc[1])
    assert result[TransactionColumns.NOTES].iloc[0] == "A < B"
    assert pd.isna(result[TransactionColumns.NOTES].iloc[1])
    assert result[TransactionColumns.NAME].dtype == pd.StringDtype()
    assert result[TransactionColumns.NOTES].dtype == pd.StringDtype()


def test_standardize_dtypes_does_not_mutate_input_or_convert_datetimes_to_text():
    raw = pd.DataFrame(
        {
            TransactionColumns.DATE: pd.to_datetime(
                ["2025-05-17 10:54", "2025-05-18 00:00"]
            ),
            TransactionColumns.AMOUNT: ["£1.00", "£2.00"],
        }
    )
    original = raw.copy(deep=True)

    result = standardize_dtypes(raw)

    pd.testing.assert_frame_equal(raw, original)
    assert pd.api.types.is_datetime64_any_dtype(result[TransactionColumns.DATE])


def test_standardize_dtypes_accepts_dataframe_without_monetary_columns():
    raw = pd.DataFrame({TransactionColumns.NAME: ["A &amp; B"]})

    result = standardize_dtypes(raw)

    assert result[TransactionColumns.NAME].iloc[0] == "A & B"
