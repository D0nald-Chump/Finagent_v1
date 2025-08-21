from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .state import State
from .nodes import (
    readpdf_agent,
    planner_agent,
    total_checker,
    aggregator,
    generator,
    checker,
    router,
    join_barrier,
    join_route,
)


def build_statement_processor_subgraph(statement_type: str) -> StateGraph:
    """
    Build a parameterized subgraph for processing a specific financial statement type.
    
    Args:
        statement_type: One of "balance_sheet", "income_statement", "cash_flows"
    
    Returns:
        A compiled subgraph that processes the specified statement type
    """
    sg = StateGraph(State)
    
    # Create statement-specific functions using the factories
    statement_generator = generator(statement_type)
    statement_checker = checker(statement_type)
    statement_router = router(statement_type)
    
    # Add nodes with generic names
    sg.add_node("Generator", statement_generator)
    sg.add_node("Checker", statement_checker)
    
    # Build the Generator -> Checker -> (retry or done) flow
    sg.add_edge(START, "Generator")
    sg.add_edge("Generator", "Checker")
    sg.add_conditional_edges("Checker", statement_router, {"retry": "Generator", "done": END})
    
    return sg


def build_sections_subgraph() -> StateGraph:
    """
    Build the main sections processing subgraph using individual statement processors.
    """
    sg = StateGraph(State)
    
    # Create individual statement processor subgraphs
    bs_subgraph = build_statement_processor_subgraph("balance_sheet").compile()
    is_subgraph = build_statement_processor_subgraph("income_statement").compile()
    cf_subgraph = build_statement_processor_subgraph("cash_flows").compile()
    
    # Add the subgraphs as nodes
    sg.add_node("BS_Processor", bs_subgraph)
    sg.add_node("IS_Processor", is_subgraph)
    sg.add_node("CF_Processor", cf_subgraph)
    sg.add_node("Join", join_barrier)
    
    # Start all processors in parallel
    sg.add_edge(START, "BS_Processor")
    sg.add_edge(START, "IS_Processor")
    sg.add_edge(START, "CF_Processor")
    
    # All processors flow to the join barrier
    sg.add_edge("BS_Processor", "Join")
    sg.add_edge("IS_Processor", "Join")
    sg.add_edge("CF_Processor", "Join")
    
    # Join barrier controls the final flow
    sg.add_conditional_edges("Join", join_route, {"wait": "Join", "go": END})
    
    return sg


def build_parent_graph() -> StateGraph:
    parent = StateGraph(State)
    parent.add_node("ReadPDF", readpdf_agent)
    parent.add_node("Planner", planner_agent)
    sections_subgraph = build_sections_subgraph().compile()
    parent.add_node("Sections", sections_subgraph)
    parent.add_node("TotalChecker", total_checker)
    parent.add_node("Aggregator", aggregator)

    parent.add_edge(START, "ReadPDF")
    parent.add_edge("ReadPDF", "Planner")
    parent.add_edge("Planner", "Sections")
    parent.add_edge("Sections", "TotalChecker")
    parent.add_edge("TotalChecker", "Aggregator")
    parent.add_edge("Aggregator", END)
    return parent


