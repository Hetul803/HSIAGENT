"""LangGraph construction for AeroSpec Agent."""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from .nodes import (
    constraint_and_ranking_node,
    knowledge_retriever_node,
    mission_interpreter_node,
    report_node,
    verification_node,
)
from .state import AgentState


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("mission_interpreter", mission_interpreter_node)
    graph.add_node("knowledge_retriever", knowledge_retriever_node)
    graph.add_node("constraint_ranking", constraint_and_ranking_node)
    graph.add_node("verification", verification_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("mission_interpreter")
    graph.add_edge("mission_interpreter", "knowledge_retriever")
    graph.add_edge("knowledge_retriever", "constraint_ranking")
    graph.add_edge("constraint_ranking", "verification")
    graph.add_edge("verification", "report")
    graph.add_edge("report", END)

    return graph.compile()
