"""Session state management and helpers for the Zeni Streamlit app."""

import pandas as pd
import streamlit as st

from zeni.banks.bank import _BANK_REGISTRY
from zeni.basic_types import Incoming, Internal, Outgoing
from zeni.database import DatabaseManager
from zeni.database.utils import DEFAULT_PATHWAY


def init_state() -> None:
    """Ensure all session-state keys exist with defaults."""
    defaults = {
        "db": None,
        "db_name": "",
        "tx_cache": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def connect_db(name: str) -> None:
    """Create a DatabaseManager and store in session state."""
    st.session_state.db = DatabaseManager(name, folder_path=DEFAULT_PATHWAY)
    st.session_state.db_name = name
    invalidate_cache()


def invalidate_cache() -> None:
    """Clear the transaction cache so next access re-fetches from DB."""
    st.session_state.tx_cache = None


def get_transactions(force_refresh: bool = False) -> pd.DataFrame:
    """Return all transactions as a DataFrame, cached in session state.

    Uses focused=False to include the id column needed for updates.
    """
    if force_refresh or st.session_state.tx_cache is None:
        db: DatabaseManager = st.session_state.db
        st.session_state.tx_cache = db.lookup(focused=False)
    return st.session_state.tx_cache


def get_all_categories() -> list[str]:
    """Return a sorted list of all category enum values."""
    return sorted([*Outgoing, *Incoming, *Internal])


def get_bank_names() -> list[str]:
    """Return sorted list of registered bank names."""
    return sorted(_BANK_REGISTRY.keys())
