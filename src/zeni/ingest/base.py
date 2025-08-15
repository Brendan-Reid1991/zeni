from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd

class IngestAdapter(ABC):
    """Base adapter: converts arbitrary bank CSV to the standard columns."""

    @abstractmethod
    def to_standard(self, df: pd.DataFrame) -> pd.DataFrame:  # must produce date/description/amount/account/currency
        ...

class GenericAdapter(IngestAdapter):
    """Assumes input already has standard columns (case-insensitive)."""

    def to_standard(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = {c.lower(): c for c in df.columns}
        out = pd.DataFrame()
        out["date"] = pd.to_datetime(df[cols.get("date", "date")]).dt.date
        out["description"] = df[cols.get("description", "description")].astype(str)
        out["amount"] = pd.to_numeric(df[cols.get("amount", "amount")], errors="coerce")
        out["account"] = df.get(cols.get("account", "account"), "unknown")
        out["currency"] = df.get(cols.get("currency", "currency"), None)
        return out
