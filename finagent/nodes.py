from __future__ import annotations

from typing import Any, Dict

from .config import MODEL_NAME
from .costing import log_cost
from .llm import call_llm
from .prompts import (
    PLANNER_SYS,
    PLANNER_USER,
    BS_SYS,
    IS_SYS,
    CF_SYS,
    BS_CHECKER_SYS,
    IS_CHECKER_SYS,
    CF_CHECKER_SYS,
    TOTAL_CHECKER_SYS,
    AGGREGATOR_SYS,
)
from .state import State, merge, log, MAX_RETRIES


def readpdf_agent(state: State) -> State:
    log("→ ReadPDFAgent")
    ctx = dict(state.get("ctx", {}))
    ctx.update({"pdf_text": "Dummy PDF text with tables & figures about a fictional company FY2024."})
    return merge(state, {"ctx": ctx})


def planner_agent(state: State) -> State:
    log("→ PlannerAgent (LLM)")
    user = "Rules: (none for demo)\nPlease propose tasks."
    text, in_tok, out_tok = call_llm(MODEL_NAME, PLANNER_SYS, PLANNER_USER + "\n" + user)
    log_cost("Planner", "planner", in_tok, out_tok, PLANNER_SYS, text)
    import json

    tasks = ["balance_sheet", "income_statement", "cash_flows"]
    try:
        j = json.loads(text)
        if isinstance(j, Dict) and isinstance(j.get("tasks"), list) and j["tasks"]:
            tasks = [t for t in j["tasks"] if t in {"balance_sheet", "income_statement", "cash_flows"}]
    except Exception:
        pass
    return merge(state, {"tasks": tasks})


def total_checker(state: State) -> State:
    log("→ TotalChecker (LLM)")
    user = (
        f"Drafts summary:\nBS:{state.get('bs', {}).get('draft', '')}\n"
        f"IS:{state.get('inc', {}).get('draft', '')}\nCF:{state.get('cf', {}).get('draft', '')}"
    )
    text, in_tok, out_tok = call_llm(MODEL_NAME, TOTAL_CHECKER_SYS, user)
    log_cost("TotalChecker", "global_checker", in_tok, out_tok, TOTAL_CHECKER_SYS, text)
    import json

    suggestions = []
    try:
        j = json.loads(text)
        suggestions = j.get("suggestions", [])
    except Exception:
        suggestions = [{"area": "normalization", "action": "ensure units and terminology are consistent"}]
    return merge(state, {"global_suggestions": {"items": suggestions, "raw": text}})


def aggregator(state: State) -> State:
    log("→ Aggregator (LLM)")
    user = f"""Inputs (validated):
- Balance Sheet:
{state.get('bs', {}).get('draft', '<none>')}

- Income Statement:
{state.get('inc', {}).get('draft', '<none>')}

- Cash Flows:
{state.get('cf', {}).get('draft', '<none>')}

- Global Suggestions: {state.get('global_suggestions', {})}
"""
    text, in_tok, out_tok = call_llm(MODEL_NAME, AGGREGATOR_SYS, user)
    log_cost("Aggregator", "synthesizer", in_tok, out_tok, AGGREGATOR_SYS, text)
    return merge(state, {"final_report": text})


# Workers
def balance_sheet_worker(state: State) -> State:
    log("→ [Sub] BalanceSheetWorker (LLM)")
    user = f"ctx.pdf_text sample: {state.get('ctx', {}).get('pdf_text', '<none>')}"
    text, in_tok, out_tok = call_llm(MODEL_NAME, BS_SYS, user)
    log_cost("BS_Worker", "worker", in_tok, out_tok, BS_SYS, text)
    bs = dict(state.get("bs", {}))
    r = bs.get("retries", 0)
    bs.update({"draft": text, "_v": bs.get("_v", 0) + 1, "retries": r})
    return merge(state, {"bs": bs})


def income_statement_worker(state: State) -> State:
    log("→ [Sub] IncomeStatementWorker (LLM)")
    user = f"ctx.pdf_text sample: {state.get('ctx', {}).get('pdf_text', '<none>')}"
    text, in_tok, out_tok = call_llm(MODEL_NAME, IS_SYS, user)
    log_cost("IS_Worker", "worker", in_tok, out_tok, IS_SYS, text)
    inc = dict(state.get("inc", {}))
    r = inc.get("retries", 0)
    inc.update({"draft": text, "_v": inc.get("_v", 0) + 1, "retries": r})
    return merge(state, {"inc": inc})


def cash_flows_worker(state: State) -> State:
    log("→ [Sub] CashFlowsWorker (LLM)")
    user = f"ctx.pdf_text sample: {state.get('ctx', {}).get('pdf_text', '<none>')}"
    text, in_tok, out_tok = call_llm(MODEL_NAME, CF_SYS, user)
    log_cost("CF_Worker", "worker", in_tok, out_tok, CF_SYS, text)
    cf = dict(state.get("cf", {}))
    r = cf.get("retries", 0)
    cf.update({"draft": text, "_v": cf.get("_v", 0) + 1, "retries": r})
    return merge(state, {"cf": cf})


# Checkers (with fix to avoid infinite join waiting)
def bs_checker(state: State) -> State:
    log("→ [Sub] BSChecker (LLM)")
    draft = dict(state.get("bs", {})).get("draft", "")
    text, in_tok, out_tok = call_llm(MODEL_NAME, BS_CHECKER_SYS, draft)
    log_cost("BS_Checker", "local_checker", in_tok, out_tok, BS_CHECKER_SYS, text)
    import json

    fb = {"passed": True, "feedback": []}
    try:
        fb = json.loads(text)
    except Exception:
        pass
    bs = dict(state.get("bs", {}))
    r = bs.get("retries", 0)
    if not fb.get("passed", False):
        # 修复：当达到重试上限时，写回 passed=True 并自增 _v，避免 Join 无限等待
        if r + 1 >= MAX_RETRIES:
            bs.update({"passed": True, "feedback": fb.get("feedback", []), "retries": r + 1, "_v": bs.get("_v", 0) + 1})
        else:
            bs.update({"passed": False, "feedback": fb.get("feedback", []), "retries": r + 1, "_v": bs.get("_v", 0) + 1})
    else:
        bs.update({"passed": True, "feedback": fb.get("feedback", []), "_v": bs.get("_v", 0) + 1})
    return merge(state, {"bs": bs})


def is_checker(state: State) -> State:
    log("→ [Sub] ISChecker (LLM)")
    draft = dict(state.get("inc", {})).get("draft", "")
    text, in_tok, out_tok = call_llm(MODEL_NAME, IS_CHECKER_SYS, draft)
    log_cost("IS_Checker", "local_checker", in_tok, out_tok, IS_CHECKER_SYS, text)
    import json

    fb = {"passed": True, "feedback": []}
    try:
        fb = json.loads(text)
    except Exception:
        pass
    inc = dict(state.get("inc", {}))
    r = inc.get("retries", 0)
    if not fb.get("passed", False):
        # 修复：当达到重试上限时，写回 passed=True 并自增 _v，避免 Join 无限等待
        if r + 1 >= MAX_RETRIES:
            inc.update({"passed": True, "feedback": fb.get("feedback", []), "retries": r + 1, "_v": inc.get("_v", 0) + 1})
        else:
            inc.update({"passed": False, "feedback": fb.get("feedback", []), "retries": r + 1, "_v": inc.get("_v", 0) + 1})
    else:
        inc.update({"passed": True, "feedback": fb.get("feedback", []), "_v": inc.get("_v", 0) + 1})
    return merge(state, {"inc": inc})


def cf_checker(state: State) -> State:
    log("→ [Sub] CFChecker (LLM)")
    draft = dict(state.get("cf", {})).get("draft", "")
    text, in_tok, out_tok = call_llm(MODEL_NAME, CF_CHECKER_SYS, draft)
    log_cost("CF_Checker", "local_checker", in_tok, out_tok, CF_CHECKER_SYS, text)
    import json

    fb = {"passed": True, "feedback": []}
    try:
        fb = json.loads(text)
    except Exception:
        pass
    cf = dict(state.get("cf", {}))
    r = cf.get("retries", 0)
    if not fb.get("passed", False):
        # 修复：当达到重试上限时，写回 passed=True 并自增 _v，避免 Join 无限等待
        if r + 1 >= MAX_RETRIES:
            cf.update({"passed": True, "feedback": fb.get("feedback", []), "retries": r + 1, "_v": cf.get("_v", 0) + 1})
        else:
            cf.update({"passed": False, "feedback": fb.get("feedback", []), "retries": r + 1, "_v": cf.get("_v", 0) + 1})
    else:
        cf.update({"passed": True, "feedback": fb.get("feedback", []), "_v": cf.get("_v", 0) + 1})
    return merge(state, {"cf": cf})


def join_barrier(state: State) -> State:
    log("→ [Sub] JoinBarrier (waiting for BS/IS/CF passed)")
    return state


def join_route(state: State):
    bs_passed = dict(state.get("bs", {})).get("passed")
    inc_passed = dict(state.get("inc", {})).get("passed")
    cf_passed = dict(state.get("cf", {})).get("passed")
    if bs_passed and inc_passed and cf_passed:
        return "go"
    return "wait"


def route_bs(state: State):
    bs = dict(state.get("bs", {}))
    if bs.get("passed"):
        return "done"
    # 仅分支判断，不修改 state
    if bs.get("retries", 0) >= MAX_RETRIES:
        return "done"
    return "retry"


def route_is(state: State):
    inc = dict(state.get("inc", {}))
    if inc.get("passed"):
        return "done"
    if inc.get("retries", 0) >= MAX_RETRIES:
        return "done"
    return "retry"


def route_cf(state: State):
    cf = dict(state.get("cf", {}))
    if cf.get("passed"):
        return "done"
    if cf.get("retries", 0) >= MAX_RETRIES:
        return "done"
    return "retry"


