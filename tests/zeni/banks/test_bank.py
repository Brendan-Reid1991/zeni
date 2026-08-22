import numpy as np
import pandas as pd
import pytest

from zeni.banks import Chase, Lloyds, Monzo
from zeni.banks.bank import Bank, bank_directory
from zeni.banks.utils import IGNORE_COLUMN, TIMELIKE
from zeni.basic_types import TransactionColumns
from zeni.utils.input_resolution import DATE_FMT, normalize_date


@pytest.mark.parametrize(
    "input_name, expected_bank",
    [
        ["chase", Chase],
        ["chse", Chase],
        ["Chse", Chase],
        ["Chasse", Chase],
        ["Loyds", Lloyds],
        ["lloyds", Lloyds],
        ["loyds", Lloyds],
        ["llloyds", Lloyds],
        ["monzo", Monzo],
        ["mnzo", Monzo],
        ["Monzo", Monzo],
    ],
)
def test_bank_directory(input_name, expected_bank):
    assert bank_directory[input_name] is expected_bank


class AllColumnsAndHeader(Bank):
    COLUMNS = (
        TransactionColumns.DATE,
        TIMELIKE,
        TransactionColumns.CATEGORY,
        TransactionColumns.NAME,
        TransactionColumns.AMOUNT,
        TransactionColumns.CURRENCY,
        TransactionColumns.BALANCE,
    )
    HEADER_ROWS = 1


class TooFewColumns(Bank):
    COLUMNS = (
        TransactionColumns.DATE,
        IGNORE_COLUMN,
        TransactionColumns.NOTES,
        TransactionColumns.NAME,
        TransactionColumns.AMOUNT,
    )


PRE_PROCESSING_OVERWRITE = 10_000


@TooFewColumns.pre_process()
def pre_process(df):
    df.loc[0, "Transaction Amount"] = PRE_PROCESSING_OVERWRITE
    return df


class ManyColumnsIgnored(Bank):
    COLUMNS = (
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
    )


POST_PROCESS_OVERWRITE = "Bleugh"


@ManyColumnsIgnored.post_process(0)
def post_process1(df):
    df[TransactionColumns.NAME] = df[TransactionColumns.NAME].apply(
        lambda _: "Should get overwritten"
    )
    return df


@ManyColumnsIgnored.post_process(1)
def post_process2(df):
    df[TransactionColumns.NAME] = df[TransactionColumns.NAME].apply(
        lambda _: POST_PROCESS_OVERWRITE
    )
    return df


def test_pre_processing_steps():
    "Exercises pre processing"
    tfc = TooFewColumns("tests/data/too_few_columns.csv")
    df = tfc.standardize()
    assert df.iloc[0][TransactionColumns.AMOUNT] == PRE_PROCESSING_OVERWRITE


def test_post_processing_steps():
    "Exercises post processing and ordering."
    mci = ManyColumnsIgnored("tests/data/many_columns_ignored.csv")
    df = mci.standardize()
    assert (df[TransactionColumns.NAME] == POST_PROCESS_OVERWRITE).all()


@pytest.fixture(
    params=[
        (AllColumnsAndHeader, "tests/data/all_columns_and_header.csv"),
        (TooFewColumns, "tests/data/too_few_columns.csv"),
        (ManyColumnsIgnored, "tests/data/many_columns_ignored.csv"),
    ]
)
def bank_and_data(request):
    return request.param


@pytest.fixture
def bank(bank_and_data):
    return bank_and_data[0]


@pytest.fixture
def data(bank_and_data):
    return bank_and_data[1]


def test_standardize_removes_ignored_columns_and_renames(bank, data):
    """This test exercises Bank._trim, adding any missing columns,
    standardizing dtypes and escaping invalid characters"""
    standardized = bank(data).standardize()
    assert tuple(standardized.columns) == tuple(TransactionColumns)
    assert pd.api.types.is_datetime64_any_dtype(
        standardized[TransactionColumns.DATE].dtype
    )
    assert standardized[TransactionColumns.AMOUNT].dtype == np.float64
    assert standardized[TransactionColumns.BALANCE].dtype == np.float64


def test_trim(bank, data):
    orig = bank.load(data)
    standardized = bank(data).standardize()
    drop_indices = [
        idx for idx, col in enumerate(bank.COLUMNS) if col in [IGNORE_COLUMN, TIMELIKE]
    ]
    dropped_columns = [x for i, x in enumerate(orig.columns) if i in drop_indices]
    assert not any(col in standardized.columns for col in dropped_columns)
    assert all(x in TransactionColumns for x in standardized.columns)


def test_normalize_datetime(bank, data):
    orig = bank.load(data)
    standardized = bank(data).standardize()

    date_column = orig.columns[bank.COLUMNS.index(TransactionColumns.DATE)]
    if TIMELIKE in bank.COLUMNS:
        time_column = orig.columns[bank.COLUMNS.index(TIMELIKE)]
        _time_data = orig[time_column].astype(str)
    else:
        _time_data = "00:00:00"
    pd.testing.assert_series_equal(
        pd.to_datetime(
            (orig[date_column].astype(str) + " " + _time_data).apply(normalize_date),
            format=DATE_FMT,
        ).rename(TransactionColumns.DATE),
        standardized[TransactionColumns.DATE],
    )


class InvalidBank(Bank):
    COLUMNS = (TransactionColumns.DATE, TransactionColumns.BALANCE)


def test_invalid_number_of_columns_errors():
    with pytest.raises(ValueError, match=r"Column map with .+ items is insufficient"):
        InvalidBank("tests/data/all_columns_and_header.csv").standardize()
