# Zeni

Multi-bank budgeting tool: ingest CSV statements, auto-classify transactions via rules, and review everything in a Streamlit UI.

## Features

- **Multi-bank ingest** — pluggable bank adapters (Chase, Monzo) with pre/post-processing pipelines to handle bank-specific quirks.
- **Rules engine** — persistent categorisation rules with regex, substring, range, and exact-match conditions. Rules apply retroactively and on import.
- **Inline editing** — reclassify transactions directly in the UI with bulk actions and one-click rule creation.
- **Dashboard** — monthly spending charts, category/bank breakdowns, date and category filtering.
- **SQLite storage** — all transactions, import history, and rules stored via SQLAlchemy ORM.

## Quickstart

```bash
# install with uv (recommended)
make install

# run the Streamlit app
python -m zeni.app
```

## Project layout

```
src/zeni/
├── app/                    # Streamlit UI
│   ├── __main__.py         # Entry point (python -m zeni.app)
│   ├── state.py            # Session state management
│   ├── components.py       # Shared UI components
│   └── pages/
│       ├── transactions.py # Browse & inline-edit
│       ├── categorise.py   # Filter, bulk-categorise, create rules
│       ├── rules.py        # Manage categorisation rules
│       ├── import_data.py  # Import CSV statements
│       └── dashboard.py    # Spending charts & metrics
├── banks/                  # Bank statement parsers
│   ├── bank.py             # ABC base + standardize() pipeline
│   ├── chase.py            # Chase adapter
│   └── monzo.py            # Monzo adapter
├── database/               # Persistence layer
│   ├── engine.py           # SQLite engine wrapper
│   ├── models.py           # Transaction, Rule, ImportedStatements
│   ├── manager.py          # DatabaseManager (CRUD + rules)
│   └── utils.py            # SQL filter helpers
├── utils/
│   ├── filters.py          # DataFrame filtering (substring, range, etc.)
│   ├── fuzzy_matcher.py    # Fuzzy string matching & @coerce_to
│   └── logging.py          # Logging setup
└── basic_types.py          # Enums: Account, Payment categories, StandardColumns
```

## Adding a bank adapter

Each adapter maps a bank's CSV format to the standard schema (`date`, `time`, `name`, `category`, `amount`, `currency`, `notes`, `balance`).

```python
from zeni.banks.bank import Bank
from zeni.basic_types import StandardColumns, Outgoing

class MyBank(Bank):
    @classmethod
    def column_map(cls):
        return {
            "Transaction Date": StandardColumns.DATE,
            "Description": StandardColumns.NAME,
            # ...
        }

    @classmethod
    def category_map(cls):
        return {
            "PURCHASE": Outgoing.LEISURE,
            # ...
        }

# Optional post-processing for bank-specific edge cases
@MyBank.post_process()
def fix_quirk(df):
    # ...
    return df
```

Register it by importing in `banks/__init__.py`.

## Categorisation rules

Rules are created in the UI or programmatically:

```python
db.add_rule(
    conditions={"name": "^tesco"},  # substring match
    category="groceries",
)

db.add_rule(
    conditions={"name": "^council", "amount": (-200, 0)},  # range match
    category="bill",
    priority=1,  # higher priority rules override lower
)
```

Filter syntax: `"^..."` substring, `"!..."` exclusion, `[a, b]` membership, `(lo, hi)` range.

## License

MIT
