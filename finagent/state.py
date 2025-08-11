from __future__ import annotations

from copy import deepcopy
from operator import or_ as dict_union
from typing import TypedDict, List, Dict, Any
from typing_extensions import Annotated


MAX_RETRIES = 2


def list_union(a: List[str] | None, b: List[str] | None) -> List[str]:
    a = a or []
    b = b or []
    seen: Dict[str, bool] = {}
    for x in a + b:
        if x not in seen:
            seen[x] = True
    return list(seen.keys())


def section_merge(a: Dict[str, Any] | None, b: Dict[str, Any] | None) -> Dict[str, Any]:
    a = a or {}
    b = b or {}
    va = a.get("_v", -1)
    vb = b.get("_v", -1)
    return a if va >= vb else b


class State(TypedDict, total=False):
    ctx: Annotated[dict, dict_union]
    tasks: Annotated[List[str], list_union]
    bs: Annotated[Dict[str, Any], section_merge]
    inc: Annotated[Dict[str, Any], section_merge]
    cf: Annotated[Dict[str, Any], section_merge]
    global_suggestions: Dict[str, Any]
    final_report: str


def log(msg: str) -> None:
    print(msg)


def merge(state: State, patch: Dict[str, Any]) -> State:
    s = deepcopy(state)
    s.update(patch)
    return s


