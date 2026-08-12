from __future__ import annotations

from sqlalchemy import Column, ForeignKey, String, Table

from .base_model import ZeniBase

transaction_imports = Table(
    "transaction_imports",
    ZeniBase.metadata,
    Column(
        "transaction_id",
        String(36),
        ForeignKey("transactions.id"),
        primary_key=True,
    ),
    Column(
        "statement_id",
        String(36),
        ForeignKey("imported_statements.id"),
        primary_key=True,
    ),
)
