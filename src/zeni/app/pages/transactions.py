"""Transactions page — browse, filter, and edit transactions."""

from typing import TYPE_CHECKING

import pandas as pd
import plotly.express as px
import streamlit as st

from zeni.app.state import get_all_categories, get_transactions, invalidate_cache

if TYPE_CHECKING:
    from zeni.database import DatabaseManager


def _apply_filters(
    df: pd.DataFrame,
    date_range: tuple | list,
    banks: list[str],
    categories: list[str],
    amt_min: float | None,
    amt_max: float | None,
    name_search: str,
) -> pd.DataFrame:
    """Apply filter widgets to the transaction DataFrame."""
    mask = pd.Series(True, index=df.index)
    if date_range and len(date_range) == 2:
        mask &= (df["date"].dt.date >= date_range[0]) & (
            df["date"].dt.date <= date_range[1]
        )
    if banks:
        mask &= df["bank"].isin(banks)
    if categories:
        mask &= df["category"].isin(categories)
    if amt_min is not None:
        mask &= df["amount"] >= amt_min
    if amt_max is not None:
        mask &= df["amount"] <= amt_max
    if name_search:
        mask &= df["name"].str.contains(name_search, case=False, na=False)
    return df[mask]


def page():
    st.header("Transactions")

    df = get_transactions()
    if df.empty:
        st.info("No transactions yet. Import a statement to get started.")
        return

    all_categories = get_all_categories()

    # --- Filters ---
    c1, c2, c3, c4, c5 = st.columns([2, 1.5, 2, 2, 1.5])
    with c1:
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        date_range = st.date_input(
            "Date range", value=(min_date, max_date), key="tx_date_range"
        )
    with c2:
        banks = sorted(df["bank"].unique().tolist())
        sel_banks = st.multiselect("Bank", banks, key="tx_bank_filter")
    with c3:
        categories = sorted(df["category"].unique().tolist())
        sel_cats = st.multiselect("Category", categories, key="tx_cat_filter")
    with c4:
        lo, hi = st.columns(2)
        amt_min = lo.number_input("Min amount", value=None, key="tx_amt_min")
        amt_max = hi.number_input("Max amount", value=None, key="tx_amt_max")
    with c5:
        name_search = st.text_input("Name contains", key="tx_name_search")

    filtered = _apply_filters(
        df, date_range, sel_banks, sel_cats, amt_min, amt_max, name_search
    )

    # --- Editable table ---
    edit_cols = ["id", "bank", "date", "name", "category", "amount", "currency", "notes"]
    edit_df = filtered[edit_cols].copy()
    # Ensure notes column has empty strings instead of NaN for editing
    edit_df["notes"] = edit_df["notes"].fillna("")

    edited = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=True,
        disabled=["id", "bank", "date", "amount", "currency"],
        column_config={
            "id": None,  # hidden
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
            "name": st.column_config.TextColumn("Name"),
            "category": st.column_config.SelectboxColumn(
                "Category",
                options=all_categories,
                required=True,
            ),
            "notes": st.column_config.TextColumn("Notes"),
        },
        key="tx_editor",
    )
    st.caption(f"{len(filtered)} transactions")

    # --- Detect and save changes ---
    changed_mask = (
        (edited["name"] != edit_df["name"])
        | (edited["category"] != edit_df["category"])
        | (edited["notes"] != edit_df["notes"])
    )
    changed = edited[changed_mask]

    if not changed.empty:
        st.info(f"{len(changed)} transaction(s) modified.")
        if st.button("Save changes", type="primary"):
            db: DatabaseManager = st.session_state.db
            original = edit_df.loc[changed.index]
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

    # --- Summary statistics ---
    st.divider()
    amounts = filtered["amount"].astype(float)
    inflow = amounts[amounts > 0].sum()
    outflow = amounts[amounts < 0].sum()
    net = inflow + outflow

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Inflow", f"\u00a3{inflow:,.2f}")
    m2.metric("Outflow", f"\u00a3{abs(outflow):,.2f}")
    m3.metric("Net", f"\u00a3{net:,.2f}")
    m4.metric("Count", len(filtered))

    # --- Spending by category chart ---
    spending = filtered[amounts < 0].copy()
    if not spending.empty:
        spending = spending.copy()
        spending["amount"] = spending["amount"].astype(float).abs()
        by_cat = (
            spending.groupby("category", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=True)
        )
        fig = px.bar(
            by_cat,
            x="amount",
            y="category",
            orientation="h",
            labels={"amount": "Total spent", "category": ""},
            title="Spending by Category",
        )
        fig.update_layout(
            yaxis_categoryorder="total ascending",
            showlegend=False,
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
