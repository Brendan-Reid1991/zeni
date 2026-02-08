"""A fuzzy matching function."""

import difflib
import inspect
from collections.abc import Callable, Sequence
from functools import lru_cache, wraps
from typing import ParamSpec, TypeVar


class NoMatchingStringsError(Exception):
    def __init__(self, input_string: str, candidates: Sequence[str]):
        candidates_list = "\n\t- ".join(candidates)
        super().__init__(
            f"No matches for '{input_string}' found in candidates:\n\t-"
            + candidates_list
        )


class TooManyMatchingStringsError(Exception):
    def __init__(self, input_string: str, matches: Sequence[str]):
        matches_list = "\n\t- ".join(matches)
        super().__init__(
            f"More than one match found for '{input_string}':\n\t-" + matches_list
        )


def normalize(candidate: str) -> str:
    """Normalize a string entry by putting to lowercase, removing spaces and commas."""
    return candidate.lower().replace(" ", "").replace(",", "")


@lru_cache
def fuzzy_string_matcher(input_str: str, candidates: tuple[str, ...]) -> str:  # type: ignore[return]
    """A cached fuzzy matching function.

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

    if (
        len(
            _starts_with := [
                x for x in normalized_candidates if x.startswith(normalized_input)
            ]
        )
        == 1
    ):
        return normalized_candidates[_starts_with[0]]

    difflib_matches = difflib.get_close_matches(
        normalized_input, normalized_candidates.keys(), cutoff=0.75
    )
    substring_matches: list[str] = [
        y for x, y in normalized_candidates.items() if normalized_input in x
    ]

    num_dl = len(difflib_matches)
    num_st = len(substring_matches)

    match (num_dl, num_st):
        case (0, 0):
            raise NoMatchingStringsError(input_str, candidates)
        case (1, _):
            return normalized_candidates[difflib_matches[0]]
        case (0, 1):
            return substring_matches[0]
        case (x, y) if (x > 1) or (x == 0 and y > 1):
            raise TooManyMatchingStringsError(
                input_str,
                substring_matches
                if x == 0
                else tuple(map(normalized_candidates.__getitem__, difflib_matches)),
            )


P = ParamSpec("P")
R = TypeVar("R")


def coerce_to(valid_fields: tuple[str, ...]):
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
        def inner(*args, **kwargs):
            new_kwargs = {
                k if k in explicit_params else fuzzy_string_matcher(k, valid_fields): v
                for k, v in kwargs.items()
            }
            return func(*args, **new_kwargs)

        return inner

    return decorator
