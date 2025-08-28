from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd
import yaml

DEFAULT_CATEGORY = "Uncategorized"


@dataclass(slots=True, frozen=True)
class Rules:
    categories: list[str]
    keywords: dict[str, list[str]]
    regex: dict[str, list[str]]
    amount_rules: dict[str, list[dict[str, float]]]
    default_category: str = DEFAULT_CATEGORY


def load_rules(path: str) -> Rules:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return Rules(
        categories=list(data.get("categories", [])),
        keywords={k: list(v) for k, v in (data.get("keywords") or {}).items()},
        regex={k: list(v) for k, v in (data.get("regex") or {}).items()},
        amount_rules={k: list(v) for k, v in (data.get("amount_rules") or {}).items()},
        default_category=data.get("default_category", DEFAULT_CATEGORY),
    )


def _match_description(desc: str, rules: Rules) -> str | None:
    d = desc.lower()
    for cat, words in rules.keywords.items():
        if any(w.lower() in d for w in words):
            return cat
    for cat, patterns in rules.regex.items():
        if any(re.search(p, desc, re.IGNORECASE) for p in patterns):
            return cat
    return None


def _match_amount(amount: float, rules: Rules) -> str | None:
    for cat, lst in rules.amount_rules.items():
        for r in lst:
            mn = r.get("min", float("-inf"))
            mx = r.get("max", float("inf"))
            if mn <= amount <= mx:
                return cat
    return None


def classify_row(row: pd.Series, rules: Rules) -> str:
    # 1) explicit category preserved
    if isinstance(row.get("category"), str) and row["category"].strip():
        return row["category"]
    # 2) description rules
    desc_cat = _match_description(str(row.get("description", "")), rules)
    if desc_cat:
        return desc_cat
    # 3) amount rules
    try:
        amount = float(row.get("amount", 0.0))
    except Exception:
        amount = 0.0
    amt_cat = _match_amount(amount, rules)
    if amt_cat:
        return amt_cat
    # 4) fallback
    return rules.default_category


def classify_df(df: pd.DataFrame, rules: Rules) -> pd.DataFrame:
    out = df.copy()
    out["category"] = out.apply(lambda r: classify_row(r, rules), axis=1)
    return out
