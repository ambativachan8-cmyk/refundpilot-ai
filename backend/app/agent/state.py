"""Agent state definition shared by the LangGraph graph and fallback runner."""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    user_message: str
    selected_customer_id: str
    detected_order_id: Optional[str]
    intent: Optional[dict[str, Any]]
    intent_method: str
    prior_session: Optional[dict[str, Any]]
    stage: str
    pending_requirement: str
    turn_count: int
    conv_reason: Optional[str]
    conv: Optional[dict[str, Any]]
    customer: Optional[dict[str, Any]]
    order: Optional[dict[str, Any]]
    policy_checks: list[dict[str, Any]]
    tool_calls: list[str]
    decision: Optional[str]
    customer_response: Optional[str]
    error: Optional[str]
    retry_count: int
    logs: list[dict[str, Any]]
    llm_mode: str
