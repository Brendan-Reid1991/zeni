from __future__ import annotations
import pandas as pd
from .base import IngestAdapter, GenericAdapter

class ExampleBankAdapter(IngestAdapter):
    """Example: maps ExampleBank columns to standard schema."""
    def to_standard(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame()
        out["date"] = pd.to_datetime(df["Transaction Date"]).dt.date
        out["description"] = df["Details"].astype(str)
        # ExampleBank uses separate credit/debit columns; combine them.
        amount = pd.to_numeric(df.get("Amount", 0), errors="coerce").fillna(0.0)
        credit = pd.to_numeric(df.get("Credit", 0), errors="coerce").fillna(0.0)
        debit = pd.to_numeric(df.get("Debit", 0), errors="coerce").fillna(0.0)
        out["amount"] = amount.where(amount != 0.0, credit - debit)
        out["account"] = df.get("Account Name", "ExampleBank")
        out["currency"] = df.get("Currency", None)
        return out

ADAPTERS = {
    "generic": GenericAdapter(),
    "example_bank": ExampleBankAdapter(),
}
