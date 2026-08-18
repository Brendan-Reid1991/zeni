import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
from zeni.utils.filters import DataframeFilters, filter_rows, filter_dataframe

df = pd.DataFrame(
    [
        [1, 2.1, "abc"],
        [4, 5.05, "def"],
        [711.112, 8, "abcdef"],
    ],
    columns=[
        "column_one",
        "column_two",
        "column_three",
    ],
)


class TestDataFrameFilters:
    filter = DataframeFilters

    def test_equals(self):
        assert_frame_equal(self.filter.equals(df, "column_one", 1), df.iloc[[0]])

    def test_approx_equals(self):
        assert_frame_equal(
            self.filter.approx_equals(df, "column_two", 5.0500001), df.iloc[[1]]
        )

    @pytest.mark.parametrize(
        "column, value, negate, expected_df",
        [
            ["column_three", "ab", False, df.iloc[[0, 2]]],
            ["column_three", "ab", True, df.iloc[[1]]],
        ],
    )
    def test_has_substring(self, column, value, negate, expected_df):
        assert_frame_equal(
            self.filter.has_substring(df, column, value, negate), expected_df
        )

    @pytest.mark.parametrize(
        "column, values, expected_df",
        [
            ["column_one", [1, 4], df.iloc[[0, 1]]],
            ["column_three", ["abc", "def"], df.iloc[[0, 1]]],
        ],
    )
    def test_is_in(self, column, values, expected_df):
        assert_frame_equal(self.filter.is_in(df, column, values), expected_df)

    def test_between(self):
        assert_frame_equal(self.filter.between(df, "column_two", (2, 5)), df.iloc[[0]])

    @pytest.mark.parametrize(
        "column, pred, expected_df",
        [
            ["column_one", lambda x: x > 3, df.iloc[[1, 2]]],
            ["column_two", lambda x: (x < 8) & (x > 5), df.iloc[[1]]],
            ["column_three", lambda x: ("a" in x) & ("e" not in x), df.iloc[[0]]],
        ],
    )
    def test_apply_predicate(self, column, pred, expected_df):
        assert_frame_equal(self.filter.apply_predicate(df, column, pred), expected_df)

    @pytest.mark.parametrize(
        "method, column, value",
        [
            ["equals", "column_one", 100],
            ["approx_equals", "column_one", 100],
            ["has_substring", "column_one", "a"],
            ["is_in", "column_one", [3, 6, 7]],
            ["between", "column_one", (-1, 0)],
            ["apply_predicate", "column_one", lambda x: x < -100],
        ],
    )
    def test_filter_methods_return_empty_df_for_no_matches(self, method, column, value):
        assert getattr(self.filter, method)(df, column, value).empty


@pytest.mark.parametrize(
    "column, setting, expected_df",
    [
        ["column_one", 1, df.iloc[[0]]],  # int
        ["column_two", (2, 5), df.iloc[[0]]],  # tuple
        ["column_three", ["abc", "def"], df.iloc[[0, 1]]],  # list
        ["column_two", 5.0500001, df.iloc[[1]]],  # float
        ["column_three", "def", df.iloc[[1]]],  # str - exact
        ["column_three", "^def", df.iloc[[1, 2]]],  # str - has substring
        ["column_three", "!def", df.iloc[[0]]],  # str - does not have substring
        [
            "column_three",
            "",
            df[df["column_three"].apply(lambda x: x == 0)],
        ],  # str - empty
        ["column_one", lambda x: x > 3, df.iloc[[1, 2]]],  # predicate #1
        [
            "column_three",
            lambda x: ("a" in x) & ("e" not in x),
            df.iloc[[0]],
        ],  # predicate #2
    ],
)
def test_filter_rows(column, setting, expected_df):
    """Exercise each branch of the match/case"""
    assert_frame_equal(filter_rows(df, column, setting), expected_df)


def test_filter_rows_raises_on_invalid_predicate():
    with pytest.raises(ValueError, match="Can't parse this function call"):
        filter_rows(df, "column_one", max)


def test_filter_rows_raises_on_unknown_setting():
    with pytest.raises(ValueError, match="Invalid filter settings:"):
        filter_rows(df, "column_one", df)


def test_filter_dataframe():
    assert_frame_equal(
        filter_dataframe(df, column_one=lambda x: x > 1, column_three="def"),
        df.iloc[[1]],
    )


def test_filter_dataframe_returns_empty_on_no_matches():
    assert filter_dataframe(df, column_one=lambda x: x < 1).empty
