import pandas as pd
from typing import Any, Dict, Iterable, Tuple, List

# --- helpers ---------------------------------------------------------------

def _pick_income_stmt_bucket(x: Dict[str, Any]) -> Dict[str, Any]:
    for key in (
        "StatementsOfIncome",
        "ConsolidatedStatementsOfIncome",
        "ConsolidatedStatementsOfOperations",
        "StatementsOfOperations",
        "IncomeStatement",
    ):
        if key in x and isinstance(x[key], dict):
            return x[key]
    raise KeyError("No income statement bucket found in xbrl_json.")

def _period_key(fact: Dict[str, Any]) -> Tuple[str, str]:
    p = fact.get("period") or {}
    return p["startDate"], p["endDate"]  # raise if missing (prefer fail-fast)

def _norm_segment_key(fact: Dict[str, Any]) -> str:
    """
    Normalize the JSON 'segment' into a stable key.
    - Handles explicitMember as dict or list
    - Handles typedMember
    - Multiple dimensions -> sort by dimension and join with '; '
    - No segment -> 'Consolidated'
    Output example:
      "srt:ProductOrServiceAxis=tsla:AutomotiveSalesMember"
      "us-gaap:StatementGeographicalAxis=us-gaap:UnitedStatesMember; srt:ProductOrServiceAxis=tsla:EnergyMember"
      "typed(tsla:CustomAxis)=<xml...>"
    """
    seg = fact.get("segment")
    if not seg:
        return "Consolidated"

    pairs: List[Tuple[str, str]] = []

    # explicitMember may be a single dict or a list of dicts
    exp = seg.get("explicitMember")
    if exp:
        if isinstance(exp, list):
            for m in exp:
                dim = m.get("dimension")
                mem = m.get("$t") or m.get("member") or ""
                if dim and mem:
                    pairs.append((dim, mem))
        elif isinstance(exp, dict):
            dim = exp.get("dimension")
            mem = exp.get("$t") or exp.get("member") or ""
            if dim and mem:
                pairs.append((dim, mem))

    # typedMember variants (structure differs by converter; we preserve content)
    typ = seg.get("typedMember") or seg.get("typedMembers")
    if typ:
        def _capture_typed(obj):
            if isinstance(obj, list):
                for t in obj:
                    _capture_typed(t)
            elif isinstance(obj, dict):
                dim = obj.get("dimension")
                # the typed value may appear under "$t" or nested; keep a compact repr
                val = obj.get("$t") or obj.get("value") or obj.get("content")
                if not val:
                    # fall back: stringified remainder without 'dimension'
                    val = str({k: v for k, v in obj.items() if k != "dimension"})
                if dim:
                    pairs.append((f"typed({dim})", str(val)))
        _capture_typed(typ)

    if not pairs:
        return "Consolidated"

    # stable: sort by dimension
    pairs.sort(key=lambda kv: kv[0])
    return "; ".join(f"{d}={m}" for d, m in pairs)

def _period_label(start: str, end: str) -> str:
    return f"{start}→{end}"  # arrow avoids splitting collisions with dates

# --- main builder ----------------------------------------------------------

def build_income_statement_with_segments(xbrl_json: Dict[str, Any], unit: str = "usd") -> pd.DataFrame:
    """
    Returns a DataFrame with:
      - index = period labels 'YYYY-MM-DD→YYYY-MM-DD' (sorted by end date)
      - columns = MultiIndex (concept, segmentKey)
      - values = numeric (NaN on non-numeric)
    Keeps only facts matching the requested 'unit' (default 'usd').
    """
    stmt = _pick_income_stmt_bucket(xbrl_json)

    # {(period_label): {(concept, segmentKey): value}}
    table: Dict[str, Dict[Tuple[str, str], Any]] = {}
    seen: set[Tuple[str, str, str]] = set()  # dedupe by (period_label, concept, segmentKey)

    for concept, facts in stmt.items():
        if not isinstance(facts, Iterable):
            continue
        for fact in facts:
            if unit and fact.get("unitRef") and fact["unitRef"].lower() != unit.lower():
                continue  # keep one unit; adjust if you need unit normalization

            try:
                start, end = _period_key(fact)
            except KeyError:
                continue
            period_label = _period_label(start, end)

            seg_key = _norm_segment_key(fact)
            key3 = (period_label, concept, seg_key)
            if key3 in seen:
                continue  # first one wins for (period, concept, segment)
            seen.add(key3)

            table.setdefault(period_label, {})[(concept, seg_key)] = fact.get("value")

    # Build DataFrame: rows=periods, columns=(concept, segmentKey)
    df = pd.DataFrame.from_dict(table, orient="index")
    # Coerce to numeric
    df = df.apply(pd.to_numeric, errors="coerce")

    # Sort rows by end date
    def _row_sort(idx: Iterable[str]):
        ends = []
        for label in idx:
            try:
                ends.append(pd.to_datetime(label.split("→", 1)[1]))
            except Exception:
                ends.append(pd.NaT)
        return ends
    df = df.sort_index(key=_row_sort)

    # Sort columns: first by concept, then by segmentKey
    if isinstance(df.columns, pd.MultiIndex):
        df = df.sort_index(axis=1, level=[0, 1])
    else:
        # ensure MultiIndex even if no segments present
        df.columns = pd.MultiIndex.from_tuples(df.columns, names=["concept", "segment"])
        df = df.sort_index(axis=1, level=[0, 1])

    # Nice names
    df.index.name = "period"
    df.columns.set_names(["concept", "segment"], inplace=True)

    return df

