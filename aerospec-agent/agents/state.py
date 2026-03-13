"""State schema for LangGraph workflow."""
from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    user_input: dict[str, Any]
    mission: dict[str, Any]
    retrieval_query: dict[str, Any]
    candidates: list[dict[str, Any]]
    ranking_summary: dict[str, Any]
    ranked: list[dict[str, Any]]
    selected: list[dict[str, Any]]
    alternatives: dict[str, list[dict[str, Any]]]
    verification: dict[str, Any]
    report: dict[str, Any]
    workflow_log: list[str]
    errors: list[dict[str, str]]
