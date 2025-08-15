# Budgeter

Multi-bank budgeting: ingest statements, auto-classify transactions (groceries, bills, etc.), and fix anything interactively. Shows a timeline of transfers, expenditure, and savings.

## Features
- **Multi-bank ingest:** map arbitrary CSV columns to a standard schema via adapters.
- **Rules-based auto-classify:** YAML rules (keywords/regex/amount rules). Defaults to `Uncategorized`.
- **Interactive review:** Streamlit UI to reclassify and save changes.
- **Timeline & summaries:** monthly/weekly spend, income, transfers.
- **Extensible:** add bank adapters or ML classifiers later.

## Quickstart

```bash
# create & activate a venv (or use uv)
python -m venv .venv && source .venv/bin/activate

# install (dev + UI extras)
pip install -e ".[dev,ui]"

# run tests
pytest

# run the UI
streamlit run src/budgeter/ui/app.py
```

## Project layout

```
budgeter-template/
├─ src/budgeter/
│  ├─ ingest/
│  │  ├─ base.py
│  │  ├─ adapters.py
│  │  └─ standard_schema.py
│  ├─ classify/
│  │  ├─ rules.py
│  │  └─ __init__.py
│  ├─ ui/
│  │  └─ app.py
│  ├─ __init__.py
│  └─ types.py
├─ data/samples/
│  ├─ sample_rules.yaml
│  └─ sample_statement.csv
├─ tests/
│  └─ test_rules.py
├─ .github/workflows/ci.yml
├─ .pre-commit-config.yaml
├─ pyproject.toml
├─ LICENSE
└─ README.md
```

## Bank adapters

Each adapter converts a raw bank CSV into the **standard schema**:
- `date` (YYYY-MM-DD)
- `description` (string)
- `amount` (float; outflow negative, inflow positive)
- `account` (string identifying the source account)
- `currency` (ISO code; optional)

See `src/budgeter/ingest/adapters.py` for examples.

## Classification rules

Rules live in YAML (see `data/samples/sample_rules.yaml`). They support:
- `categories`: canonical category names
- `keywords`: map of category -> list of substrings to match on `description`
- `regex`: map of category -> list of regex to match on `description`
- `amount_rules`: map of category -> list of rules: `{ min?: float, max?: float }`
- `default_category`: used when no rule matches (defaults to `Uncategorized`).

## Streamlit UI

Run `streamlit run src/budgeter/ui/app.py` then:
- Upload a CSV.
- Choose an adapter (or generic).
- Load rules YAML.
- Review/override categories.
- Download the corrected CSV.

## Roadmap
- Support PDF parsing (statement OCR) via optional extra.
- ML classifier fallback (scikit-learn/lightgbm).
- Recurring transactions detection.
- Budget planning envelopes.
- Bank API connectors (Plaid/TrueLayer where available).

## Contributing
- Use `ruff` + `mypy` and keep functions small and testable.
- Add unit tests with any new rules.
- Run CI locally with `pytest -q`.

## License
MIT
