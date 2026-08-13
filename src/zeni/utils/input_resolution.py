"""A collection of utilities to resolve user input errors."""

import difflib
import inspect
from collections.abc import Callable, Iterable, Sequence
from functools import lru_cache, wraps
from typing import Any, ParamSpec, TypeVar

from dateutil.parser import parse


class NoMatchingStringsError(Exception):
    def __init__(self, input_string: str, candidates: Sequence[str]) -> None:
        candidates_list = "\n\t- ".join(candidates)
        super().__init__(
            f"No matches for '{input_string}' found in candidates:\n\t- "
            + candidates_list
        )


class TooManyMatchingStringsError(Exception):
    def __init__(self, input_string: str, matches: Sequence[str]) -> None:
        matches_list = "\n\t- ".join(matches)
        super().__init__(
            f"More than one match found for '{input_string}':\n\t-" + matches_list
        )


def normalize(candidate: str) -> str:
    """Normalize a string entry by putting to lowercase, removing spaces and commas."""
    return candidate.lower().replace(" ", "").replace(",", "")


@lru_cache
def resolve(input_str: str, candidates: tuple[str, ...]) -> str:
    """Resolving user input (`input_str`) against a list of `candidates` and return the
    best match.

    This function first normalizes the input and list of candidates, and performs a
    series of checks.

    First, if the exact string exists in the candidates, return it.

    Second, if only one of the candidates has the input as an opening substring, return
    it.

    Finally, we perform two naive matching procedures: difflib and substring matching.

    Difflib matching use difflib.get_close_matches to look for close matches, with
    the cutoff set to 0.75.

    Substring matching looks for all candidates that have the input as a substring.

    Depending on the output of these techniques, one of the following will occur:
        - Zero difflib matches; Zero substring matches
            Raise a NoMatchingStringsErro
        - 1 difflib match; X substring matches
            Return the difflib match. It does not matter how many substring matches were
            found/
        - 0 difflib matches; 1 substring match;
            Return the substring match.
        - (>1 difflib matches; X substring match) | (0 difflib; >1 substring)
            Raise a TooManyMatchingStringsError.

    Parameters
    ----------
    input_str : str
        Input string corresponding to what we roughly want.
    candidates : tuple[str, ...]
        Candidates to look through. Should be a tuple to be cached.

    Returns
    -------
    str
        A best match.

    Raises
    ------
    NoMatchingStringsError
        If there are no matching strings in the candidates.
    TooManyMatchingStringsError
        If a single close match could not be identified.
    """
    normalized_candidates = {normalize(candidate): candidate for candidate in candidates}
    normalized_input = normalize(input_str)

    if normalized_input in normalized_candidates:
        return normalized_candidates[normalized_input]

    starts_with = [x for x in normalized_candidates if x.startswith(normalized_input)]
    if len(starts_with) == 1:
        return normalized_candidates[starts_with[0]]

    difflib_matches = difflib.get_close_matches(
        normalized_input, normalized_candidates.keys(), cutoff=0.75
    )
    substring_matches: list[str] = [
        y for x, y in normalized_candidates.items() if normalized_input in x
    ]

    match (len(difflib_matches), len(substring_matches)):
        case (0, 0):
            raise NoMatchingStringsError(input_str, candidates)
        case (1, _):
            return normalized_candidates[difflib_matches[0]]
        case (0, 1):
            return substring_matches[0]
        case (0, _):
            raise TooManyMatchingStringsError(input_str, substring_matches)
        case _:
            raise TooManyMatchingStringsError(
                input_str, [normalized_candidates[m] for m in difflib_matches]
            )


P = ParamSpec("P")
R = TypeVar("R")

type CandidateSource = Iterable[str] | Callable[[Any], Iterable[str]]
"""Either a static collection of candidates, or a callable evaluated at call
time with the bound instance (i.e. `self`) that produces them."""


def _materialize(source: CandidateSource, args: tuple[Any, ...]) -> tuple[str, ...]:
    """Evaluate a candidate source at call time.

    Callables receive the bound instance (``args[0]`` on methods); plain
    iterables are simply frozen. Always returns a tuple, because `resolve`
    is lru_cached and needs hashable candidates.
    """
    if callable(source):
        return tuple(source(args[0]))
    return tuple(source)


def coerce_kwargs(
    valid_fields: CandidateSource,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A decorator to coerce kwargs of a function call to a set of valid field names."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(func)
        explicit_params = {
            name
            for name, param in sig.parameters.items()
            if param.kind
            not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
        }

        @wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            fields = _materialize(valid_fields, args)
            new_kwargs = {
                k if k in explicit_params else resolve(k, fields): v
                for k, v in kwargs.items()
            }
            return func(*args, **new_kwargs)  # type: ignore[arg-type]

        return inner

    return decorator


def assert_membership(
    field: str, candidates: CandidateSource
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to ensure that the argument provided to `field` is a member
    of `candidates`."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(func)

        @wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> R:
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            bound.arguments[field] = resolve(
                bound.arguments[field], _materialize(candidates, args)
            )
            return func(*bound.args, **bound.kwargs)

        return inner

    return decorator


def coerce_datetime(*args: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A decorator to coerce the input data to `args` into a consistent datetime format.

    `args` should be field names on the decorated function. The input to those fields
    will be coerced by `dateutil.parser.parse`.

    We assume European-style date notation, i.e. 01/02/27 is the 1st Feb 2027.
    """

    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(function)

        @wraps(function)
        def _inner(*inner_args: P.args, **inner_kwargs: P.kwargs) -> R:
            bound = sig.bind(*inner_args, **inner_kwargs)
            bound.apply_defaults()
            for field in args:
                bound.arguments[field] = parse(bound.arguments[field], dayfirst=True)
            return function(*bound.args, **bound.kwargs)

        return _inner

    return decorator
