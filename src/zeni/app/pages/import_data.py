"""Import page — upload CSV bank statements and import them."""

import os
import tempfile
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

from zeni.app.state import get_bank_names, invalidate_cache
from zeni.basic_types import Account

if TYPE_CHECKING:
    from zeni.database import DatabaseManager


def page():
    st.header("Import Statement")

    db: DatabaseManager = st.session_state.db

    uploaded = st.file_uploader(
        "Upload a bank statement CSV", type=["csv"], key="csv_upload"
    )
    if uploaded is None:
        st.info("Upload a CSV file to import transactions.")
        return

    # --- Configure ---
    c1, c2 = st.columns(2)
    with c1:
        bank = st.selectbox("Bank", get_bank_names(), key="import_bank")
    with c2:
        account_options = [a.value for a in Account]
        account_str = st.selectbox("Account type", account_options, key="import_account")

    # --- Preview ---
    st.subheader("Preview")
    preview_df = pd.read_csv(uploaded)
    st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)
    st.caption(f"{len(preview_df)} rows in file")
    uploaded.seek(0)

    # --- Import ---
    if st.button("Import", type="primary"):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="wb") as tmp:
            tmp.write(uploaded.getvalue())
            tmp_path = tmp.name
        try:
            result = db.read_in(
                bank=bank,
                account_type=Account(account_str),
                statement=tmp_path,
            )
            invalidate_cache()
            st.success(
                f"Imported **{result.new_count}** new transactions, "
                f"**{result.duplicate_count}** duplicates skipped "
                f"(out of {result.transaction_count} total)."
            )
        except Exception as e:
            st.error(f"Import failed: {e}")
        finally:
            os.unlink(tmp_path)
