"""The controlled refund agent.

Implemented as a LangGraph StateGraph with explicit nodes. If LangGraph is not
installed (or fails to import on this Python version), an equivalent built-in
sequential orchestrator runs the *same* node functions — so behaviour and the
audit logs are identical either way.

Nodes:
  receive_request -> extract_intent -> identify_customer -> fetch_customer
  -> fetch_order -> read_policy -> run_policy_checks -> decide
  -> generate_response -> persist_logs ; with handle_error as the failure branch.
"""
from __future__ import annotations

from typing import Any

from . import decisions, tools
from .state import AgentState

# Detect LangGraph availability once at import time.
try:  # pragma: no cover - import guard
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover - import guard
    LANGGRAPH_AVAILABLE = False

ORCHESTRATOR = "langgraph" if LANGGRAPH_AVAILABLE else "builtin-sequential"


def _log(state: AgentState, step: str, tool: str, inp: str, out: str,
         status: str = "success", snapshot: str | None = None) -> dict[str, Any]:
    entry = tools.save_reasoning_log(
        state["session_id"], step, tool, inp, out, status, snapshot
    )
    logs = list(state.get("logs", []))
    logs.append(entry)
    calls = list(state.get("tool_calls", []))
    calls.append(tool)
    return {"logs": logs, "tool_calls": calls}


# --- Nodes -----------------------------------------------------------------
def node_receive_request(state: AgentState) -> dict[str, Any]:
    upd = _log(
        state, "receive_request", "receive_request",
        f"customer={state.get('selected_customer_id')}",
        f"message='{state.get('user_message', '')[:80]}'",
    )
    upd["retry_count"] = state.get("retry_count", 0)
    return upd


def node_extract_intent(state: AgentState) -> dict[str, Any]:
    message = state.get("user_message", "")
    intent, method, note = tools.extract_intent(message)
    status = "warning" if intent.get("needs_clarification") else "success"
    summary = (
        f"type={intent.get('intent_type')} reason={intent.get('reason')} "
        f"condition={intent.get('product_condition_claimed')} "
        f"proof={intent.get('proof_mentioned')} conf={intent.get('confidence')}"
    )
    upd = _log(state, "extract_intent", "extract_intent",
               f"method={method} ({note})", summary, status=status)
    upd["intent"] = intent
    upd["intent_method"] = method
    return upd


def node_identify_customer(state: AgentState) -> dict[str, Any]:
    cid = state.get("selected_customer_id", "")
    customer = tools.identify_customer(cid, state.get("user_message", ""))
    if not customer:
        upd = _log(state, "identify_customer", "identify_customer",
                   f"customer_id={cid}", "No matching customer found",
                   status="failed")
        upd["error"] = f"Customer {cid} not found."
        return upd
    upd = _log(state, "identify_customer", "identify_customer",
               f"customer_id={cid}", f"Identified {customer['name']}")
    return upd


def node_fetch_customer(state: AgentState) -> dict[str, Any]:
    cid = state.get("selected_customer_id", "")
    customer = tools.fetch_customer_profile(cid)
    upd = _log(state, "fetch_customer", "fetch_customer_profile",
               f"customer_id={cid}",
               f"{customer['name']} | tier={customer['tier']} | "
               f"refunds_90d={customer['refund_count_90d']}")
    upd["customer"] = customer
    return upd


def node_fetch_order(state: AgentState) -> dict[str, Any]:
    cid = state.get("selected_customer_id", "")
    order, ambiguous = tools.fetch_order(
        cid, state.get("user_message", ""), state.get("detected_order_id")
    )
    if not order:
        upd = _log(state, "fetch_order", "fetch_order",
                   f"customer_id={cid}", "No order found for customer",
                   status="failed")
        upd["error"] = "No order found. Please provide an order ID."
        return upd
    status = "warning" if ambiguous else "success"
    note = " (ambiguous — chose most recent order)" if ambiguous else ""
    upd = _log(state, "fetch_order", "fetch_order",
               f"customer_id={cid}",
               f"{order['order_id']} {order['product_name']} "
               f"(₹{order['price']:.0f}){note}", status=status)
    upd["order"] = order
    upd["detected_order_id"] = order["order_id"]
    return upd


def node_read_policy(state: AgentState) -> dict[str, Any]:
    text = tools.read_refund_policy()
    return _log(state, "read_policy", "read_refund_policy",
                "policy document", f"Loaded refund policy ({len(text)} chars)")


def node_run_policy_checks(state: AgentState) -> dict[str, Any]:
    customer = state["customer"]
    order = state["order"]
    decision, checks = tools.run_decision(
        customer, order, state.get("user_message", ""), state.get("intent")
    )
    # Log each individual policy check for the audit trail.
    logs = list(state.get("logs", []))
    calls = list(state.get("tool_calls", []))
    for c in checks:
        entry = tools.save_reasoning_log(
            state["session_id"], "run_policy_checks", "check_policy_rule",
            c["rule"], c["detail"], c["status"],
        )
        logs.append(entry)
        calls.append("check_policy_rule")
    return {
        "logs": logs,
        "tool_calls": calls,
        "policy_checks": checks,
        "decision": decision,  # provisional; confirmed in decide node
    }


def node_decide(state: AgentState) -> dict[str, Any]:
    decision = state.get("decision", "escalated")
    upd = _log(state, "decide", "decide_refund",
               f"checks={len(state.get('policy_checks', []))}",
               f"decision={decision}", snapshot=decision)
    upd["decision"] = decision
    return upd


def node_generate_response(state: AgentState) -> dict[str, Any]:
    decision = state.get("decision", "escalated")
    response, mode = decisions.generate_response(
        decision, state["customer"], state["order"],
        state.get("policy_checks", []), state.get("user_message", ""),
        state.get("intent"),
    )
    upd = _log(state, "generate_response", "generate_response",
               f"mode={mode}", f"Generated {len(response)}-char reply",
               snapshot=decision)
    upd["customer_response"] = response
    upd["llm_mode"] = mode
    return upd


def node_persist_logs(state: AgentState) -> dict[str, Any]:
    return _log(state, "persist_logs", "persist_logs",
                f"session={state['session_id']}",
                f"{len(state.get('logs', []))} log entries persisted",
                snapshot=state.get("decision"))


def node_handle_error(state: AgentState) -> dict[str, Any]:
    err = state.get("error", "Unknown error")
    customer = state.get("customer") or {"name": "there"}
    name = customer.get("name", "there").split(" ")[0]
    response = (
        f"Hi {name}, I couldn't fully verify your request ({err}). I've escalated "
        "this to our support team, who will follow up with you shortly."
    )
    upd = _log(state, "handle_error", "handle_error",
               err, "Escalated due to missing data", status="failed",
               snapshot="escalated")
    upd["decision"] = "escalated"
    upd["customer_response"] = response
    upd["llm_mode"] = state.get("llm_mode", "deterministic")
    return upd


# --- Routing helpers -------------------------------------------------------
def _route_after_customer(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "fetch_customer"


def _route_after_order(state: AgentState) -> str:
    return "handle_error" if state.get("error") else "read_policy"


# --- LangGraph build -------------------------------------------------------
def _build_langgraph():  # pragma: no cover - exercised only when installed
    g = StateGraph(AgentState)
    g.add_node("receive_request", node_receive_request)
    g.add_node("extract_intent", node_extract_intent)
    g.add_node("identify_customer", node_identify_customer)
    g.add_node("fetch_customer", node_fetch_customer)
    g.add_node("fetch_order", node_fetch_order)
    g.add_node("read_policy", node_read_policy)
    g.add_node("run_policy_checks", node_run_policy_checks)
    g.add_node("decide", node_decide)
    g.add_node("generate_response", node_generate_response)
    g.add_node("persist_logs", node_persist_logs)
    g.add_node("handle_error", node_handle_error)

    g.set_entry_point("receive_request")
    g.add_edge("receive_request", "extract_intent")
    g.add_edge("extract_intent", "identify_customer")
    g.add_conditional_edges("identify_customer", _route_after_customer,
                            {"handle_error": "handle_error", "fetch_customer": "fetch_customer"})
    g.add_edge("fetch_customer", "fetch_order")
    g.add_conditional_edges("fetch_order", _route_after_order,
                            {"handle_error": "handle_error", "read_policy": "read_policy"})
    g.add_edge("read_policy", "run_policy_checks")
    g.add_edge("run_policy_checks", "decide")
    g.add_edge("decide", "generate_response")
    g.add_edge("generate_response", "persist_logs")
    g.add_edge("persist_logs", END)
    g.add_edge("handle_error", "persist_logs")
    return g.compile()


_COMPILED = _build_langgraph() if LANGGRAPH_AVAILABLE else None


# --- Fallback sequential runner -------------------------------------------
def _run_sequential(state: AgentState) -> AgentState:
    def apply(node):
        state.update(node(state))

    apply(node_receive_request)
    apply(node_extract_intent)
    apply(node_identify_customer)
    if state.get("error"):
        apply(node_handle_error)
        apply(node_persist_logs)
        return state
    apply(node_fetch_customer)
    apply(node_fetch_order)
    if state.get("error"):
        apply(node_handle_error)
        apply(node_persist_logs)
        return state
    apply(node_read_policy)
    apply(node_run_policy_checks)
    apply(node_decide)
    apply(node_generate_response)
    apply(node_persist_logs)
    return state


# --- Public entry point ----------------------------------------------------
def run_agent(
    session_id: str,
    customer_id: str,
    message: str,
    order_id: str | None = None,
) -> AgentState:
    state: AgentState = {
        "session_id": session_id,
        "user_message": message,
        "selected_customer_id": customer_id,
        "detected_order_id": order_id,
        "intent": None,
        "intent_method": "fallback",
        "policy_checks": [],
        "tool_calls": [],
        "logs": [],
        "retry_count": 0,
        "llm_mode": "deterministic",
    }
    if LANGGRAPH_AVAILABLE and _COMPILED is not None:
        result = _COMPILED.invoke(state)
        return result  # type: ignore[return-value]
    return _run_sequential(state)
