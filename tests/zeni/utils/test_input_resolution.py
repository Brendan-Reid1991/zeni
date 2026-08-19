import pytest
from datetime import date, datetime, time
from zeni.utils.input_resolution import (
    DATE_FMT,
    TIME_FMT,
    TooManyMatchingStringsError,
    NoMatchingStringsError,
    normalize_time,
    normalize_string,
    normalize_date,
    resolve,
    coerce_kwargs,
    coerce_date,
    coerce_to,
)


def test_date_fmt():
    assert DATE_FMT == "%Y-%m-%d"


def test_time_fmt():
    assert TIME_FMT == "%H:%M:%S"


@pytest.mark.parametrize(
    "input_string,expected",
    [
        ("Input", "input"),
        ("Section One", "sectionone"),
        ("Section one, part two", "sectiononeparttwo"),
    ],
)
def test_normalize_string(input_string, expected):
    assert normalize_string(input_string) == expected


@pytest.mark.parametrize(
    "input_obj, expected",
    [
        ("20 June 2007", date(2007, 6, 20)),
        ("20th June 27", date(2027, 6, 20)),
        ("June 19 27", date(2027, 6, 19)),
        (datetime(2005, 1, 1, 12, 3, 1), date(2005, 1, 1)),
        (date(2005, 1, 1), date(2005, 1, 1)),
    ],
)
def test_normalize_date(input_obj, expected):
    """Some of these are just exercising `dateutil`, but if I ever stop using
    dateutil I want this test to fail if the replacement does not do the same thing."""
    assert normalize_date(input_obj) == expected


@pytest.mark.parametrize("input_obj", [12, time(3, 12, 2), [0, 1, 2]])
def test_normalize_date_raises_an_error_for_unrecognised_obj(input_obj):
    with pytest.raises(ValueError, match="Can't normalize this object into a date"):
        normalize_date(input_obj)


@pytest.mark.parametrize(
    "input_obj, expected",
    [
        ("12:01", time(12, 1).strftime(TIME_FMT)),
        ("00:01", time(0, 1).strftime(TIME_FMT)),
        ("03,04,56", time(0, 0, 0).strftime(TIME_FMT)),  # This one reads like a date!
        ("23:04:56", time(23, 4, 56).strftime(TIME_FMT)),
        (time(23, 4, 56), time(23, 4, 56).strftime(TIME_FMT)),
        (datetime(2005, 1, 1, 12, 3, 1), time(12, 3, 1).strftime(TIME_FMT)),
    ],
)
def test_normalize_time(input_obj, expected):
    assert normalize_time(input_obj) == expected


@pytest.mark.parametrize("input_obj", [12, date(3, 12, 2), [0, 1, 2]])
def test_normalize_time_raises_an_error_for_unrecognised_obj(input_obj):
    with pytest.raises(ValueError, match="Can't normalize this object into a timestamp"):
        normalize_time(input_obj)


def test_exact_match_after_normalization():
    candidates = ("Foo Bar", "Baz, Qux", "FoooBar")
    assert resolve("  FOO,bar ", candidates) == "Foo Bar"


def test_unique_startswith_match():
    candidates = ("Alpha", "Beta")
    assert resolve("al", candidates) == "Alpha"


def test_single_difflib_match_wins_regardless_of_substring_count():
    candidates = ("apple", "pineapple", "banana")
    assert resolve("pple", candidates) == "apple"


def test_zero_difflib_one_substring_match():
    candidates = ("blueberrymuffin", "banana")
    assert resolve("berry", candidates) == "blueberrymuffin"


def test_zero_difflib_zero_substring_raises_no_match():
    candidates = ("apple", "banana")
    with pytest.raises(NoMatchingStringsError, match="No matches"):
        resolve("zzz", candidates)


@pytest.mark.parametrize(
    "input_str, candidates",
    [
        ("car", ("carpet", "cartoon", "banana")),  # 0 Difflib, >1 substring
        ("aplpe", ("apple", "appel", "banana")),  # >1 Difflib
        ("appl", ("apple", "appll", "banana")),  # >1 difflib, >1 substring
    ],
)
def test_zero_difflib_multiple_substring_raises_too_many(input_str, candidates):
    with pytest.raises(TooManyMatchingStringsError, match="More than one match"):
        resolve(input_str, candidates)


def test_coerce_kwargs_with_iterable():
    @coerce_kwargs(
        valid_fields=(
            "one",
            "two",
        )
    )
    def func(pos: int, **kwargs):
        return inner(pos, **kwargs)

    def inner(positional, /, one: str, two: int):
        return (positional, one, two)

    with pytest.raises(NoMatchingStringsError):
        func(1, xxx=1, zzz=2)

    assert func(1, on="a", tw=1) == (1, "a", 1)


def test_coerce_kwargs_with_callable():
    class A:
        fields = ("one", "two")

        @coerce_kwargs(lambda self: self.fields)
        def func(self, **kwargs):
            return kwargs

    a = A()
    with pytest.raises(NoMatchingStringsError):
        a.func(x=1)

    assert a.func(on=1, to=2) == {"one": 1, "two": 2}


def test_coerce_to_with_iterable():
    @coerce_to("second_arg", ("one", "two"))
    def func(first_arg, second_arg):
        return first_arg, second_arg

    assert func(1, "on") == (1, "one")
    assert func(1, "wo") == (1, "two")

    with pytest.raises(NoMatchingStringsError):
        func(1, "xyz")


def test_coerce_to_with_callable():
    class A:
        fields = ("one", "two")

        @coerce_to("argument", lambda self: self.fields)
        def func(self, argument):
            return argument

    a = A()
    assert a.func("on") == "one"
    assert a.func("wo") == "two"

    with pytest.raises(NoMatchingStringsError):
        a.func("xyz")


@pytest.mark.parametrize(
    "input_obj, expected",
    [
        ("20 June 2007", date(2007, 6, 20)),
        ("20th June 27", date(2027, 6, 20)),
        ("June 19 27", date(2027, 6, 19)),
        (datetime(2005, 1, 1, 12, 3, 1), date(2005, 1, 1)),
        (date(2005, 1, 1), date(2005, 1, 1)),
    ],
)
def test_coerce_date(input_obj, expected):
    @coerce_date("b")
    def func(a, b):
        return a, b

    assert func("x", input_obj) == ("x", expected)
