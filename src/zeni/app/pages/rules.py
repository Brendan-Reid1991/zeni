"""Rules page — manage auto-categorisation rules."""

import json
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from zeni.app.state import get_all_categories, get_transactions, invalidate_cache

if TYPE_CHECKING:
    from zeni.database import DatabaseManager


def _format_conditions(raw_json: str) -> str:
    """Format a JSON conditions string for display."""
    conditions = json.loads(raw_json)
    parts = []
    for field, pattern in conditions.items():
        if isinstance(pattern, list) and len(pattern) == 2:
            parts.append(f"{field} between {pattern[0]} and {pattern[1]}")
        elif isinstance(pattern, str) and pattern.startswith("^"):
            parts.append(f"{field} contains '{pattern[1:]}'")
        elif isinstance(pattern, str) and pattern.startswith("!"):
            parts.append(f"{field} excludes '{pattern[1:]}'")
        else:
            parts.append(f"{field} = {pattern!r}")
    return " AND ".join(parts)


def _apply_conditions_to_df(df: pd.DataFrame, conditions: dict) -> pd.DataFrame:
    """Apply rule conditions to a DataFrame for preview/testing."""
    mask = pd.Series(True, index=df.index)
    for field, pattern in conditions.items():
        if field not in df.columns:
            continue
        if isinstance(pattern, list) and len(pattern) == 2:
            mask &= (df[field].astype(float) >= pattern[0]) & (
                df[field].astype(float) <= pattern[1]
            )
        elif isinstance(pattern, str) and pattern.startswith("^"):
            mask &= df[field].astype(str).str.contains(pattern[1:], case=False, na=False)
        elif isinstance(pattern, str) and pattern.startswith("!"):
            mask &= ~df[field].astype(str).str.contains(
                pattern[1:], case=False, na=False
            )
        else:
            mask &= df[field] == pattern
    return df[mask]


def page():
    st.header("Rules")
    st.caption(
        "Rules automatically categorise transactions on import. "
        "They also apply retroactively when created."
    )

    db: DatabaseManager = st.session_state.db

    # --- Existing rules ---
    rules = db.get_rules()
    if rules:
        st.subheader("Active Rules")
        for rule in rules:
            col_desc, col_del = st.columns([5, 1])
            with col_desc:
                desc = _format_conditions(rule.conditions)
                notes_part = f"  (notes: {rule.notes!r})" if rule.notes else ""
                st.text(f"[P{rule.priority}]  {desc}  →  {rule.category}{notes_part}")
            with col_del:
                if st.button("Delete", key=f"del_{rule.id}"):
                    db.delete_rule(rule.id)
                    st.rerun()
    else:
        st.info("No rules yet. Create one below.")

    # --- Add rule ---
    st.divider()
    st.subheader("Add Rule")

    # Name condition
    c1, c2 = st.columns(2)
    with c1:
        name_pattern = st.text_input(
            "Name pattern",
            key="rule_name_pattern",
            help="Use ^text for substring match, !text for exclusion, or exact value",
        )
    with c2:
        bank_pattern = st.text_input(
            "Bank (optional)",
            key="rule_bank_pattern",
            help="Leave empty to match all banks",
        )

    # Amount condition
    c3, c4 = st.columns(2)
    with c3:
        amt_min = st.number_input(
            "Min amount (optional)", value=None, key="rule_amt_min"
        )
    with c4:
        amt_max = st.number_input(
            "Max amount (optional)", value=None, key="rule_amt_max"
        )

    # Target
    c5, c6, c7 = st.columns(3)
    with c5:
        category = st.selectbox(
            "Set category to", get_all_categories(), key="rule_category"
        )
    with c6:
        notes = st.text_input("Notes (optional)", key="rule_notes")
    with c7:
        priority = st.number_input(
            "Priority",
            value=0,
            step=1,
            key="rule_priority",
            help="Higher priority rules run later and override lower ones",
        )

    # Build conditions dict
    conditions: dict = {}
    if name_pattern:
        conditions["name"] = name_pattern
    if bank_pattern:
        conditions["bank"] = bank_pattern
    if amt_min is not None and amt_max is not None:
        conditions["amount"] = (amt_min, amt_max)
    elif amt_min is not None:
        conditions["amount"] = (amt_min, 999999)
    elif amt_max is not None:
        conditions["amount"] = (-999999, amt_max)

    has_conditions = len(conditions) > 0

    # --- Test / Preview ---
    bc1, bc2 = st.columns(2)
    with bc1:
        if st.button("Test rule", disabled=not has_conditions):
            df = get_transactions()
            if not df.empty:
                matches = _apply_conditions_to_df(df, conditions)
                st.info(f"Would match **{len(matches)}** transactions.")
                if not matches.empty:
                    st.dataframe(
                        matches[["bank", "date", "name", "category", "amount"]].head(10),
                        use_container_width=True,
                        hide_index=True,
                    )

    with bc2:
        if st.button("Save rule", type="primary", disabled=not has_conditions):
            rule = db.add_rule(
                conditions=conditions,
                category=category,
                notes=notes.strip() or None,
                priority=int(priority),
            )
            invalidate_cache()
            st.success("Rule created and applied retroactively.")
            st.rerun()
