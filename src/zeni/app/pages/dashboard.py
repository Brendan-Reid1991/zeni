"""Dashboard page — spending summary and charts."""

from typing import TYPE_CHECKING

import streamlit as st

from zeni.app.state import get_transactions
from zeni.utils import filter_dataframe

if TYPE_CHECKING:
    from zeni.utils.filters import FilterT


def page():
    st.header("Spending Dashboard")

    df = get_transactions()
    if df.empty:
        st.info("No transactions to analyse. Import some statements first.")
        return

    # Ensure amount is float for charting
    df = df.copy()
    df["amount"] = df["amount"].astype(float)

    # --- Filters ---
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    with c1:
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        date_range = st.date_input(
            "Date range", value=(min_date, max_date), key="dash_date_range"
        )
    with c2:
        banks = sorted(df["bank"].unique().tolist())
        sel_banks = st.multiselect("Bank", banks, key="dash_bank_filter")
    with c3:
        categories = sorted(df["category"].unique().tolist())
        sel_cats = st.multiselect("Include categories", categories, key="dash_cat_inc")
    with c4:
        excl_cats = st.multiselect("Exclude categories", categories, key="dash_cat_exc")

    filters: dict[str, FilterT] = {}
    if date_range and len(date_range) == 2:
        filters["date"] = (str(date_range[0]), str(date_range[1]))
    if sel_banks:
        filters["bank"] = sel_banks
    if sel_cats:
        filters["category"] = sel_cats
    period = filter_dataframe(df, **filters)
    if excl_cats:
        period = period[~period["category"].isin(excl_cats)]

    # --- Metrics ---
    income = period.loc[period["amount"] > 0, "amount"].sum()
    expenses = period.loc[period["amount"] < 0, "amount"].sum()
    net = income + expenses

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Income", f"\u00a3{income:,.2f}")
    m2.metric("Expenses", f"\u00a3{abs(expenses):,.2f}")
    m3.metric("Net", f"\u00a3{net:,.2f}")
    m4.metric("Transactions", len(period))

    # --- Charts ---
    spending = period[period["amount"] < 0].copy()

    st.subheader("Monthly Spending")
    if not spending.empty:
        monthly = (
            spending.assign(month=lambda d: d["date"].dt.to_period("M").astype(str))
            .groupby("month")["amount"]
            .sum()
            .abs()
        )
        st.bar_chart(monthly)
    else:
        st.info("No expenses in this period.")

    left, right = st.columns(2)

    with left:
        st.subheader("Spending by Category")
        if not spending.empty:
            by_cat = (
                spending.groupby("category")["amount"]
                .sum()
                .abs()
                .sort_values(ascending=True)
            )
            st.bar_chart(by_cat, horizontal=True)
        else:
            st.info("No expenses in this period.")

    with right:
        st.subheader("Spending by Bank")
        if not spending.empty:
            by_bank = (
                spending.groupby("bank")["amount"]
                .sum()
                .abs()
                .sort_values(ascending=True)
            )
            st.bar_chart(by_bank, horizontal=True)
        else:
            st.info("No expenses in this period.")

    # --- Monthly breakdown table ---
    st.subheader("Monthly Breakdown")
    if not period.empty:
        pivot = (
            period.assign(month=lambda d: d["date"].dt.to_period("M").astype(str))
            .pivot_table(
                index="month",
                columns="category",
                values="amount",
                aggfunc="sum",
                fill_value=0,
            )
            .sort_index(ascending=False)
        )
        st.dataframe(pivot, width="stretch")
