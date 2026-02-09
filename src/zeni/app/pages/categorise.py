"""Categorise page — bulk assign categories to transactions."""

from typing import TYPE_CHECKING

import streamlit as st

from zeni.app.state import get_all_categories, get_transactions, invalidate_cache

if TYPE_CHECKING:
    from zeni.database import DatabaseManager


def page():
    st.header("Categorise Transactions")

    db: DatabaseManager = st.session_state.db
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
    fc1, fc2, fc3 = st.columns([2, 2, 1.5])
    with fc1:
        all_cats = sorted(df["category"].unique().tolist())
        # Default to "uncategorised" if present
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

    # Apply filters
    view = df[df["category"] == cat_filter].copy()
    if name_filter:
        view = view[view["name"].str.contains(name_filter, case=False, na=False)]
    if bank_filter != "All":
        view = view[view["bank"] == bank_filter]

    if view.empty:
        st.success(f"No '{cat_filter}' transactions found. You're all caught up!")
        return

    # --- Table with checkboxes ---
    view = view.sort_values("date", ascending=False)
    edit_df = view[["id", "date", "name", "category", "amount", "bank", "notes"]].copy()
    edit_df.insert(0, "_select", False)

    edited = st.data_editor(
        edit_df,
        hide_index=True,
        use_container_width=True,
        disabled=["id", "date", "name", "category", "amount", "bank", "notes"],
        column_config={
            "_select": st.column_config.CheckboxColumn("", default=False, width="small"),
            "id": None,  # hidden
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "amount": st.column_config.NumberColumn("Amount", format="%.2f"),
        },
        key="cat_editor",
    )

    selected_ids = edited.loc[edited["_select"], "id"].tolist()

    # --- Action bar ---
    st.divider()
    ac1, ac2 = st.columns([2, 2])
    with ac1:
        target_cat = st.selectbox(
            "Assign category", get_all_categories(), key="cat_target"
        )
    with ac2:
        notes_text = st.text_input("Notes (optional)", key="cat_notes")

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
    with bc2:
        if st.button(
            "Save as rule",
            disabled=not name_filter,
            help="Create a permanent rule from the current name filter + category. "
            "Applies retroactively and on all future imports.",
        ):
            conditions = {"name": f"^{name_filter}"}
            _ = db.add_rule(
                conditions=conditions,
                category=target_cat,
                notes=notes_text.strip() or None,
            )
            invalidate_cache()
            st.success(
                f"Rule created: name contains '{name_filter}' → {target_cat}. "
                f"Applied retroactively to all matching transactions."
            )
            st.rerun()
