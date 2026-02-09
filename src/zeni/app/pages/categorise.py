"""Categorise page — bulk assign categories to transactions."""

import streamlit as st

from zeni.app.components import save_inline_changes, transaction_editor
from zeni.app.state import get_all_categories, get_db, get_transactions, invalidate_cache
from zeni.utils import filter_dataframe, parse_amount_query


def page():
    st.header("Categorise Transactions")

    db = get_db()
    df = get_transactions()

    if df.empty:
        st.info("No transactions to categorise. Import some statements first.")
        return

    # --- Quick stats ---
    total = len(df)
    uncat = len(df[df["category"] == "uncategorised"])
    m1, m2, m3 = st.columns(3)
    m1.metric("Uncategorised", uncat)
    m2.metric("Total", total)
    m3.metric(
        "Categorised", f"{((total - uncat) / total * 100):.0f}%" if total else "0%"
    )

    # --- Filters ---
    fc1, fc2, fc3, fc4 = st.columns([2, 2, 1.5, 1.5])
    with fc1:
        all_cats = sorted(df["category"].unique().tolist())
        default_idx = (
            all_cats.index("uncategorised") if "uncategorised" in all_cats else 0
        )
        cat_filter = st.selectbox(
            "Show category", all_cats, index=default_idx, key="cat_page_filter"
        )
    with fc2:
        name_filter = st.text_input("Name contains", key="cat_name_filter")
    with fc3:
        bank_options = ["All", *sorted(df["bank"].unique().tolist())]
        bank_filter = st.selectbox("Bank", bank_options, key="cat_bank_filter")
    with fc4:
        amt_query = st.text_input(
            "Amount",
            key="cat_amt",
            placeholder="e.g. 3.30, >=50",
        )

    # Apply filters
    filters: dict = {"category": cat_filter}
    if name_filter:
        filters["name"] = f"^{name_filter}"
    if bank_filter != "All":
        filters["bank"] = bank_filter
    if (amt_filter := parse_amount_query(amt_query)) is not None:
        filters["amount"] = amt_filter
    view = filter_dataframe(df, **filters)

    if view.empty:
        st.success(f"No '{cat_filter}' transactions found. You're all caught up!")
        return

    all_categories = get_all_categories()
    view = view.sort_values("date", ascending=False)

    # --- Editable table with checkboxes ---
    result = transaction_editor(
        view, key="cat", categories=all_categories, selectable=True
    )
    save_inline_changes(result, key="cat")

    # --- Bulk action bar ---
    st.divider()
    ac1, ac2 = st.columns([2, 2])
    with ac1:
        target_cat = st.selectbox(
            "Assign category", get_all_categories(), key="cat_target"
        )
    with ac2:
        notes_text = st.text_input("Notes (optional)", key="cat_notes")

    selected_ids = result.selected_ids

    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button(
            f"Apply to {len(selected_ids)} selected",
            disabled=len(selected_ids) == 0,
            type="primary",
        ):
            kwargs = {"category": target_cat}
            if notes_text.strip():
                kwargs["notes"] = notes_text.strip()
            count = db.update_transactions(selected_ids, **kwargs)
            invalidate_cache()
            st.success(f"Updated {count} transactions to '{target_cat}'.")
            st.rerun()
    # Build conditions from all active filters
    conditions: dict = {}
    if name_filter:
        conditions["name"] = f"^{name_filter}"
    if bank_filter != "All":
        conditions["bank"] = bank_filter
    if amt_query.strip():
        conditions["amount"] = amt_query.strip()

    has_conditions = len(conditions) > 0

    with bc2:
        if st.button(
            "Save as rule",
            disabled=not has_conditions,
            help="Create a permanent rule from all active filters + category. "
            "Applies retroactively and on all future imports.",
        ):
            _ = db.add_rule(
                conditions=conditions,
                category=target_cat,
                notes=notes_text.strip() or None,
            )
            invalidate_cache()
            # Build a human-readable summary
            parts = []
            if name_filter:
                parts.append(f"name contains '{name_filter}'")
            if bank_filter != "All":
                parts.append(f"bank = '{bank_filter}'")
            if amt_query.strip():
                parts.append(f"amount {amt_query.strip()}")
            st.success(
                f"Rule created: {' AND '.join(parts)} → {target_cat}. "
                f"Applied retroactively to all matching transactions."
            )
            st.rerun()
