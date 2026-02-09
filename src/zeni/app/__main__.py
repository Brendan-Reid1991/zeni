"""Entry point for the Zeni Streamlit app.

Usage:
    python -m zeni.app          # launches via streamlit run
    streamlit run -m zeni.app   # direct streamlit invocation
"""

import sys


def _launch() -> None:
    """Launch the app through streamlit run."""
    from streamlit.web.cli import main as st_main

    sys.argv = ["streamlit", "run", __file__]
    st_main()


def _app() -> None:
    """The Streamlit application (executed by the streamlit runtime)."""
    import streamlit as st

    from zeni.app.pages import categorise, dashboard, import_data, rules, transactions
    from zeni.app.state import (
        connect_db,
        disconnect_db,
        get_db,
        get_db_name,
        init_state,
    )
    from zeni.database.utils import DEFAULT_PATHWAY, list_databases

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

        connected = st.session_state.db is not None

        if st.button("Connect", disabled=connected or not target):
            connect_db(target)
            st.rerun()

        if st.button("Disconnect", disabled=not connected):
            disconnect_db()
            st.rerun()

        if connected:
            st.caption(f"Connected: **{get_db_name()}**")
            if st.button("Delete database", type="secondary"):
                get_db().delete()
                disconnect_db()
                st.rerun()

    if not connected:
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


if "streamlit" in sys.modules and hasattr(sys.modules["streamlit"], "runtime"):
    _app()
else:
    _launch()
