from budgeter.classify.rules import load_rules, classify_df
import pandas as pd
from io import StringIO

CSV = """date,description,amount,account,currency
2025-07-01,SALARY ACME LTD,2500.00,Current,GBP
2025-07-02,TESCO EXTRA,-54.23,Current,GBP
2025-07-03,STARBUCKS,-3.25,Current,GBP
"""

def test_rules_keywords(tmp_path):
    rules = load_rules("data/samples/sample_rules.yaml")
    df = pd.read_csv(StringIO(CSV))
    out = classify_df(df, rules)
    cats = out["category"].tolist()
    assert cats[0] == "Income"
    assert cats[1] == "Groceries"
    assert cats[2] == "Eating Out"
