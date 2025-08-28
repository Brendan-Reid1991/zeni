# app.py
from __future__ import annotations

import base64
import io
from datetime import datetime, date
from typing import Any, List, Optional

import pandas as pd
import plotly.express as px
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from starlette.middleware.wsgi import WSGIMiddleware

# ---- FastAPI (zeni API stub) -------------------------------------------------

app = FastAPI(title="zeni API + Dash UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Transaction(BaseModel):
    date: str | date | datetime
    name: str
    amount: float
    currency: Optional[str] = "GBP"
    type: Optional[str] = None


class ClassifyRequest(BaseModel):
    transactions: List[Transaction]


def _coerce_date(v: Any) -> date:
    if isinstance(v, date):
        return v
    return pd.to_datetime(v).date()


def _simple_rules_category(name: str, amount: float) -> str:
    s = name.lower()
    if any(
        k in s
        for k in [
            "tesco",
            "sainsbury",
            "asda",
            "aldi",
            "lidl",
            "waitrose",
            "morrisons",
            "ocado",
        ]
    ):
        return "Groceries"
    if any(
        k in s
        for k in [
            "uber",
            "bolt",
            "tfl",
            "train",
            "rail",
            "bus",
            "oyster",
            "national express",
        ]
    ):
        return "Transport"
    if any(k in s for k in ["netflix", "spotify", "itunes", "disney", "patreon"]):
        return "Entertainment"
    if any(
        k in s for k in ["octopus", "ovo", "edf", "british gas", "thames water", "eon"]
    ):
        return "Utilities"
    if any(k in s for k in ["amazon", "argos", "currys", "ikea", "b&q"]):
        return "Shopping"
    if any(
        k in s for k in ["hmrc", "tax", "salary", "payroll", "transfer in", "deposit"]
    ):
        return "Income"
    if amount > 500:
        return "Large Expense"
    return "Other"


def classify_transactions(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure required columns exist (adapt this to your standardization layer)
    required = ["date", "name", "amount"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(missing)}")

    out = df.copy()
    out["date"] = out["date"].apply(_coerce_date)
    # currency/type are optional in the input; keep if present, else default
    if "currency" not in out.columns:
        out["currency"] = "GBP"
    if "type" not in out.columns:
        out["type"] = None

    # Add/overwrite predicted category column
    out["category"] = [
        _simple_rules_category(str(n), float(a))
        for n, a in zip(out["name"], out["amount"])
    ]
    return out


@app.post("/classify")
def classify(req: ClassifyRequest):
    # Convert to DataFrame, run rules, return records (replace with your zeni classifier)
    df = pd.DataFrame([t.model_dump() for t in req.transactions])
    classified = classify_transactions(df)
    # Return records; pydantic will serialize dates properly
    return {"transactions": classified.to_dict(orient="records")}


@app.get("/", response_class=HTMLResponse)
def root():
    # Redirect the user to the Dash app
    return RedirectResponse(url="/dash")


# ---- Dash (Plotly) UI --------------------------------------------------------

# Dash runs on Flask internally; mount it under FastAPI via WSGI
import dash  # noqa: E402
from dash import Dash, Input, Output, State, dcc, html, dash_table  # noqa: E402


def make_dash_app() -> Dash:
    dash_app = Dash(
        __name__,
        requests_pathname_prefix="/dash/",
        suppress_callback_exceptions=True,
        title="zeni • Budgeting UI",
    )

    dash_app.layout = html.Div(
        style={"maxWidth": 1200, "margin": "0 auto", "padding": "24px"},
        children=[
            html.H2("zeni • CSV classifier + live Plotly"),
            html.Div(
                style={"marginBottom": "12px"},
                children=[
                    dcc.Upload(
                        id="upload",
                        children=html.Div(["Drag & Drop or ", html.A("Select CSV")]),
                        style={
                            "width": "100%",
                            "height": "64px",
                            "lineHeight": "64px",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "8px",
                            "textAlign": "center",
                        },
                        multiple=False,
                    ),
                ],
            ),
            html.Div(
                style={"display": "flex", "gap": "8px", "marginBottom": "8px"},
                children=[
                    html.Button(
                        "Re-classify (via API)", id="reclassify-btn", n_clicks=0
                    ),
                    html.Button("Clear", id="clear-btn", n_clicks=0),
                    html.Button("Download CSV", id="download-btn", n_clicks=0),
                    html.Div(id="status", style={"marginLeft": "auto", "opacity": 0.7}),
                ],
            ),
            dcc.Store(id="data-store"),  # holds the current dataset (list[dict])
            dash_table.DataTable(
                id="table",
                columns=[],
                data=[],
                editable=True,  # we'll restrict to the 'category' field in a callback
                row_deletable=True,
                page_size=12,
                sort_action="native",
                filter_action="native",
                style_table={"overflowX": "auto"},
                style_cell={"minWidth": 90, "maxWidth": 260, "whiteSpace": "normal"},
            ),
            html.Hr(),
            html.Div(
                style={
                    "display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "16px",
                },
                children=[
                    dcc.Graph(id="by-category"),
                    dcc.Graph(id="timeline"),
                ],
            ),
            dcc.Download(id="download"),
        ],
    )

    # Helper: parse uploaded CSV (base64 string from dcc.Upload)
    def parse_upload(contents: str) -> pd.DataFrame:
        header, b64 = contents.split(",", 1)
        decoded = base64.b64decode(b64)
        # Try utf-8 then fall back to latin-1 for bank exports
        try:
            s = decoded.decode("utf-8")
        except UnicodeDecodeError:
            s = decoded.decode("latin-1")
        buf = io.StringIO(s)
        df = pd.read_csv(buf)
        return df

    # Upload → parse → classify → store + table
    @dash_app.callback(
        Output("data-store", "data"),
        Output("table", "data"),
        Output("table", "columns"),
        Output("status", "children"),
        Input("upload", "contents"),
        State("upload", "filename"),
        prevent_initial_call=True,
    )
    def on_upload(contents, filename):
        if not contents:
            raise dash.exceptions.PreventUpdate
        try:
            df = parse_upload(contents)

            # 🔁 Call the in-process classifier (you can swap this for a real HTTP call)
            classified = classify_transactions(df)

            records = classified.to_dict(orient="records")
            cols = [
                {"name": c, "id": c, "editable": (c == "category")}
                for c in classified.columns
            ]

            msg = f"Loaded {len(classified)} rows from {filename}"
            return records, records, cols, msg
        except Exception as e:
            return dash.no_update, dash.no_update, dash.no_update, f"Error: {e}"

    # Re-classify current rows via the API (simulate async / remote)
    @dash_app.callback(
        Output("table", "data"),
        Output("status", "children"),
        Input("reclassify-btn", "n_clicks"),
        State("table", "data"),
        prevent_initial_call=True,
    )
    def reclassify_click(n, rows):
        if not rows:
            raise dash.exceptions.PreventUpdate
        try:
            df = pd.DataFrame(rows)
            classified = classify_transactions(df)
            records = classified.to_dict(orient="records")
            return records, f"Re-classified {len(records)} rows"
        except Exception as e:
            return dash.no_update, f"Error: {e}"

    # Clear table & store
    @dash_app.callback(
        Output("table", "data"),
        Output("table", "columns"),
        Output("data-store", "data"),
        Output("status", "children"),
        Input("clear-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def clear_table(_):
        return [], [], None, "Cleared"

    # Update charts whenever table data changes (edits / sorts / deletes)
    @dash_app.callback(
        Output("by-category", "figure"),
        Output("timeline", "figure"),
        Input("table", "data"),
    )
    def update_charts(rows):
        if not rows:
            # Empty figures to keep UI tidy
            return px.bar(title="By Category"), px.line(title="Daily Total")
        df = pd.DataFrame(rows)
        # Ensure required columns for plotting
        if "category" not in df.columns:
            df["category"] = "Uncategorized"
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        by_cat = (
            df.groupby("category", dropna=False)["amount"]
            .sum()
            .reset_index()
            .sort_values("amount", ascending=False)
        )
        fig_cat = px.bar(by_cat, x="category", y="amount", title="Spend by Category")

        by_day = (
            df.groupby("date", dropna=False)["amount"]
            .sum()
            .reset_index()
            .sort_values("date")
        )
        fig_time = px.line(
            by_day, x="date", y="amount", markers=True, title="Daily Total"
        )

        return fig_cat, fig_time

    # Download current table as CSV
    @dash_app.callback(
        Output("download", "data"),
        Input("download-btn", "n_clicks"),
        State("table", "data"),
        prevent_initial_call=True,
    )
    def on_download(n, rows):
        if not rows:
            raise dash.exceptions.PreventUpdate
        df = pd.DataFrame(rows)
        return dcc.send_data_frame(df.to_csv, "zeni_classified.csv", index=False)

    return dash_app


dash_app = make_dash_app()
# Mount the Dash (Flask/WGSI) app under FastAPI
app.mount("/dash", WSGIMiddleware(dash_app.server))


# ---- Dev entrypoint ----------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


# # create a venv first if you like
# pip install fastapi "uvicorn[standard]" dash plotly pandas python-multipart
# python app.py
# # open http://localhost:8000/dash
