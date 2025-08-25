import pandas as pd
from typing import Dict, Any, Iterable, Tuple

def _pick_income_stmt_bucket(xbrl_json: Dict[str, Any]) -> Dict[str, Any]:
    """Return the dict for the income/operations statement, handling common key variants."""
    for key in (
        "StatementsOfIncome",
        "ConsolidatedStatementsOfIncome",
        "ConsolidatedStatementsOfOperations",
        "StatementsOfOperations",
        "IncomeStatement"  # fallback if a tool normalizes names
    ):
        if key in xbrl_json and isinstance(xbrl_json[key], dict):
            return xbrl_json[key]
    raise KeyError("No income statement bucket found in xbrl_json.")

def _period_key(fact: Dict[str, Any]) -> Tuple[str, str]:
    """Return (startDate, endDate) tuple; raises if missing."""
    p = fact.get("period") or {}
    return p["startDate"], p["endDate"]

# convert XBRL-JSON of income statement to a pandas DataFrame
def get_income_statement(xbrl_json: Dict[str, Any]) -> pd.DataFrame:
    stmt = _pick_income_stmt_bucket(xbrl_json)
    rows: Dict[str, Dict[str, Any]] = {}  # {usGaapItem: { "start-end": value, ... }}

    for us_gaap_item, facts in stmt.items():
        if not isinstance(facts, Iterable):
            continue
        per: Dict[str, Any] = {}
        for fact in facts:
            # skip segmented facts (not needed for your analysis)
            if "segment" in fact:
                continue
            try:
                start, end = _period_key(fact)
            except KeyError:
                continue  # malformed period; skip
            col = f"{start}-{end}"
            # first occurrence wins for a given period
            if col not in per:
                per[col] = fact.get("value")
        if per:
            rows[us_gaap_item] = per

    # Build DF with items as rows, periods as columns
    df = pd.DataFrame.from_dict(rows, orient="index")

    # Coerce all to numeric (non-numeric -> NaN)
    df = df.apply(pd.to_numeric, errors="coerce")

    # Sort columns by endDate (the right half of "start-end")
    def _sort_key(cols: Iterable[str]):
        ends = []
        for c in cols:
            try:
                ends.append(pd.to_datetime(c.split("-", 1)[1]))
            except Exception:
                ends.append(pd.NaT)
        return ends

    df = df.sort_index(axis=1, key=_sort_key)

    # Optional: sort rows (items) alphabetically for consistency
    df = df.sort_index()

    return df
