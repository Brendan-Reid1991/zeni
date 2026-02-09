"""Reusable Streamlit UI components for transaction views."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import streamlit as st

from zeni.app.state import get_db, invalidate_cache

if TYPE_CHECKING:
    import pandas as pd

_FOCUSED_COLS = ["id", "bank", "date", "name", "category", "amount", "currency", "notes"]
_ALL_COLS = [
    "id",
    "bank",
    "date",
    "time",
    "name",
    "category",
    "amount",
    "currency",
    "notes",
    "balance",
]
_DISABLED_FOCUSED = ["id", "bank", "date", "amount", "currency"]
_DISABLED_ALL = ["id", "bank", "date", "time", "amount", "currency", "balance"]


@dataclass
class EditorResult:
    """Return value from transaction_editor."""

    edited: pd.DataFrame
    original: pd.DataFrame
    selected_ids: list[str] = field(default_factory=list)


def transaction_editor(
    dataframe: pd.DataFrame,
    *,
    key: str,
    categories: list[str],
    selectable: bool = False,
) -> EditorResult:
    """Render an editable transaction table with optional row checkboxes.

    Parameters
    ----------
    df : pd.DataFrame
        Transactions to display. Must contain an ``id`` column.
    key : str
        Unique prefix for all Streamlit widget keys.
    categories : list[str]
        Valid category options for the selectbox column.
    selectable : bool
        If True, prepend a checkbox column for row selection.

    Returns
    -------
    EditorResult
    """
    show_all = st.toggle("Show all columns", value=False, key=f"{key}_show_all")

    if show_all:
        cols = [c for c in _ALL_COLS if c in dataframe.columns]
        disabled = [c for c in _DISABLED_ALL if c in dataframe.columns]
    else:
        cols = [c for c in _FOCUSED_COLS if c in dataframe.columns]
        disabled = [c for c in _DISABLED_FOCUSED if c in dataframe.columns]

    edit_df = dataframe[cols].copy()
    edit_df["notes"] = edit_df["notes"].fillna("")

    if selectable:
        edit_df.insert(0, "_select", False)

    column_config: dict = {
        "id": None,
        "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
        "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
        "name": st.column_config.TextColumn("Name"),
        "category": st.column_config.SelectboxColumn(
            "Category",
            options=categories,
            required=True,
        ),
        "notes": st.column_config.TextColumn("Notes"),
    }
    if selectable:
        column_config["_select"] = st.column_config.CheckboxColumn(
            "", default=False, width="small"
        )

    edited = st.data_editor(
        edit_df,
        width="stretch",
        hide_index=True,
        disabled=disabled,
        column_config=column_config,
        key=f"{key}_editor",
    )

    selected_ids: list[str] = []
    if selectable:
        selected_ids = edited.loc[edited["_select"], "id"].tolist()

    return EditorResult(edited=edited, original=edit_df, selected_ids=selected_ids)


def save_inline_changes(result: EditorResult, *, key: str) -> None:
    """Detect inline edits and render a save button if any rows changed.

    Compares name, category, and notes columns between *edited* and *original*.
    """
    changed_mask = (
        (result.edited["name"] != result.original["name"])
        | (result.edited["category"] != result.original["category"])
        | (result.edited["notes"] != result.original["notes"])
    )
    changed = result.edited[changed_mask]

    if changed.empty:
        return

    st.info(f"{len(changed)} transaction(s) modified.")
    if st.button("Save changes", type="primary", key=f"{key}_save"):
        db = get_db()
        original = result.original.loc[changed.index]
        for idx, row in changed.iterrows():
            orig = original.loc[idx]
            db.update_transaction(
                row["id"],
                name=row["name"] if row["name"] != orig["name"] else None,
                category=row["category"]
                if row["category"] != orig["category"]
                else None,
                notes=row["notes"] if row["notes"] != orig["notes"] else None,
            )
        invalidate_cache()
        st.rerun()


def summary_metrics(df: pd.DataFrame) -> None:
    """Render an inflow / outflow / net / count metrics row."""
    amounts = df["amount"].astype(float)
    inflow = amounts[amounts > 0].sum()
    outflow = amounts[amounts < 0].sum()
    net = inflow + outflow

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inflow", f"\u00a3{inflow:,.2f}")
    m2.metric("Outflow", f"\u00a3{abs(outflow):,.2f}")
    m3.metric("Net", f"\u00a3{net:,.2f}")
    m4.metric("Count", len(df))
