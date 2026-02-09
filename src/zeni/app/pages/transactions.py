"""Transactions page — browse, filter, and edit transactions."""

from typing import TYPE_CHECKING

import plotly.express as px
import streamlit as st

from zeni.app.components import save_inline_changes, summary_metrics, transaction_editor
from zeni.app.state import get_all_categories, get_transactions
from zeni.utils import filter_dataframe, parse_amount_query

if TYPE_CHECKING:
    from zeni.utils.filters import FilterT


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
        amt_query = st.text_input(
            "Amount",
            key="tx_amt",
            placeholder="e.g. 3.30, >=50, <10",
        )
    with c5:
        name_search = st.text_input("Name contains", key="tx_name_search")

    filters: dict[str, FilterT] = {}
    if date_range and len(date_range) == 2:
        filters["date"] = (str(date_range[0]), str(date_range[1]))
    if sel_banks:
        filters["bank"] = sel_banks
    if sel_cats:
        filters["category"] = sel_cats
    if (amt_filter := parse_amount_query(amt_query)) is not None:
        filters["amount"] = amt_filter
    if name_search:
        filters["name"] = f"^{name_search}"
    filtered = filter_dataframe(df, **filters)

    # --- Editable table ---
    result = transaction_editor(filtered, key="tx", categories=all_categories)
    st.caption(f"{len(filtered)} transactions")
    save_inline_changes(result, key="tx")

    # --- Summary statistics ---
    st.divider()
    summary_metrics(filtered)

    # --- Spending by category chart ---
    amounts = filtered["amount"].astype(float)
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
        st.plotly_chart(fig, width="stretch")
