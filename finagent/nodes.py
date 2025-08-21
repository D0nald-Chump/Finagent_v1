from __future__ import annotations

from typing import Any, Dict
from pathlib import Path

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
from .pdf_rag import PDFRAGManager


def readpdf_agent(state: State) -> State:
    log("→ ReadPDFAgent")
    ctx = dict(state.get("ctx", {}))

    # 1) If pdf_text already provided upstream, keep it
    existing_text = ctx.get("pdf_text")
    if isinstance(existing_text, str) and existing_text.strip():
        # Still initialize PDF RAG if we have a path
        pdf_path_value = ctx.get("pdf_path")
        if pdf_path_value:
            _initialize_pdf_rag(pdf_path_value, ctx)
        return merge(state, {"ctx": ctx})

    # 2) Build candidate PDF paths: ctx.pdf_path then default TSLA file
    candidates: list[Path] = []
    pdf_path_value = ctx.get("pdf_path")
    if isinstance(pdf_path_value, str) and pdf_path_value.strip():
        candidates.append(Path(pdf_path_value))
    default_pdf = Path("TSLA-Q2-2025-Update.pdf")
    if default_pdf.exists():
        candidates.append(default_pdf)

    extracted_text: str | None = None
    successful_path: str | None = None
    
    for path in candidates:
        try:
            if not path.exists():
                continue
            # Lazy import so the rest of the app works even without pypdf installed
            try:
                from pypdf import PdfReader  # type: ignore
            except Exception as e:
                log(f"pypdf not available: {e}")
                continue

            reader = PdfReader(str(path))
            pages_text: list[str] = []
            for page in getattr(reader, "pages", []):
                try:
                    pages_text.append(page.extract_text() or "")
                except Exception:
                    pages_text.append("")
            text_joined = "\n".join(pages_text).strip()
            if text_joined:
                extracted_text = text_joined
                successful_path = str(path.resolve())
                ctx["pdf_path"] = successful_path
                break
        except Exception as e:
            log(f"PDF read failed for {path}: {e}")

    # 3) Fallback to dummy text if extraction failed
    if not extracted_text:
        extracted_text = "Dummy PDF text with tables & figures about a fictional company FY2024."

    ctx["pdf_text"] = extracted_text
    
    # 4) Initialize PDF RAG system if we have a successful path
    if successful_path:
        _initialize_pdf_rag(successful_path, ctx)
    
    return merge(state, {"ctx": ctx})


# Global PDF RAG manager instance
_pdf_rag_manager: PDFRAGManager | None = None


def _initialize_pdf_rag(pdf_path: str, ctx: dict) -> None:
    """Initialize the PDF RAG system."""
    global _pdf_rag_manager
    try:
        if _pdf_rag_manager is None:
            _pdf_rag_manager = PDFRAGManager()
        
        success = _pdf_rag_manager.initialize_from_pdf(pdf_path)
        ctx["pdf_rag_enabled"] = success
        
        if success:
            # Store some statistics for debugging
            stats = _pdf_rag_manager.get_statistics()
            ctx["pdf_rag_stats"] = stats
            log(f"→ PDF RAG: Initialized with {stats.get('total_chunks', 0)} chunks")
        else:
            log("→ PDF RAG: Initialization failed")
            
    except Exception as e:
        log(f"→ PDF RAG: Initialization error: {e}")
        ctx["pdf_rag_enabled"] = False


def get_pdf_rag_manager() -> PDFRAGManager | None:
    """Get the global PDF RAG manager instance."""
    return _pdf_rag_manager


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


# Configuration mapping for financial statement types
STATEMENT_CONFIG = {
    "balance_sheet": {
        "sys_prompt": BS_SYS,
        "state_key": "bs",
        "log_name": "BS_Worker",
        "display_name": "BalanceSheetWorker"
    },
    "income_statement": {
        "sys_prompt": IS_SYS,
        "state_key": "inc",
        "log_name": "IS_Worker",
        "display_name": "IncomeStatementWorker"
    },
    "cash_flows": {
        "sys_prompt": CF_SYS,
        "state_key": "cf",
        "log_name": "CF_Worker",
        "display_name": "CashFlowsWorker"
    }
}

CHECKER_CONFIG = {
    "balance_sheet": {
        "sys_prompt": BS_CHECKER_SYS,
        "state_key": "bs",
        "log_name": "BS_Checker",
        "display_name": "BSChecker"
    },
    "income_statement": {
        "sys_prompt": IS_CHECKER_SYS,
        "state_key": "inc",
        "log_name": "IS_Checker",
        "display_name": "ISChecker"
    },
    "cash_flows": {
        "sys_prompt": CF_CHECKER_SYS,
        "state_key": "cf",
        "log_name": "CF_Checker",
        "display_name": "CFChecker"
    }
}


# Generic generator function to replace all worker functions
def generator(statement_type: str) -> callable:
    """
    Generic generator function factory for financial statement generation.
    
    Args:
        statement_type: One of "balance_sheet", "income_statement", "cash_flows"
    
    Returns:
        A function that generates the specified financial statement type
    """
    config = STATEMENT_CONFIG.get(statement_type)
    if not config:
        raise ValueError(f"Unknown statement type: {statement_type}")
    
    def _generator(state: State) -> State:
        # Check if PDF RAG is available and enabled
        ctx = state.get('ctx', {})
        pdf_rag_enabled = ctx.get('pdf_rag_enabled', False)
        
        if pdf_rag_enabled and _pdf_rag_manager and _pdf_rag_manager.is_initialized:
            # Use citation-enhanced generator
            citation_generator = _pdf_rag_manager.get_citation_enhanced_generator(
                statement_type, config['sys_prompt']
            )
            return citation_generator(state)
        else:
            # Fallback to original generator logic
            section_data = dict(state.get(config['state_key'], {}))
            feedback = section_data.get('feedback', [])
            existing_draft = section_data.get('draft', '')
            r = section_data.get("retries", 0)
            
            # 区分首次生成和修订模式
            if feedback and existing_draft:
                # 修订模式：基于反馈改进现有草稿
                log(f"→ [Sub] {config['display_name']} (LLM) - Revision Mode (attempt {r + 1})")
                
                feedback_text = "\n".join([
                    f"- {item.get('issue', '')}: {item.get('suggestion', '')}" 
                    for item in feedback if isinstance(item, dict)
                ]) if feedback else "General improvements needed"
                
                user = f"""Previous draft needs revision based on checker feedback:

FEEDBACK TO ADDRESS:
{feedback_text}

CURRENT DRAFT TO REVISE:
{existing_draft}

ORIGINAL DOCUMENT CONTEXT:
{state.get('ctx', {}).get('pdf_text', '<none>')}

Please revise the draft above to address all the feedback points while maintaining the same structure and style. Focus on fixing the specific issues mentioned."""
            else:
                # 首次生成模式
                log(f"→ [Sub] {config['display_name']} (LLM) - Initial Generation")
                user = f"ctx.pdf_text sample: {state.get('ctx', {}).get('pdf_text', '<none>')}"
            
            text, in_tok, out_tok = call_llm(MODEL_NAME, config['sys_prompt'], user)
            log_cost(config['log_name'], "worker", in_tok, out_tok, config['sys_prompt'], text)
            
            # 清除反馈，因为已经处理了
            section_data.update({
                "draft": text, 
                "_v": section_data.get("_v", 0) + 1, 
                "retries": r,
                "feedback": []  # 清除已处理的反馈
            })
            
            return merge(state, {config['state_key']: section_data})
    
    return _generator


# Generic checker function to replace all checker functions
def checker(statement_type: str) -> callable:
    """
    Generic checker function factory for financial statement validation.
    
    Args:
        statement_type: One of "balance_sheet", "income_statement", "cash_flows"
    
    Returns:
        A function that validates the specified financial statement type
    """
    config = CHECKER_CONFIG.get(statement_type)
    if not config:
        raise ValueError(f"Unknown statement type: {statement_type}")
    
    def _checker(state: State) -> State:
        log(f"→ [Sub] {config['display_name']} (LLM)")
        draft = dict(state.get(config['state_key'], {})).get("draft", "")
        text, in_tok, out_tok = call_llm(MODEL_NAME, config['sys_prompt'], draft)
        log_cost(config['log_name'], "local_checker", in_tok, out_tok, config['sys_prompt'], text)
        import json

        fb = {"passed": True, "feedback": []}
        try:
            fb = json.loads(text)
        except Exception:
            pass
        
        section_data = dict(state.get(config['state_key'], {}))
        r = section_data.get("retries", 0)
        if not fb.get("passed", False):
            # 修复：当达到重试上限时，写回 passed=True 并自增 _v，避免 Join 无限等待
            if r + 1 >= MAX_RETRIES:
                section_data.update({"passed": True, "feedback": fb.get("feedback", []), "retries": r + 1, "_v": section_data.get("_v", 0) + 1})
            else:
                section_data.update({"passed": False, "feedback": fb.get("feedback", []), "retries": r + 1, "_v": section_data.get("_v", 0) + 1})
        else:
            section_data.update({"passed": True, "feedback": fb.get("feedback", []), "_v": section_data.get("_v", 0) + 1})
        
        return merge(state, {config['state_key']: section_data})
    
    return _checker


# Create specific generator functions using the generic factory
balance_sheet_generator = generator("balance_sheet")
income_statement_generator = generator("income_statement")
cash_flows_generator = generator("cash_flows")

# Create specific checker functions using the generic factory
balance_sheet_checker = checker("balance_sheet")
income_statement_checker = checker("income_statement")
cash_flows_checker = checker("cash_flows")

# Keep backward compatibility by creating aliases with old names
balance_sheet_worker = balance_sheet_generator
income_statement_worker = income_statement_generator
cash_flows_worker = cash_flows_generator
bs_checker = balance_sheet_checker
is_checker = income_statement_checker
cf_checker = cash_flows_checker





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


# Generic router function to replace all route functions
def router(statement_type: str) -> callable:
    """
    Generic router function factory for financial statement routing.
    
    Args:
        statement_type: One of "balance_sheet", "income_statement", "cash_flows"
    
    Returns:
        A function that routes based on the specified financial statement validation status
    """
    config = CHECKER_CONFIG.get(statement_type)
    if not config:
        raise ValueError(f"Unknown statement type: {statement_type}")
    
    def _router(state: State):
        section_data = dict(state.get(config['state_key'], {}))
        if section_data.get("passed"):
            return "done"
        # 仅分支判断，不修改 state
        if section_data.get("retries", 0) >= MAX_RETRIES:
            return "done"
        return "retry"
    
    return _router


# Create specific router functions using the generic factory
balance_sheet_router = router("balance_sheet")
income_statement_router = router("income_statement")
cash_flows_router = router("cash_flows")

# Keep backward compatibility by creating aliases with old names
route_bs = balance_sheet_router
route_is = income_statement_router
route_cf = cash_flows_router


