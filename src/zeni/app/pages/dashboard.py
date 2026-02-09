"""Dashboard page — spending summary and charts."""

import streamlit as st

from zeni.app.state import get_transactions


def page():
    st.header("Spending Dashboard")

    df = get_transactions()
    if df.empty:
        st.info("No transactions to analyse. Import some statements first.")
        return

    # Ensure amount is float for charting
    df = df.copy()
    df["amount"] = df["amount"].astype(float)

    # --- Date range ---
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    dc1, dc2 = st.columns(2)
    with dc1:
        start = st.date_input("From", value=min_date, key="dash_start")
    with dc2:
        end = st.date_input("To", value=max_date, key="dash_end")

    period = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]

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
    left, right = st.columns([3, 2])

    with left:
        st.subheader("Monthly Spending")
        spending = period[period["amount"] < 0].copy()
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

    with right:
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
        st.dataframe(pivot, use_container_width=True)
