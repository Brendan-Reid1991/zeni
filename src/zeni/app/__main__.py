"""Entry point for the Zeni Streamlit app. Run with: python -m zeni.app"""

import streamlit as st

from zeni.app.pages import categorise, dashboard, import_data, rules, transactions
from zeni.app.state import connect_db, init_state
from zeni.database.utils import DEFAULT_PATHWAY, list_databases


def main():
    st.set_page_config(
        page_title="Zeni",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_state()

    with st.sidebar:
        st.title("Zeni")

        databases = list_databases(DEFAULT_PATHWAY)
        options = [*databases, "+ Create new"]
        choice = st.selectbox("Database", options, key="db_choice")

        if choice == "+ Create new":
            target = st.text_input("Database name", key="new_db_name").strip()
        else:
            target = choice

        if st.button("Connect", disabled=not target):
            connect_db(target)
            st.rerun()

        if st.session_state.db is not None:
            st.caption(f"Connected: **{st.session_state.db_name}**")

    if st.session_state.db is None:
        st.info("Select a database from the sidebar to get started.")
        st.stop()

    pages = st.navigation(
        [
            st.Page(
                transactions.page,
                title="Transactions",
                icon=":material/search:",
                url_path="transactions",
            ),
            st.Page(
                categorise.page,
                title="Categorise",
                icon=":material/label:",
                url_path="categorise",
            ),
            st.Page(rules.page, title="Rules", icon=":material/rule:", url_path="rules"),
            st.Page(
                import_data.page,
                title="Import",
                icon=":material/upload:",
                url_path="import",
            ),
            st.Page(
                dashboard.page,
                title="Dashboard",
                icon=":material/bar_chart:",
                url_path="dashboard",
            ),
        ]
    )
    pages.run()


main()
