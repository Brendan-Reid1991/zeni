import streamlit as st
import pandas as pd
from budgeter.ingest.adapters import ADAPTERS
from budgeter.classify.rules import load_rules, classify_df, DEFAULT_CATEGORY

st.set_page_config(page_title="Budgeter", layout="wide")
st.title("💸 Budgeter")

st.sidebar.header("1) Uploads")
csv_file = st.sidebar.file_uploader("Statement CSV", type=["csv"])
rules_file = st.sidebar.file_uploader("Rules YAML", type=["yml", "yaml"])
adapter_name = st.sidebar.selectbox("Bank adapter", list(ADAPTERS.keys()), index=0)

st.sidebar.header("2) Settings")
default_category = st.sidebar.text_input("Default category", value=DEFAULT_CATEGORY)

if csv_file is not None:
    df_raw = pd.read_csv(csv_file)
    df_std = ADAPTERS[adapter_name].to_standard(df_raw)
    st.subheader("Standardized Input")
    st.dataframe(df_std.head(20))

    if rules_file is not None:
        # Save to temp and load so we reuse loader
        import tempfile, yaml, os
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml")
        tmp.write(rules_file.read())
        tmp.flush()
        rules = load_rules(tmp.name)
        os.unlink(tmp.name)
        # let UI override default
        object.__setattr__(rules, "default_category", default_category)

        st.subheader("Auto-classified")
        df_cls = classify_df(df_std, rules)

        # Allow interactive edits
        categories = sorted(set(list(rules.categories) + [default_category]))
        st.caption("Click a cell in the 'category' column to edit use the dropdown below.")
        edited = df_cls.copy()
        selected_row = st.number_input("Row index to edit", min_value=0, max_value=len(df_cls)-1, value=0)
        new_cat = st.selectbox("Set category", options=[*categories, "Other…"], index=categories.index(df_cls.loc[selected_row, "category"]) if df_cls.loc[selected_row, "category"] in categories else len(categories))
        if new_cat == "Other…":
            new_cat = st.text_input("New category name", value=df_cls.loc[selected_row, "category"])
        if st.button("Apply change"):
            edited.loc[selected_row, "category"] = new_cat
            st.success(f"Row {selected_row} set to '{new_cat}'.")

        st.dataframe(edited)

        # Download
        st.download_button("⬇️ Download CSV", data=edited.to_csv(index=False), file_name="classified.csv", mime="text/csv")

        # Simple timeline summary
        st.subheader("Timeline")
        dt = pd.to_datetime(edited["date"])
        month = dt.dt.to_period("M").astype(str)
        monthly = edited.assign(month=month).groupby(["month","category"], as_index=False)["amount"].sum()
        st.dataframe(monthly.pivot_table(index="month", columns="category", values="amount", fill_value=0).reset_index())
    else:
        st.info("Upload a rules YAML to classify.")
else:
    st.info("Upload a CSV to begin.")
