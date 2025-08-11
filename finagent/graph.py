from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from .state import State
from .nodes import (
    readpdf_agent,
    planner_agent,
    total_checker,
    aggregator,
    balance_sheet_worker,
    income_statement_worker,
    cash_flows_worker,
    bs_checker,
    is_checker,
    cf_checker,
    join_barrier,
    join_route,
    route_bs,
    route_is,
    route_cf,
)


def build_sections_subgraph() -> StateGraph:
    sg = StateGraph(State)
    sg.add_node("BS_Worker", balance_sheet_worker)
    sg.add_node("IS_Worker", income_statement_worker)
    sg.add_node("CF_Worker", cash_flows_worker)
    sg.add_node("BS_Checker", bs_checker)
    sg.add_node("IS_Checker", is_checker)
    sg.add_node("CF_Checker", cf_checker)
    sg.add_node("Join", join_barrier)

    sg.add_edge(START, "BS_Worker")
    sg.add_edge(START, "IS_Worker")
    sg.add_edge(START, "CF_Worker")

    sg.add_edge("BS_Worker", "BS_Checker")
    sg.add_edge("IS_Worker", "IS_Checker")
    sg.add_edge("CF_Worker", "CF_Checker")

    sg.add_conditional_edges("BS_Checker", route_bs, {"retry": "BS_Worker", "done": "Join"})
    sg.add_conditional_edges("IS_Checker", route_is, {"retry": "IS_Worker", "done": "Join"})
    sg.add_conditional_edges("CF_Checker", route_cf, {"retry": "CF_Worker", "done": "Join"})

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


