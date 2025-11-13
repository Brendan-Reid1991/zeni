from typing import ClassVar, Protocol


class Bank(Protocol):
    _columns: ClassVar[set[str]]
    _categories: ClassVar[set[str]]

    @classmethod
    def column_map(cls) -> dict[str, str]: ...

    @classmethod
    def category_map(cls) -> dict[str, str]: ...


class BankRegistry:
    _supported_institutions: ClassVar[dict[str, Bank]] = {}

    @classmethod
    def register(cls, institution: Bank):
        cls._supported_institutions[institution.__name__.lower()] = institution
        return institution

    @classmethod
    def get_bank(cls, name: str) -> Bank:
        try:
            return cls._supported_institutions[name]
        except KeyError:
            raise KeyError(
                f"Invalid bank name: '{name}'. Supported banks are {list(cls._supported_institutions.keys())}"
            )
